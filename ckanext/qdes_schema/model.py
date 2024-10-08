import ckanext.qdes_schema.constants as constants
import datetime
import logging

from ckan.model import meta
from ckan.model import types as _types
from sqlalchemy import types, Column
from ckan.model.domain_object import DomainObject
from sqlalchemy import desc
try:
    from ckan.plugins.toolkit import BaseModel
except ImportError:
    # CKAN <= 2.9
    from ckan.model.meta import metadata
    from sqlalchemy.ext.declarative import declarative_base
    BaseModel = declarative_base(metadata=metadata)


log = logging.getLogger(__name__)


class PublishLog(DomainObject, BaseModel):
    u"""
    An PublishLog object.
    """
    __tablename__ = 'publish_log'
    id = Column(types.UnicodeText, primary_key=True, default=_types.make_uuid)
    dataset_id = Column(types.UnicodeText, nullable=False)
    resource_id = Column(types.UnicodeText)
    trigger = Column(types.UnicodeText, nullable=False)
    destination = Column(types.UnicodeText)
    destination_identifier = Column(types.UnicodeText)
    action = Column(types.UnicodeText)
    date_created = Column(types.DateTime, default=datetime.datetime.utcnow())
    date_processed = Column(types.DateTime)
    status = Column(types.UnicodeText, nullable=False)
    details = Column(types.UnicodeText)

    # Available destination.
    destinations = [
        constants.PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA,
        constants.PUBLISH_EXTERNAL_IDENTIFIER_QSPATIAL_SCHEMA,
        constants.PUBLISH_EXTERNAL_IDENTIFIER_SIR_SCHEMA,
        constants.PUBLISH_EXTERNAL_IDENTIFIER_QLD_CDP_SCHEMA
    ]

    def __init__(self, dataset_id=None, resource_id=None, trigger=None, destination=None, destination_identifier=None,
                 action=None, status=None, details=None, date_processed=None):
        self.dataset_id = dataset_id
        self.resource_id = resource_id
        self.trigger = trigger
        self.destination = destination
        self.destination_identifier = destination_identifier
        self.action = action
        self.status = status
        self.details = details
        self.date_processed = date_processed

    @classmethod
    def get(cls, id):
        query = meta.Session.query(cls).filter(cls.id == id)
        return query.first()

    @classmethod
    def get_recent_resource_log(cls, resource_id, status=False, action=[], destination=None):
        query = meta.Session.query(cls) \
            .filter(cls.resource_id == resource_id) \
            .order_by(desc(cls.date_processed)) \
            .order_by(desc(cls.date_created))

        if status:
            query = query.filter(cls.status == status)

        if action:
            query = query.filter(cls.action.in_(tuple(action)))

        if destination:
            query = query.filter(cls.destination == destination)

        return query.first()

    @classmethod
    def has_published(cls, id, type='dataset'):
        published_log = {}
        for destination in cls.destinations:
            query = meta.Session.query(cls) \
                .filter(cls.action.in_(tuple([constants.PUBLISH_ACTION_UPDATE, constants.PUBLISH_ACTION_CREATE]))) \
                .filter(cls.status == constants.PUBLISH_STATUS_SUCCESS) \
                .filter(cls.destination == destination) \
                .order_by(desc(cls.date_processed))

            if type == 'dataset':
                query = query.filter(cls.dataset_id == id)
            elif type == 'resource':
                query = query.filter(cls.resource_id == id)

            publish_log = query.first()

            if publish_log and not cls.has_unpublished(publish_log, destination):
                # Check if this resource already unpublished.
                published_log[destination] = publish_log

        return published_log

    @classmethod
    def has_unpublished(cls, publish_log, destination):
        query = meta.Session.query(cls) \
            .filter(cls.resource_id == publish_log.resource_id) \
            .filter(cls.action == constants.PUBLISH_ACTION_DELETE) \
            .filter(cls.status == constants.PUBLISH_STATUS_SUCCESS) \
            .filter(cls.destination == destination)

        if publish_log.date_processed:
            query = query.filter(cls.date_processed > publish_log.date_processed)

        return query.first()

    @classmethod
    def get_published_distributions(cls, pkg):
        published_log = {}
        for destination in cls.destinations:
            published_log[destination] = []

        for resource in pkg.get('resources'):
            published_distributions = cls.has_published(resource.get('id'), 'resource')
            for destination in published_distributions:
                published_log[destination].append(published_distributions[destination])

        return published_log

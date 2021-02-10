import ckanext.qdes_schema.constants as constants
import datetime

from ckan.model import meta
from ckan.model import types as _types
from sqlalchemy import types, Column, Table
from ckan.model.domain_object import DomainObject
from sqlalchemy import desc

# Define publish_log table structure.
publish_log_table = Table(
    'publish_log', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('dataset_id', types.UnicodeText, nullable=False),
    Column('resource_id', types.UnicodeText),
    Column('trigger', types.UnicodeText, nullable=False),
    Column('destination', types.UnicodeText),
    Column('destination_identifier', types.UnicodeText),
    Column('action', types.UnicodeText),
    Column('date_created', types.DateTime, default=datetime.datetime.utcnow()),
    Column('date_processed', types.DateTime),
    Column('status', types.UnicodeText, nullable=False),
    Column('details', types.UnicodeText),
)


class PublishLog(DomainObject):
    u"""
    An PublishLog object.
    """

    def __init__(self, dataset_id=None, resource_id=None, trigger=None, destination=None, destination_identifier=None,
                 action=None, status=None, details=None):
        self.dataset_id = dataset_id
        self.resource_id = resource_id
        self.trigger = trigger
        self.destination = destination
        self.destination_identifier = destination_identifier
        self.action = action
        self.status = status
        self.details = details

    @classmethod
    def get(cls, id):
        query = meta.Session.query(cls).filter(cls.id == id)
        return query.first()

    @classmethod
    def get_recent_resource_log(cls, resource_id, status):
        query = meta.Session.query(cls) \
            .filter(cls.resource_id == resource_id) \
            .filter(cls.status == status) \
            .order_by(desc(cls.date_processed))
        return query.first()

    @classmethod
    def dataset_has_published_to_external(cls, dataset_id):
        query = meta.Session.query(cls) \
            .filter(cls.dataset_id == dataset_id) \
            .filter(cls.action.in_(tuple([constants.PUBLISH_ACTION_UPDATE, constants.PUBLISH_ACTION_CREATE]))) \
            .filter(cls.status == constants.PUBLISH_STATUS_SUCCESS) \
            .order_by(desc(cls.date_processed))
        return query.first()

    @classmethod
    def resource_has_published_to_external(cls, resource_id):
        query = meta.Session.query(cls) \
            .filter(cls.resource_id == resource_id) \
            .filter(cls.action.in_(tuple([constants.PUBLISH_ACTION_UPDATE, constants.PUBLISH_ACTION_CREATE]))) \
            .filter(cls.status == constants.PUBLISH_STATUS_SUCCESS) \
            .order_by(desc(cls.date_processed))
        return query.first()


meta.mapper(PublishLog, publish_log_table)

import logging
import ckan.plugins.toolkit as toolkit

from datetime import datetime
from ckanext.qdes_schema.model import PublishLog
from pprint import pformat

log = logging.getLogger(__name__)


def publish_log(context, data):
    u"""
    Create publish_log.
    """
    session = context['session']

    try:
        publish_log_data = PublishLog(**data)
        session.add(publish_log_data)
        session.commit()

        return publish_log_data
    except Exception as e:
        log.error(e)
        return None

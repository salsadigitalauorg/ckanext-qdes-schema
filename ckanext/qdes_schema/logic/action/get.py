import logging
import requests

from ckan.plugins.toolkit import get_action
from ckan import model
from ckan.model import meta

log = logging.getLogger(__name__)

def dataservice(context, name):
    """
    Returns all dataservice where private is false.
    """
    data = []

    try:
        cls = model.Package
        data = model.Package().Session.query(cls).filter(cls.type == 'dataservice').filter(cls.private == 'f').all()
    except Exception as e:
        log.error(str(e))

    return data
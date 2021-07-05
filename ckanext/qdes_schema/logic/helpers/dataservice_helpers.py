import logging
import json

from ckan.logic import NotFound
from ckan.plugins.toolkit import get_action

log = logging.getLogger(__name__)


def datasets_available_as_list(dataservice_dict):
    """
    Get the value of 'datasets_available' if the key exists in the dict
    or empty list ([]) if it does not exist OR is an empty string
    """
    datasets_available = dataservice_dict.get('datasets_available', None) or None

    if datasets_available:
        try:
            return json.loads(datasets_available)
        except json.JSONDecodeError as e:
            log.error('Unable to load json from datasets_available from data service ID %: ' % dataservice_dict['id'])
            log.error(str(e))

    return []

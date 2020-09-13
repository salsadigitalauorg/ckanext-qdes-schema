import json
import logging

from ckan.logic import NotFound
from ckan.plugins.toolkit import c, g, config, get_action, h

log = logging.getLogger(__name__)


def get_resource_package(context, pkg_id):
    try:
        return get_action('package_show')(context, {'id': pkg_id})
    except NotFound as e:
        log.error(str(e))
    return {}


def data_services_as_list(resource_dict):
    data_services_json = resource_dict.get('data_services', None) or None
    if data_services_json:
        try:
            # Will throw a json.JSONDecoder exception if not valid JSON
            return json.loads(data_services_json)
        except json.JSONDecodeError as e:
            log.error('Unable to load JSON from resource.data_services for resource ID %s.' % resource_dict['id'])
            log.error(str(e))
    return []

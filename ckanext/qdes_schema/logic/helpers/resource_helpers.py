import json
import logging

from ckan.logic import NotFound
from ckan.plugins.toolkit import c, g, config, get_action, h
from pprint import pformat

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


def after_create_and_update(context, resource):
    get_action('update_dataservice_datasets_available')(context, {'resource': resource})


def before_update(context, current, resource):
    # Get data_services that removed from current resource.
    new_data_services = data_services_as_list(resource)
    data_services_removed = []
    for current_dt in data_services_as_list(current):
        if not current_dt in new_data_services:
            data_services_removed.append(current_dt)

    if data_services_removed:
        pkg_dict = get_action('package_show')({}, {'id': current.get('package_id')})
        resources = pkg_dict.get('resources')
        for res in resources:
            if res.get('id') == resource.get('id'):
                get_action('update_dataservice_datasets_available')(context, {
                    'resource': res,
                    'resource_deleted': True,
                    'resources': resources,
                })


def before_delete(context, resource, resources):
    for res in resources:
        if res.get('id') == resource.get('id'):
            get_action('update_dataservice_datasets_available')(context, {
                'resource': res,
                'resource_deleted': True,
                'resources': resources,
            })

            get_action('delete_invalid_uri')({}, {
                'entity_type': 'resource',
                'entity_id': res.get('id'),
                'parent_entity_id': res.get('package_id')
            })


def delete_resource_dataservice(context, dataservice_id, datasets_available):
    for dataset_id in datasets_available:
        pkg_dict = get_action('package_show')(context, {'id': dataset_id})

        for resource in pkg_dict.get('resources', []):
            if dataservice_id in resource.get('data_services'):
                try:
                    data_services = json.loads(resource.get('data_services'))
                    data_services.remove(dataservice_id)

                    resource['data_services'] = json.dumps(data_services)

                    get_action('resource_update')(context, resource)
                except json.JSONDecodeError as e:
                    log.error(str(e))

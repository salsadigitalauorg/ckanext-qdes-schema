import ckan.plugins as plugins
import logging

from ckan.plugins.toolkit import get_action
from ckanext.qdes_schema.logic.helpers import resource_helpers as res_helpers

log = logging.getLogger(__name__)

class QDESSchemaResourcesPlugin(plugins.SingletonPlugin):
    """
    Separated into own plugin to avoid conflicts with
    IPackageController after_create and after_update functions
    when they are added to main `plugin.py` file
    """
    plugins.implements(plugins.IResourceController, inherit=True)

    def after_create(self, context, resource):
        get_action('update_dataservice_datasets_available')(context, {'resource': resource})

    def after_update(self, context, resource):
        get_action('update_dataservice_datasets_available')(context, {'resource': resource})

    def before_update(self, context, current, resource):
        # Get data_services that removed from current resource.
        new_data_services = res_helpers.data_services_as_list(resource)
        data_services_removed = []
        for current_dt in res_helpers.data_services_as_list(current):
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

    def before_delete(self, context, resource, resources):
        for res in resources:
            if res.get('id') == resource.get('id'):
                get_action('update_dataservice_datasets_available')(context, {
                    'resource': res,
                    'resource_deleted': True,
                    'resources': resources,
                })

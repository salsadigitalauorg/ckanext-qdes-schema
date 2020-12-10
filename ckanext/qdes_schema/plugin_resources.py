import ckan.plugins as plugins
import logging

from ckan.plugins.toolkit import get_action

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

    def before_delete(self, context, resource, resources):
        for res in resources:
            if res.get('id') == resource.get('id'):
                get_action('update_dataservice_datasets_available')(context, {
                    'resource': res,
                    'resource_deleted': True,
                    'resources': resources,
                })

import ckan.plugins as plugins

from ckan.plugins.toolkit import get_action


class QDESSchemaResourcesPlugin(plugins.SingletonPlugin):
    """
    Separated into own plugin to avoid conflicts with
    IPackageController after_create and after_update functions
    when they are added to main `plugin.py` file
    """
    plugins.implements(plugins.IResourceController, inherit=True)

    def after_create(self, context, resource):
        get_action('update_dataservice_datasets_available')(context, resource)

    def after_update(self, context, resource):
        get_action('update_dataservice_datasets_available')(context, resource)

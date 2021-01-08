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
        res_helpers.after_create_and_update(context, resource)

    def after_update(self, context, resource):
        res_helpers.after_create_and_update(context, resource)

    def before_update(self, context, current, resource):
        res_helpers.before_update(context, current, resource)

    def before_delete(self, context, resource, resources):
        res_helpers.before_delete(context, resource, resources)

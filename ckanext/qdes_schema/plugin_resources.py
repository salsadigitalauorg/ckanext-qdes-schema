import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import logging

from ckan.common import request
from ckan.plugins.toolkit import get_action
from ckanext.qdes_schema.logic.helpers import resource_helpers as res_helpers

h = toolkit.h
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

        if request and request.endpoint == 'resource.edit':
            if h.resource_has_published_to_external_schema(resource.get('id')):
                url = h.url_for('qdes_schema.datasets_schema_validation', id=resource.get('package_id'))
                h.flash_success('You have updated a dataset resource that is publicly available. Please go to the <a href="' + url +'">Publish tab</a> to validate the changes and publish to the relevant data service(s). This will ensure the metadata in updated in all systems.', True)

    def before_update(self, context, current, resource):
        res_helpers.before_update(context, current, resource)

    def before_delete(self, context, resource, resources):
        res_helpers.before_delete(context, resource, resources)

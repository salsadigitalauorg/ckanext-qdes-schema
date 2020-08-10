import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import json


class QDESSchemaPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'qdes_schema')

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'get_multi_textarea_values': self.get_multi_textarea_values,
        }

    def get_multi_textarea_values(self, value):
        return json.loads(value) if value else ['']

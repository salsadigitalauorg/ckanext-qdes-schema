import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import json

from ckanext.qdes_schema import helpers, validators

class QDESSchemaPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IValidators)

    # IConfigurer

    # IValidators
    def get_validators(self):
        return {
            'qdes_temporal_start_end_date': validators.qdes_temporal_start_end_date,
            'qdes_dataset_creation_date': validators.qdes_dataset_creation_date,
            'qdes_dataset_current_date_later_than_creation': validators.qdes_dataset_current_date_later_than_creation,
            'qdes_uri_validator': validators.qdes_uri_validator,
        }

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'qdes_schema')

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'get_multi_textarea_values': self.get_multi_textarea_values
        }

    def get_multi_textarea_values(self, value):
        return json.loads(value) if value else ['']

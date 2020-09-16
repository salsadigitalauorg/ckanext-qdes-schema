import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import json

from ckanext.qdes_schema import helpers, validators
from ckanext.qdes_schema.logic.action import get, update
from ckanext.relationships import helpers as ckanext_relationships_helpers


class QDESSchemaPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IPackageController, inherit=True)

    # IPackageController
    def after_update(self, context, pkg_dict):
        pass

    def after_create(self, context, pkg_dict):
        pass

    def before_index(self, pkg_dict):
        # Remove the relationship type fields from the pkg_dict to prevent indexing from breaking
        # because we removed the relationship type fields from solr schema.xml
        relationship_types = ckanext_relationships_helpers.get_relationship_types_as_flat_list()

        for relationship_type in relationship_types:
            if pkg_dict.get(relationship_type, None):
                pkg_dict.pop(relationship_type)

        return pkg_dict

    # IValidators
    def get_validators(self):
        return {
            'qdes_temporal_start_end_date': validators.qdes_temporal_start_end_date,
            'qdes_dataset_current_date_later_than_creation': validators.qdes_dataset_current_date_later_than_creation,
            'qdes_uri_validator': validators.qdes_uri_validator,
            'qdes_validate_decimal': validators.qdes_validate_decimal,
            'qdes_validate_geojson': validators.qdes_validate_geojson,
            'qdes_validate_geojson_point': validators.qdes_validate_geojson_point,
            'qdes_validate_geojson_polygon': validators.qdes_validate_geojson_polygon,
            'qdes_within_au_bounding_box': validators.qdes_within_au_bounding_box,
            'qdes_validate_geojson_spatial': validators.qdes_validate_geojson_spatial,
            'qdes_spatial_points_pair': validators.qdes_spatial_points_pair,
            'qdes_iso_8601_durations': validators.qdes_iso_8601_durations,
            'qdes_validate_multi_groups': validators.qdes_validate_multi_groups,
            'qdes_validate_related_dataset': validators.qdes_validate_related_dataset,
            'qdes_validate_related_resources': validators.qdes_validate_related_resources
        }

    # IConfigurer
    def update_config_schema(self, schema):
        ignore_missing = toolkit.get_validator('ignore_missing')
        qdes_validate_geojson = toolkit.get_validator('qdes_validate_geojson')

        schema.update({
            'ckanext.qdes_schema.au_bounding_box': [ignore_missing, qdes_validate_geojson],
        })

        return schema

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'qdes_schema')

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'get_multi_textarea_values': self.get_multi_textarea_values,
            'set_first_option': helpers.set_first_option,
            'get_current_datetime': helpers.get_current_datetime,
            'qdes_dataservice_choices': helpers.qdes_dataservice_choices,
            'qdes_relationship_types_choices': helpers.qdes_relationship_types_choices,
            'get_related_versions': helpers.get_related_versions
        }

    def get_multi_textarea_values(self, value):
        try:
            if len(value) > 0:
                return json.loads(value)
        except:
            pass

        return ['']

    # IActions
    def get_actions(self):
        return {
            'get_dataservice': get.dataservice,
            'package_autocomplete': get.package_autocomplete,
            'update_dataservice_datasets_available': update.dataservice_datasets_available,
            'get_all_successor_versions': get.all_successor_versions,
            'get_all_predecessor_versions': get.all_predecessor_versions
        }

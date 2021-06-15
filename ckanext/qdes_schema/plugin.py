import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import calendar
import json
import logging

from ckan.common import request
from ckan.logic import validators as core_validator
from ckanext.qdes_schema.cli import get_commands
from ckanext.qdes_schema import blueprint, helpers, validators, auth
from ckanext.qdes_schema.logic.action import (
    get,
    create,
    update,
    delete
)
from ckanext.relationships import helpers as ckanext_relationships_helpers
from ckanext.qdes_schema.logic.helpers import indexing_helpers, relationship_helpers, resource_helpers as res_helpers
from collections import OrderedDict
from pprint import pformat

h = toolkit.h
get_action = toolkit.get_action
log = logging.getLogger(__name__)


class QDESSchemaPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurable, inherit=True)
    plugins.implements(plugins.IClick)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IFacets, inherit=True)
    plugins.implements(plugins.IAuthFunctions)

    # IConfigurable
    def configure(self, config):
        core_validator.object_id_validators['publish external schema'] = core_validator.package_id_exists
        core_validator.object_id_validators['unpublish external schema'] = core_validator.package_id_exists

    # IClick
    def get_commands(self):
        return get_commands()

    # IBlueprint
    def get_blueprint(self):
        return blueprint.qdes_schema

    # IPackageController
    def after_create(self, context, pkg_dict):
        u'''
        Extensions will receive the validated data dict after the dataset
        has been created (Note that the create method will return a dataset
        domain object, which may not include all fields). Also the newly
        created dataset id will be added to the dict.
        '''
        helpers.update_related_resources(context, pkg_dict, False)

        # Remove `ignore_auth` from the context - in case it was set
        # lower in the chain, i.e. by ckanext-relationships
        # `package_relationship_create` auth function
        ignore_auth = context.get('ignore_auth', None)
        if ignore_auth:
            context.pop('ignore_auth')

        if request.endpoint == 'api.action' and request.view_args['logic_function'] == 'package_create':
            for resource in pkg_dict.get('resources', []):
                res_helpers.after_create_and_update(context, resource)

        return pkg_dict

    def after_update(self, context, pkg_dict):
        u'''
        Extensions will receive the validated data dict after the dataset
        has been updated.
        '''
        # Don't run this function when adding or editing a resource
        if toolkit.g and toolkit.g.controller == 'resource':
            return pkg_dict

        # Only reconcile relationships if the request has come from the Web UI form via the dataset controller
        # We do not want to reconcile relationships from the API
        reconcile_relationships = True if toolkit.g and toolkit.g.controller == 'dataset' else False
        helpers.update_related_resources(context, pkg_dict, reconcile_relationships)

        # Remove `ignore_auth` from the context - in case it was set
        # lower in the chain, i.e. by ckanext-relationships
        # `package_relationship_create` auth function
        ignore_auth = context.get('ignore_auth', None)
        if ignore_auth:
            context.pop('ignore_auth')

        for resource in pkg_dict.get('resources', []):
            res_helpers.after_create_and_update(context, resource)

        if request and request.endpoint == 'dataset.edit':
            if h.dataset_has_published_to_external_schema(pkg_dict.get('id')):
                url = h.url_for('qdes_schema.datasets_schema_validation', id=pkg_dict.get('id'))
                h.flash_success('You have updated a dataset that is publicly available. Please go to the <a href="' + url +
                                '">Publish tab</a> to validate the changes and publish to the relevant data service(s). This will ensure the metadata is updated in all systems.', True)

        return pkg_dict

    def before_index(self, pkg_dict):
        # Remove the relationship type fields from the pkg_dict to prevent indexing from breaking
        # because we removed the relationship type fields from solr schema.xml
        relationship_types = ckanext_relationships_helpers.get_relationship_types()

        for relationship_type in relationship_types:
            if pkg_dict.get(relationship_type, None):
                pkg_dict.pop(relationship_type)

        dataset_type = pkg_dict.get('dataset_type', None)

        if dataset_type:
            # Get collection_package_id for each dataset that part of collection.
            collection_package_id = indexing_helpers.get_collection_ids(pkg_dict)
            if collection_package_id:
                pkg_dict['collection_package_id'] = collection_package_id

            # Process the package's CKAN resources (aka "Data Access" (QDCAT), aka "Distribution" (DCAT))
            # The values stored in `res_format` are URIs for the vocabulary term
            # A new field was added to the solr schema.xml to store the labels of the resource formats
            if 'res_format' in pkg_dict:
                resource_format_labels = indexing_helpers.get_resource_format_labels(
                    dataset_type,
                    pkg_dict.get('res_format', None)
                )

                # If we have some resource format labels - include these in the
                # details being sent to Solr for indexing
                if resource_format_labels:
                    pkg_dict['resource_format_labels'] = resource_format_labels

            # "Topic or theme" terms are stored as URIs, so also need to be indexed
            # by their labels for searching on keyword
            if 'topic' in pkg_dict:
                topic_labels = indexing_helpers.convert_vocabulary_terms_json_to_labels(
                    dataset_type,
                    'topic',
                    pkg_dict.get('topic', '')
                )

                if topic_labels:
                    pkg_dict['topic_labels'] = topic_labels

            # Make license searchable via vocabulary term label
            if 'license_id' in pkg_dict:
                license_label = indexing_helpers.convert_license_uri_to_label(
                    dataset_type,
                    # Check `license_id` first, fall-back to `license` or None if empty string
                    pkg_dict.get('license_id', None) or pkg_dict.get('license', None) or None
                )

                if license_label:
                    pkg_dict['license_label'] = license_label

            # General classification.
            if 'classification' in pkg_dict:
                general_classification = indexing_helpers.convert_vocabulary_terms_json_to_labels(
                    dataset_type,
                    'classification',
                    pkg_dict.get('classification', '')
                )

                if general_classification:
                    pkg_dict['general_classification'] = general_classification

            # Publication status.
            if 'publication_status' in pkg_dict:
                publication_status_label = indexing_helpers.convert_term_uri_to_label(
                    dataset_type,
                    'publication_status',
                    pkg_dict.get('publication_status', '')
                )

                if publication_status_label:
                    pkg_dict['publication_status_label'] = publication_status_label

            # Access restriction.
            if 'classification_and_access_restrictions' in pkg_dict:
                classification_and_access_restrictions_label = indexing_helpers.convert_vocabulary_terms_json_to_labels(
                    dataset_type,
                    'classification_and_access_restrictions',
                    pkg_dict.get('classification_and_access_restrictions', '')
                )

                if classification_and_access_restrictions_label:
                    pkg_dict['classification_and_access_restrictions_label'] = classification_and_access_restrictions_label

            # Service status.
            if 'service_status' in pkg_dict:
                service_status_label = indexing_helpers.convert_term_uri_to_label(
                    dataset_type,
                    'service_status',
                    pkg_dict.get('service_status', '')
                )

                if service_status_label:
                    pkg_dict['service_status_label'] = service_status_label

            # Standards.
            if 'standards' in pkg_dict:
                standards_label = indexing_helpers.convert_vocabulary_terms_json_to_labels(
                    dataset_type,
                    'standards',
                    pkg_dict.get('standards', '')
                )

                if standards_label:
                    pkg_dict['standards_label'] = standards_label

        return pkg_dict

    def before_search(self, search_params):
        temporal_coverage_from = request.params.get('temporal_coverage_from', '') or ''
        temporal_coverage_to = request.params.get('temporal_coverage_to', '') or ''

        if 'fq' in search_params:
            # Clean up fq params from temporal start end.
            search_params['fq'] = search_params['fq'].replace('temporal_coverage_from:"' + temporal_coverage_from + '"', '')
            search_params['fq'] = search_params['fq'].replace('temporal_coverage_to:"' + temporal_coverage_to + '"', '')

            if temporal_coverage_from and not temporal_coverage_to:
                search_params['fq'] += ' +temporal_start:[' + temporal_coverage_from + ' TO *]'

            if temporal_coverage_from and temporal_coverage_to:
                # Need to make sure to use the last day of the selected month,
                # otherwise solr will assume this is the first day.
                to_date = temporal_coverage_to.split('-')
                last_day = calendar.monthrange(int(to_date[0]), int(to_date[1]))[1]
                temporal_coverage_to = temporal_coverage_to + '-' + str(last_day)

                search_params['fq'] += ' +temporal_start:[' + temporal_coverage_from + ' TO ' + temporal_coverage_to + ']'
                search_params['fq'] += '+temporal_end:[' + temporal_coverage_from + ' TO ' + temporal_coverage_to + ']'

        return search_params

    def delete(self, pkg_dict):
        get_action('delete_invalid_uri')({}, {
            'entity_type': 'dataset',
            'entity_id': pkg_dict.id,
        })

        get_action('delete_invalid_uri')({}, {
            'entity_type': 'resource',
            'parent_entity_id': pkg_dict.id,
        })

    # IValidators
    def get_validators(self):
        return {
            'qdes_temporal_start_end_date': validators.qdes_temporal_start_end_date,
            'qdes_dataset_current_date_later_than_creation': validators.qdes_dataset_current_date_later_than_creation,
            'qdes_dataset_last_modified_date_before_today': validators.qdes_dataset_last_modified_date_before_today,
            'qdes_uri_validator': validators.qdes_uri_validator,
            'qdes_validate_decimal': validators.qdes_validate_decimal,
            'qdes_validate_decimal_positive': validators.qdes_validate_decimal_positive,
            'qdes_validate_geojson': validators.qdes_validate_geojson,
            'qdes_validate_geojson_point': validators.qdes_validate_geojson_point,
            'qdes_validate_geojson_polygon': validators.qdes_validate_geojson_polygon,
            'qdes_within_au_bounding_box': validators.qdes_within_au_bounding_box,
            'qdes_validate_geojson_spatial': validators.qdes_validate_geojson_spatial,
            'qdes_spatial_points_pair': validators.qdes_spatial_points_pair,
            'qdes_iso_8601_durations': validators.qdes_iso_8601_durations,
            'qdes_validate_multi_groups': validators.qdes_validate_multi_groups,
            'qdes_validate_related_dataset': validators.qdes_validate_related_dataset,
            'qdes_validate_related_resources': validators.qdes_validate_related_resources,
            'qdes_validate_metadata_review_date': validators.qdes_validate_metadata_review_date,
            'qdes_convert_related_resources': relationship_helpers.convert_related_resources,
        }

    # IConfigurer
    def update_config_schema(self, schema):
        ignore_missing = toolkit.get_validator('ignore_missing')
        qdes_validate_geojson = toolkit.get_validator('qdes_validate_geojson')

        schema.update({
            'ckanext.qdes_schema.au_bounding_box': [ignore_missing, qdes_validate_geojson],
            'ckanext.qdes_schema.qld_bounding_box': [ignore_missing, qdes_validate_geojson],
            'ckanext.qdes_schema.default_map_zoom': [ignore_missing],
            'ckanext.qdes_schema.publishing_portals.opendata': [ignore_missing],
            'ckanext.qdes_schema.publishing_portals.qspatial': [ignore_missing],
            'ckanext.qdes_schema.publishing_portals.sir': [ignore_missing],
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
            'get_related_versions': helpers.get_related_versions,
            'get_superseded_versions': relationship_helpers.get_superseded_versions,
            'has_newer_version': relationship_helpers.has_newer_version,
            'get_all_relationships': helpers.get_all_relationships,
            'convert_relationships_to_related_resources': helpers.convert_relationships_to_related_resources,
            'get_qld_bounding_box_config': helpers.get_qld_bounding_box_config,
            'get_default_map_zoom': helpers.get_default_map_zoom,
            'get_package_dict': helpers.get_package_dict,
            'get_invalid_uris': helpers.get_invalid_uris,
            'wrap_url_within_text_as_link': helpers.wrap_url_within_text_as_link,
            'get_series_relationship': helpers.get_series_relationship,
            'is_collection': helpers.is_collection,
            'is_part_of_collection': helpers.is_part_of_collection,
            'qdes_get_field_label': helpers.qdes_get_field_label,
            'qdes_merge_invalid_uris_error': helpers.qdes_merge_invalid_uris_error,
            'schema_validate': helpers.schema_validate,
            'schema_publish': helpers.schema_publish,
            'load_activity_with_full_data': helpers.load_activity_with_full_data,
            'map_update_schedule': helpers.map_update_schedule,
            'dataset_has_published_to_external_schema': helpers.dataset_has_published_to_external_schema,
            'resource_has_published_to_external_schema': helpers.resource_has_published_to_external_schema,
            'get_publish_activities': helpers.get_publish_activities,
            'get_distribution_naming': helpers.get_distribution_naming,
            'get_published_distributions': helpers.get_published_distributions,
            'get_state_list': helpers.get_state_list,
            'get_pkg_title': helpers.get_pkg_title,
            'get_collection_parent_title': relationship_helpers.get_collection_parent_title,
            'get_external_distribution_url': helpers.get_external_distribution_url,
            'has_display_group_required_fields': helpers.has_display_group_required_fields,
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
            'update_related_resources': update.update_related_resources,
            'get_all_successor_versions': get.all_successor_versions,
            'get_all_predecessor_versions': get.all_predecessor_versions,
            'get_all_relationships': get.all_relationships,
            'create_publish_log': create.publish_log,
            'update_publish_log': update.publish_log,
            'dataservice_purge': delete.dataservice_purge,
            'dataset_purge': delete.dataset_purge
        }

    # IFacets
    def dataset_facets(self, facets_dict, package_type):

        # Remove the default facets we don't want
        if 'license_id' in facets_dict:
            facets_dict.pop('license_id')
        if 'tags' in facets_dict:
            facets_dict.pop('tags')
        if 'groups' in facets_dict:
            facets_dict.pop('groups')
        if 'organization' in facets_dict:
            facets_dict.pop('organization')

        facets_dict['collection_package_id'] = 'Collections'
        facets_dict['type'] = plugins.toolkit._('Dataset or Data service')
        facets_dict['general_classification'] = plugins.toolkit._('General classification')
        facets_dict['topic_labels'] = plugins.toolkit._('Topic or theme')
        facets_dict['publication_status_label'] = plugins.toolkit._('Status')
        facets_dict['service_status_label'] = plugins.toolkit._('Status')
        facets_dict['classification_and_access_restrictions_label'] = plugins.toolkit._('Access restrictions')
        facets_dict['resource_format_labels'] = plugins.toolkit._('Primary format')
        facets_dict['standards_label'] = plugins.toolkit._('Data service standards')
        facets_dict['temporal_start'] = plugins.toolkit._('Temporal start')
        facets_dict['temporal_end'] = plugins.toolkit._('Temporal end')
        facets_dict['temporal_coverage_from'] = plugins.toolkit._('Temporal coverage from')
        facets_dict['temporal_coverage_to'] = plugins.toolkit._('Temporal coverage to')

        # Reorder facets.
        if facets_dict:
            if package_type == 'dataset':
                facets_order = [
                    'general_classification',
                    'topic_labels',
                    'temporal_start',
                    'temporal_end',
                    'publication_status_label',
                    'classification_and_access_restrictions_label',
                    'resource_format_labels',
                    'type',
                    'collection_package_id',
                    'temporal_coverage_from',
                    'temporal_coverage_to'
                ]
                ordered_facets = OrderedDict((k, facets_dict[k]) for k in facets_order)
            else:
                facets_order = [
                    'general_classification',
                    'topic_labels',
                    'service_status_label',
                    'classification_and_access_restrictions_label',
                    'standards_label',
                    'collection_package_id',
                ]
                ordered_facets = OrderedDict((k, facets_dict[k]) for k in facets_order)

            return ordered_facets

    # IAuthFunctions
    def get_auth_functions(self):
        return {
            'package_show': auth.package_show,
            'package_create': auth.package_create,
            'package_update': auth.package_update,
            'package_patch': auth.package_patch,
            'package_delete': auth.package_delete,
            'dataservice_index': auth.dataservice_index,
        }

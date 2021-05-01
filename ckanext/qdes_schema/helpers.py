import ckan.logic as logic
import ckan.plugins.toolkit as toolkit
import ckanext.qdes_schema.constants as constants
import ckanext.qdes_schema.jobs as jobs
import json
import re
import datetime
import logging
import os

from ckan import model
from ckan.common import c
from ckan.model.package_relationship import PackageRelationship
from ckan.lib import helpers as core_helper
from ckan.lib.helpers import render_datetime
from ckan.plugins.toolkit import config, h, get_action, get_converter, get_validator, Invalid, request, _
from ckanext.qdes_schema.model import PublishLog
from ckanext.qdes_schema.logic.helpers import relationship_helpers
from ckanext.invalid_uris.model import InvalidUri
from ckanext.scheming.plugins import SchemingDatasetsPlugin
from pprint import pformat

Session = model.Session
log = logging.getLogger(__name__)
h = toolkit.h


def is_legacy_ckan():
    return False if h.ckan_version() > '2.9' else True


def set_first_option(options, first_option):
    """Find the option (case insensitive) from the options text property and move it to the start of the list at index 0"""
    option = next((option for option in options if option.get('text').lower() == first_option.lower()), None)
    if option:
        old_index = options.index(option)
        options.insert(0, options.pop(old_index))
    return options


def get_current_datetime():
    """
    Returns current datetime.
    """
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')


def qdes_dataservice_choices(field=None):
    """
    Return choices for dataservice dropdown.
    """
    choices = []

    try:
        for data in get_action('get_dataservice')({}):
            choices.append({
                'value': data.id,
                'label': data.title
            })
    except Exception as e:
        log.error(str(e))

    return choices


def qdes_relationship_types_choices(field):
    """
    Return choices for dataset relationship types.
    """
    def search_term_definition(terms, search_string):
        for term in terms:
            if search_string.lower() in term['label'].lower():
                return term['title']

        return ''

    choices = []

    try:
        # Remove the duplicate `unspecified relationship` type
        # as it has the same value for forward and reverse
        unique_relationship_types = []

        types = PackageRelationship.get_forward_types()

        nature_of_relationship = []
        for term in get_action('get_vocabulary_service_terms')({}, 'nature-of-relationship'):
            nature_of_relationship.append({'uri': term.uri, 'label': term.label, 'title': term.definition})

        for relationship_type in h.get_relationship_types():
            if relationship_type not in types:
                continue

            if relationship_type not in unique_relationship_types:
                unique_relationship_types.append(relationship_type)

        for data in unique_relationship_types:
            choices.append({
                'value': data,
                'label': data,
                'title': search_term_definition(nature_of_relationship, data)
            })
    except Exception as e:
        log.error(str(e))

    return choices


def update_related_resources(context, pkg_dict, reconcile_relationships=False):
    if reconcile_relationships:
        # Combine existing related_resources and new related_resources together
        existing_related_resources = []
        if request:
            existing_related_resources = get_converter('json_or_string')(request.form.get('existing_related_resources', '')) or []
        new_related_resources = get_converter('json_or_string')(pkg_dict.get('related_resources', '')) or []
        combined_related_resources = existing_related_resources + new_related_resources
        pkg_dict['related_resources'] = h.dump_json(combined_related_resources)

        remove_duplicate_related_resources(pkg_dict)
        reconcile_package_relationships(context, pkg_dict['id'], pkg_dict.get('related_resources', None))

    if pkg_dict.get('type') == 'dataset':
        create_related_relationships(context, pkg_dict, 'series_or_collection', 'Is Part Of')
        create_related_relationships(context, pkg_dict, 'related_datasets', 'unspecified relationship')
    elif pkg_dict.get('type') == 'dataservice':
        create_related_relationships(context, pkg_dict, 'related_services', 'unspecified relationship')

    create_related_resource_relationships(context, pkg_dict)
    get_action('update_related_resources')(context, {"id": pkg_dict.get('id')})


# @TODO: This should be renamed to something more appropriate to what it does, i.e. "stage|build|add_related_resources"
# and could probably just be absorbed into the `set_pkg_related_resources` function below
def create_related_relationships(context, pkg_dict, metadata_field, relationship_type):
    resources = get_converter('json_or_string')(pkg_dict.get(metadata_field, []))
    set_pkg_related_resources(pkg_dict, resources, relationship_type)


def set_pkg_related_resources(pkg_dict, resources, relationship_type):
    if resources and isinstance(resources, list):
        pkg_related_resources = get_converter('json_or_string')(pkg_dict.get('related_resources', []))
        if not pkg_related_resources:
            pkg_related_resources = []

        for resource in resources:
            # Only add `resource` to `related_resources` if it does not already exist
            if not any(x for x in pkg_related_resources
                       if x.get('resource', {}).get('id', '') == resource.get('id', '')
                       and x.get('relationship', '') == relationship_type):
                pkg_related_resources.append({
                    'resource': resource,
                    'relationship': relationship_type
                })

        pkg_dict['related_resources'] = h.dump_json(pkg_related_resources)


def create_related_resource_relationships(context, pkg_dict):
    remove_duplicate_related_resources(pkg_dict)
    pkg_related_resources = get_converter('json_or_string')(pkg_dict.get('related_resources', []))
    if pkg_related_resources and isinstance(pkg_related_resources, list):
        create_package_relationship_records(context, pkg_dict.get('id'), pkg_related_resources)


def create_package_relationship_records(context, pkg_id, pkg_related_resources):
    try:
        for resource in pkg_related_resources:
            relationship_type = resource.get('relationship')
            object_package_id, url = get_related_object_or_url(context, resource.get('resource'))

            if object_package_id or url:
                # Pre-check to see if a `package_relationship` already exists for this `subject_package_id`,
                # `object_package_id` and `type`, because it's possible that a sysadmin user added a
                # relationship to a package that an admin or editor user does not have `package_update` permission
                if object_package_id and \
                        relationship_helpers.get_existing_relationship(pkg_id, object_package_id, relationship_type):
                    continue

                # Upsert the `package_relationship`
                get_action('package_relationship_create')(context, {
                    'subject': pkg_id,
                    'object': object_package_id,
                    'type': relationship_type,
                    'comment': url,
                })
    except Exception as e:
        log.error('create_package_relationship_records error: {0}'.format(e), exc_info=True)
        raise


def get_related_object_or_url(context, resource):
    object_package_id = None
    url = None
    resource_id = resource.get('id', '')
    try:
        get_validator('package_id_exists')(resource_id, context)
        object_package_id = resource_id
    except Exception as e:
        # Dataset does not exist so must be an external dataset URL
        # Validation should have already happened in validator 'qdes_validate_related_dataset'
        # so the `resource` should be a URL to external dataset
        url = resource_id
        log.error(str(e))

    return object_package_id, url


def reconcile_package_relationships(context, pkg_id, related_resources):
    """
    Only delete package relationships for the dataset when the relationship
    no longer exists in the `related_resources` field

    Called on IPackageController `after_update`

    :param context:
    :param pkg_id: package/dataset ID
    :return:
    """
    model = context.get('model')
    existing_relationships = get_action('subject_package_relationship_objects')(context, {'id': pkg_id})

    # `related_resources` might be an empty string
    related_resources = related_resources or None

    # If `related_resources` is empty - it indicates that all related resources have been removed from the dataset
    if not related_resources:
        # Delete ALL existing relationships for this dataset
        log.debug('Deleting ALL package_relationship records for dataset id {0}'.format(pkg_id))
        get_action('package_relationship_delete_all')(context, {'id': pkg_id})
    else:
        # Convert the `related_resources` JSON string into a more usable structure
        related_resources = get_converter('json_or_string')(related_resources)
        # Check each existing relationship to see if it still exists in the dataset's related_resources
        # if not, delete it.
        for relationship in existing_relationships:
            matching_related_resource = None

            # If it's an external URI we can process straight away
            if not relationship.object_package_id:
                matching_related_resource = [resource for resource in related_resources
                                             if resource.get('relationship', None) == relationship.type
                                             and resource.get('resource', {}).get('id', None) == relationship.comment]
            else:
                try:
                    matching_related_resource = [resource for resource in related_resources
                                                 if resource.get('relationship', None) == relationship.type
                                                 and resource.get('resource', {}).get('id', None) == relationship.object_package_id]
                except Exception as e:
                    log.error(str(e))

            if not matching_related_resource:
                # Delete the existing relationship from `package_relationships` as it no longer exists in the dataset
                log.debug('Purging relationship: Subject {0} - Object {1} - Type {2} - Comment {3}'
                          .format(relationship.subject_package_id, relationship.object_package_id, relationship.type, relationship.comment))
                relationship.purge()
                model.meta.Session.commit()


def remove_duplicate_related_resources(pkg_dict):
    related_resources = get_converter('json_or_string')(pkg_dict.get('related_resources', []))
    if related_resources and isinstance(related_resources, list):
        distinct_list = []
        for related_resource in related_resources:
            dataset_id = related_resource.get('resource', {}).get('id', '')
            relationship_type = related_resource.get('relationship', '')

            if not any(distinct_dataset for distinct_dataset in distinct_list
                       if distinct_dataset.get('resource', {}).get('id', '') == dataset_id
                       and distinct_dataset.get('relationship', '') == relationship_type):
                distinct_list.append(related_resource)

        pkg_dict['related_resources'] = h.dump_json(distinct_list)


def get_related_versions(id):
    """
    Get related versions of dataset, index 0 is the current version.
    """
    successors = get_action('get_all_successor_versions')({}, {'id': id})
    predecessors = get_action('get_all_predecessor_versions')({}, {'id': id})

    versions = []
    try:
        # Load provided version.
        package_dict = get_action('package_show')({}, {'id': id})

        # Build versions list.
        versions = successors + [package_dict] + predecessors
    except Exception as e:
        log.error(str(e))

    return list(version for version in versions)


def get_all_relationships(id):
    return get_action('get_all_relationships')({}, id)


def convert_relationships_to_related_resources(relationships):
    related_resources = []
    for relationship in relationships:
        id = relationship.get('object', None) or relationship.get('comment', None)
        related_resources.append({"resource": {"id": id}, "relationship": relationship.get('type', None)})

    return h.dump_json(related_resources) if related_resources and len(related_resources) > 0 else ''


def get_qld_bounding_box_config():
    return config.get('ckanext.qdes_schema.qld_bounding_box', None)


def get_default_map_zoom():
    return config.get('ckanext.qdes_schema.default_map_zoom', None) or 5


def get_package_dict(id):
    try:
        return get_action('package_show')({}, {'id': id})
    except Exception as e:
        log.error(str(e))


def get_invalid_uris(entity_id, pkg_dict):
    u"""
    Get invalid uris for the current package.
    """
    uris = Session.query(InvalidUri).filter(InvalidUri.entity_id == entity_id).all()

    return [uri.as_dict() for uri in uris]


def wrap_url_within_text_as_link(value):
    urlfinder = re.compile("(https?:[;\/?\\@&=+$,\[\]A-Za-z0-9\-_\.\!\~\*\'\(\)%][\;\/\?\:\@\&\=\+\$\,\[\]A-Za-z0-9\-_\.\!\~\*\'\(\)%#\{\}]*|[KZ]:\\*.*\w+)")

    return urlfinder.sub(r'<a href="\1">\1</a>', value)


def get_series_relationship(package):
    """
    Return package series relationship.
    """
    # Get all relationship.
    relationships = get_all_relationships(package.get('id'))

    # Group hasPart/isPartOf relationship.
    has_part = []
    is_part_of = []
    for relationship in relationships:
        type = relationship.get('type')
        if type == 'Has Part':
            has_part.append(relationship)
        elif type == 'Is Part Of':
            is_part_of.append(relationship)

    return {'Has Part': has_part, 'Is Part Of': is_part_of}


def is_collection(series_relationship):
    if series_relationship.get('Has Part'):
        return True

    return False


def is_part_of_collection(series_relationship):
    if series_relationship.get('Is Part Of'):
        return True

    return False


def qdes_get_field_label(field_name, schema, field='dataset_fields'):
    for field in schema.get(field):
        if field.get('field_name') == field_name:
            return field.get('label')


def qdes_merge_invalid_uris_error(invalid_uris, field_name, current_errors, error='The URL could not be validated'):
    error = _(error)
    for uri in invalid_uris:
        if uri.get('field') == field_name:
            if field_name in current_errors:
                current_errors[field_name].append(str(error))
            else:
                current_errors[field_name] = [str(error)]

            current_errors[field_name] = list(set(current_errors[field_name]))

    return current_errors


def schema_validate(extra_vars, pkg_validated, data):
    res_errors = []
    for selected_opt in extra_vars['options']:
        if selected_opt.get('value') == data.get('schema'):
            extra_vars['selected_opt'] = selected_opt

    context = {
        'model': model,
        'session': Session,
        'user': c.user,
        'for_view': True,
        'ignore_auth': True,
        'auth_user_obj': c.userobj
    }
    p = SchemingDatasetsPlugin.instance
    schema = logic.schema.default_update_package_schema()
    pkg_validated['type'] = data.get('schema')
    pkg_data, pkg_errors = p.validate(context, pkg_validated, schema, 'package_update')
    if pkg_errors.get('resources', None):
        pkg_errors.pop('resources')

    # Validate resource, the above code will validate resource
    # but it has no indication which resource is throwing an error,
    # so we will re-run the validation for each resource.
    resources = pkg_validated.get('resources', [])
    if resources:
        pkg_validated.pop('resources')
        for res in resources:
            if res.get('id') in data.get('resources', []):
                pkg_validated['resources'] = [res]
                pkg_data, resource_errors = p.validate(context, pkg_validated, schema, 'package_update')
                if resource_errors.get('resources', None):
                    res_errors.append({
                        'resource_id': res.get('id'),
                        'resource_name': res.get('name'),
                        'errors': resource_errors.get('resources')
                    })

                # Only add validation error/success if the dataset is published.
                if resource_has_published_to_external_schema(res.get('id'), data.get('schema')):
                    if resource_errors.get('resources', None):
                        get_action('create_publish_log')({}, {
                            'dataset_id': res.get('package_id'),
                            'resource_id': res.get('id'),
                            'trigger': constants.PUBLISH_TRIGGER_MANUAL,
                            'destination': data.get('schema'),
                            'status': constants.PUBLISH_STATUS_VALIDATION_ERROR,
                            'date_processed': datetime.datetime.utcnow(),
                            'details': json.dumps({'validation_error': resource_errors.get('resources')})
                        })
                    else:
                        get_action('create_publish_log')({}, {
                            'dataset_id': res.get('package_id'),
                            'resource_id': res.get('id'),
                            'trigger': constants.PUBLISH_TRIGGER_MANUAL,
                            'destination': data.get('schema'),
                            'status': constants.PUBLISH_STATUS_VALIDATION_SUCCESS,
                            'date_processed': datetime.datetime.utcnow()
                        })

    extra_vars['pkg_errors'] = pkg_errors
    extra_vars['res_errors'] = res_errors

    return extra_vars


def schema_publish(pkg, data):
    # Get resources that will be published.
    resources_to_publish = []
    for resource in pkg.get('resources', []):
        if resource.get('id') in data.get('resources', []):
            resources_to_publish.append(resource)

    # Add to publish log.
    try:
        for resource in resources_to_publish:
            publish_log = get_action('create_publish_log')({}, {
                'dataset_id': pkg.get('id'),
                'resource_id': resource.get('id'),
                'trigger': constants.PUBLISH_TRIGGER_MANUAL,
                'destination': data.get('schema'),
                'status': constants.PUBLISH_STATUS_PENDING
            })

            # Add to job worker queue.
            if publish_log:
                toolkit.enqueue_job(jobs.publish_to_external_catalogue, [publish_log.id, c.user])

        return True
    except Exception as e:
        log.error(str(e))
        return False


def load_activity_with_full_data(activity_id):
    site_user = get_action(u'get_site_user')({u'ignore_auth': True}, {})
    context = {u'user': site_user[u'name']}
    return get_action(u'activity_show')(context, {u'id': activity_id, u'include_data': True})


def map_update_schedule(uri, schema):
    frequency_map = {
        constants.PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA: {
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/annually': 'annually',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/asNeeded': 'non-regular',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/biannually': 'half-yearly',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/biennially': 'non-regular',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/continual': 'near-realtime',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/daily': 'daily',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/fortnightly': 'fortnightly',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/irregular': 'non-regular',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/monthly': 'monthly',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/notPlanned': 'not-updated',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/periodic': 'non-regular',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/quarterly': 'quarterly',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/semimonthly': 'fortnightly',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/unknown': 'not-updated',
            'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/weekly': 'weekly',
        },
        # @todo, in case needed, need to map this against external schema in future.
        constants.PUBLISH_EXTERNAL_IDENTIFIER_QSPATIAL_SCHEMA: {},
        constants.PUBLISH_EXTERNAL_IDENTIFIER_SIR_SCHEMA: {}
    }

    return frequency_map.get(schema, {}).get(uri, '')


def map_license(uri, schema):
    license_map = {
        constants.PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA: {
            'http://linked.data.gov.au/def/licence-document/cc-by-4.0': 'cc-by-4',
            'http://linked.data.gov.au/def/licence-document/cc-by-nd-4.0': 'cc-by-nd-4',
            'http://linked.data.gov.au/def/licence-document/cc-by-sa-4.0': 'cc-by-sa-4'
        },
        # @todo, in case needed, need to map this against external schema in future.
        constants.PUBLISH_EXTERNAL_IDENTIFIER_QSPATIAL_SCHEMA: {},
        constants.PUBLISH_EXTERNAL_IDENTIFIER_SIR_SCHEMA: {}
    }

    return license_map.get(schema, {}).get(uri, '')


def dataset_has_published_to_external_schema(package_id, schema=None):
    return PublishLog.has_published(package_id, 'dataset')


def resource_has_published_to_external_schema(resource_id, schema=None):
    return PublishLog.has_published(resource_id, 'resource')


def get_distribution_naming(pkg, resource):
    schema = h.scheming_get_dataset_schema(pkg.get('type'))

    for field in schema.get('resource_fields', []):
        if field.get('field_name') == 'format':
            format_field = field
            return h.scheming_choices_label(h.scheming_field_choices(format_field), resource.get('format')) + ' - ' + resource.get('name')

    return resource.get('name')


def get_last_success_publish_date(resource):
    last_success_log = PublishLog.get_recent_resource_log(
        resource.get('id'),
        constants.PUBLISH_STATUS_SUCCESS,
        [
            constants.PUBLISH_ACTION_UPDATE,
            constants.PUBLISH_ACTION_CREATE
        ]
    )

    processed_date = None
    if last_success_log:
        processed_date = last_success_log.date_processed

    return processed_date


def resource_needs_republish(resource, pkg, publish_log):
    res_metadata_modified = resource.get('metadata_modified', None)
    if not res_metadata_modified:
        return False

    res_metadata_modified_date = datetime.datetime.strptime(res_metadata_modified, '%Y-%m-%dT%H:%M:%S.%f')
    processed_date = publish_log.date_processed

    # Determine if this the status is need republish.
    if publish_log.date_processed and res_metadata_modified_date > processed_date:
        return True

    if publish_log.status == constants.PUBLISH_STATUS_VALIDATION_SUCCESS:
        return True

    if publish_log.status == constants.PUBLISH_STATUS_PENDING:
        return False

    return False


def dataset_need_republish(pkg):
    pkg_metadata_modified = pkg.get('metadata_modified', None)
    if not pkg_metadata_modified:
        return False

    pkg_metadata_modified_date = datetime.datetime.strptime(pkg_metadata_modified, '%Y-%m-%dT%H:%M:%S.%f')

    has_pending = False
    has_updated_resource = False
    most_recent_updated_resource = None
    for resource in pkg.get('resources', []):
        res_publish_log = PublishLog.get_recent_resource_log(resource.get('id'))
        if not res_publish_log:
            continue

        if res_publish_log.date_processed:
            if resource_needs_republish(resource, pkg, res_publish_log):
                has_updated_resource = True

        if res_publish_log.status == constants.PUBLISH_STATUS_PENDING:
            has_pending = True

        if res_publish_log.date_processed:
            if not most_recent_updated_resource or most_recent_updated_resource < res_publish_log.date_processed:
                most_recent_updated_resource = res_publish_log.date_processed
        elif res_publish_log.date_created:
            if not most_recent_updated_resource or most_recent_updated_resource < res_publish_log.date_created:
                most_recent_updated_resource = res_publish_log.date_created

    if not has_updated_resource and not has_pending and pkg_metadata_modified_date > most_recent_updated_resource:
        return True

    return False


def get_publish_activity_status(publish_logs, resource, pkg, details):
    status = constants.PUBLISH_LOG_PENDING
    if publish_logs.status == constants.PUBLISH_STATUS_SUCCESS and not publish_logs.action == constants.PUBLISH_ACTION_DELETE:
        status = constants.PUBLISH_LOG_PUBLISHED

    if publish_logs.status == constants.PUBLISH_STATUS_SUCCESS and publish_logs.action == constants.PUBLISH_ACTION_DELETE:
        status = constants.PUBLISH_LOG_UNPUBLISHED

    if publish_logs.status == constants.PUBLISH_STATUS_FAILED:
        if publish_logs.action == constants.PUBLISH_ACTION_DELETE:
            status = constants.PUBLISH_LOG_UNPUBLISH_ERROR
        else:
            status = constants.PUBLISH_LOG_PUBLISH_ERROR

    if publish_logs.status == constants.PUBLISH_STATUS_VALIDATION_ERROR:
        status = constants.PUBLISH_LOG_VALIDATION_ERROR

    if not publish_logs.status == constants.PUBLISH_STATUS_PENDING \
            and not publish_logs.action == constants.PUBLISH_ACTION_DELETE \
            and (resource_needs_republish(resource, pkg, publish_logs) or dataset_need_republish(pkg)):
        # For publish error that cause by the external dataset is deleted (in trash),
        # don't change the status.
        if details and not details.get('external_distribution_deleted', False):
            status = constants.PUBLISH_LOG_NEED_REPUBLISH

    return status

def get_publish_activities(pkg):
    resource_publish_logs = []

    for resource in pkg.get('resources'):
        # @todo, for multiple portals, modify below statement
        # maybe add more parameter called `portal` to get_recent_resource_log(),
        # and do looping for all available portals.
        # Currently only returning single portal for each resources.
        resource_publish_log = PublishLog.get_recent_resource_log(resource.get('id'))
        if resource_publish_log:
            # Get last success published date.
            published_date = ''
            unpublished_date = ''
            date_format = '%d/%m/%Y %H:%M:%S'
            processed_date = ''
            processed_unpublished_date = ''
            if resource_publish_log.status == constants.PUBLISH_STATUS_SUCCESS:
                processed_date = resource_publish_log.date_processed
            elif resource_publish_log.status == constants.PUBLISH_STATUS_FAILED:
                # If failed, get the last success published date.
                processed_date = get_last_success_publish_date(resource)

            # Get detail.
            try:
                details = json.loads(resource_publish_log.details)
            except Exception as e:
                log.warning('get_publish_activities json.loads error: {0}'.format(e))
                log.warning('{0}'.format(resource_publish_log))
                details = {}

            # Get status.
            status = get_publish_activity_status(resource_publish_log, resource, pkg, details)

            # If status validation success, keep the last status.
            if resource_publish_log.status == constants.PUBLISH_STATUS_VALIDATION_SUCCESS and status == constants.PUBLISH_LOG_PENDING and resource_has_published_to_external_schema(resource.get('id'), resource_publish_log.destination):
                status = constants.PUBLISH_LOG_PUBLISHED

            # Get published and unpublished date for distribution that unpublished.
            if status == constants.PUBLISH_LOG_UNPUBLISHED:
                # Get last published date.
                processed_date = get_last_success_publish_date(resource)

                # Get unpublished date.
                processed_unpublished_date = resource_publish_log.date_processed

            # Get portal.
            portal = ''
            if resource_publish_log.destination == constants.PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA:
                portal = 'Opendata'
            elif resource_publish_log.destination == constants.PUBLISH_EXTERNAL_IDENTIFIER_QSPATIAL_SCHEMA:
                portal = 'QSpatial'
            elif resource_publish_log.destination == constants.PUBLISH_EXTERNAL_IDENTIFIER_SIR_SCHEMA:
                portal = 'SIR'

            # Process the published date.
            if processed_date:
                offset = render_datetime(processed_date, date_format='%z')
                published_date = render_datetime(processed_date, date_format=date_format) + offset[:3] + ':' + offset[-2:]

            # Process the unpublished date.
            if processed_unpublished_date:
                offset = render_datetime(processed_unpublished_date, date_format='%z')
                unpublished_date = render_datetime(processed_unpublished_date, date_format=date_format) + offset[:3] + ':' + offset[-2:]

            data = {
                'resource': resource,
                'publish_log': resource_publish_log,
                'portal': portal,
                'distribution': get_distribution_naming(pkg, resource),
                'status': status,
                'published_date': published_date,
                'unpublished_date': unpublished_date,
                'details': details
            }
            resource_publish_logs.append(data)

    return resource_publish_logs


def get_published_distributions(pkg):
    return PublishLog.get_published_distributions(pkg)


def is_unpublish_pending(publish_log_id):
    publish_log = PublishLog.get(publish_log_id)

    if publish_log:
        return publish_log.status == constants.PUBLISH_STATUS_PENDING

    return True


def get_state_list(field=None):
    return [
        {
            'value': u'draft',
            'label': u'draft'
        },
        {
            'value': model.core.State.ACTIVE,
            'label': model.core.State.ACTIVE
        },
        {
            'value': model.core.State.DELETED,
            'label': model.core.State.DELETED
        },
        {
            'value': model.core.State.PENDING,
            'label': model.core.State.PENDING
        }
    ]


def get_pkg_title(name_or_id, pkg_dict=[]):
    try:
        if not pkg_dict:
            pkg_dict = get_action('package_show')({'ignore_auth': True}, {'name_or_id': name_or_id})

        pkg_name = h.dataset_display_name(pkg_dict)

        if pkg_dict.get('state') == model.core.State.DELETED:
            return pkg_name + ' [DELETED]'

        return pkg_name
    except Exception as e:
        return ''


def get_external_distribution_url(schema, external_dataset_id, external_distribution_id):
    if schema == constants.PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA:
        domain = os.getenv(constants.get_external_schema_url(schema))
        if domain and external_dataset_id and external_distribution_id:
            return domain + '/dataset/' + external_dataset_id + '/resource/' + external_distribution_id

    return ''

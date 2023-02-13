import ckan.plugins.toolkit as toolkit
import ckanext.qdes_schema.constants as constants
import ckanext.qdes_schema.helpers as helpers
import ckanext.scheming.helpers as scheming_helpers
import ckanext.vocabulary_services.logic.action.get as vocab_get_action
import json
import logging
import os
import traceback

from ckanapi import RemoteCKAN
from ckanext.qdes_schema.logic.helpers import resource_helpers
from ckanext.qdes_schema.model import PublishLog
from datetime import datetime
from pprint import pformat

get_action = toolkit.get_action
config = toolkit.config
log = logging.getLogger(__name__)


def publish_to_external_catalogue(publish_log_id, user):
    u"""
    Background job for publishing schema to external.
    """
    # Load the publish_log.
    publish_log = PublishLog.get(publish_log_id)

    if not publish_log:
        return

    package_dict = {}
    external_pkg_dict = {}
    try:
        site_user = get_action(u'get_site_user')({u'ignore_auth': True}, {})
        context = {u'user': site_user[u'name']}
        package_dict = get_action('package_show')(context, {'id': publish_log.dataset_id})

        # Get the api ket.
        api_key = os.getenv(constants.get_key_name(publish_log.destination))
        destination = _get_external_destination_ckan(publish_log.destination, api_key)

        # Get the dataset by name on external schema.
        detail, external_pkg_dict = _get_external_dataset(package_dict.get('name'), destination)

        if external_pkg_dict:
            if external_pkg_dict.get('state') == 'deleted':
                status = constants.PUBLISH_STATUS_FAILED
                detail = {
                    'external_distribution_deleted': True,
                    'error': 'The distribution cannot be published as it already exists in Data.QLD in a deleted state. The deleted dataset needs to be purged before it can be republished. Please contact the catalogue administrator.'}
            else:
                publish_log.action = constants.PUBLISH_ACTION_UPDATE
                publish_log.destination_identifier = external_pkg_dict.get('id')

                # Load recent publish log for this dataset.
                recent_publish_log = PublishLog.get_recent_resource_log(publish_log.resource_id,
                                                                        constants.PUBLISH_STATUS_SUCCESS)

                # Update external dataset.
                status, detail, external_pkg_dict = _update_external_dataset(
                    publish_log,
                    destination,
                    external_pkg_dict,
                    package_dict,
                    recent_publish_log
                )
        else:
            publish_log.action = constants.PUBLISH_ACTION_CREATE

            # Create external dataset.
            status, detail, external_pkg_dict = _create_external_dataset(publish_log, destination, package_dict)

        # Update dataset identifier.
        if external_pkg_dict and not external_pkg_dict.get('state') == 'deleted':
            identifiers = json.loads(package_dict['identifiers']) if package_dict.get('identifiers') else []
            identifiers.append(destination.address + '/dataset/' + external_pkg_dict.get('id'))
            identifiers = list(set(identifiers))
            package_dict['identifiers'] = json.dumps(identifiers)

            # Update resource dataservice.
            dataservice_id = config.get(constants.get_dataservice_id(publish_log.destination), None)
            if dataservice_id:
                resource = _get_selected_resource_to_publish(package_dict, publish_log)
                resource_helpers.add_dataservice(context, dataservice_id, resource[0], package_dict)
            else:
                # Update dataset identifiers.
                get_action('package_update')(context, package_dict)

    except Exception as e:
        log.error(''.join(traceback.format_tb(e.__traceback__)))
        log.error(str(e))
        status = constants.PUBLISH_STATUS_FAILED
        detail = {'type': 'system_error', 'error': str(e)}

    # Update publish_log processed time.
    publish_log.date_processed = datetime.utcnow()

    # Update activity stream.
    _update_activity_schema(publish_log, package_dict, status, user)

    # Update publish log.
    _update_publish_log(publish_log, status, detail, external_pkg_dict)


def unpublish_external_distribution(publish_log_id, user):
    # Load the publish_log.
    publish_log = PublishLog.get(publish_log_id)

    if not publish_log:
        return

    package_dict = {}
    external_pkg_dict = {}

    try:
        site_user = get_action(u'get_site_user')({u'ignore_auth': True}, {})
        context = {u'user': site_user[u'name']}
        package_dict = get_action('package_show')(context, {'id': publish_log.dataset_id})

        # Get the api ket.
        api_key = os.getenv(constants.get_key_name(publish_log.destination))
        destination = _get_external_destination_ckan(publish_log.destination, api_key)

        # Get the dataset by name on external schema.
        detail, external_pkg_dict = _get_external_dataset(package_dict.get('name'), destination)
        status = constants.PUBLISH_STATUS_FAILED
        if external_pkg_dict:
            resources = external_pkg_dict.get('resources', [])
            if len(resources) == 1:
                # Remove the dataset too.
                external_dataset_id = external_pkg_dict.get('id')
                detail, external_pkg_dict = _delete_external_dataset(external_dataset_id, destination)

                if not detail:
                    status = constants.PUBLISH_STATUS_SUCCESS
                    # Remove dataset identifier.
                    identifiers = json.loads(package_dict['identifiers']) if package_dict.get('identifiers') else []
                    identifiers.remove(destination.address + '/dataset/' + external_dataset_id)
                    identifiers = list(set(identifiers))
                    package_dict['identifiers'] = json.dumps(identifiers)
                    
            elif resources:
                # Remove the resource.
                new_resources = []
                external_pkg_dict.pop('resources')

                # Load recent publish log for this distribution.
                recent_publish_log = PublishLog.get_recent_resource_log(publish_log.resource_id,
                                                                        constants.PUBLISH_STATUS_SUCCESS)

                external_resource_id = ''
                if recent_publish_log:
                    recent_publish_log_detail = json.loads(recent_publish_log.details)
                    external_resource_id = recent_publish_log_detail.get('external_resource_id')

                for resource in resources:
                    if not resource.get('id') == external_resource_id:
                        new_resources.append(resource)

                external_pkg_dict['resources'] = new_resources

                # Update external dataset.
                status, detail, external_pkg_dict = _update_external_dataset(
                    publish_log,
                    destination,
                    external_pkg_dict,
                    external_pkg_dict,
                    recent_publish_log,
                    True
                )

            # Update resource dataservice.
            dataservice_id = config.get(constants.get_dataservice_id(publish_log.destination), None)
            if dataservice_id:
                resource = _get_selected_resource_to_publish(package_dict, publish_log)
                resource_helpers.add_dataservice(context, dataservice_id, resource[0], package_dict, True)
            else:
                # Remove dataset identifier.
                get_action('package_update')(context, package_dict)

    except Exception as e:
        log.error(''.join(traceback.format_tb(e.__traceback__)))
        log.error(str(e))
        status = constants.PUBLISH_STATUS_FAILED
        detail = {'type': 'system_error', 'error': str(e)}

    # Update publish_log processed time.
    publish_log.date_processed = datetime.utcnow()

    # Update activity stream.
    _update_activity_schema(publish_log, package_dict, status, user, True)

    # Update publish log.
    _update_publish_log(publish_log, status, detail, external_pkg_dict)


def _get_external_destination_ckan(schema, api_key):
    url = os.getenv(constants.get_external_schema_url(schema))
    return RemoteCKAN(url, apikey=api_key)


def _get_external_dataset(dataset_name, destination):
    detail = {}
    try:
        package_dict = destination.action.package_show(name_or_id=dataset_name)
    except Exception as e:
        detail = {'error': str(e)}
        package_dict = {}

    return detail, package_dict


def _delete_external_dataset(dataset_name, destination):
    detail = {}
    try:
        deletion_reason = 'Dataset unpublished from {0}'.format(config.get('ckan.site_url'))
        package_dict = destination.action.package_delete(id=dataset_name, deletion_reason=deletion_reason)
    except Exception as e:
        detail = str(e)
        package_dict = {}

    return detail, package_dict


def _get_selected_resource_to_publish(package_dict, publish_log):
    # Build new dataset and its resource.
    distribution = []
    for resource in package_dict.get('resources', []):
        if publish_log.resource_id == resource.get('id'):
            distribution.append(resource)

    return distribution


def _create_external_dataset(publish_log, destination, package_dict):
    pkg_dict = package_dict.copy()
    pkg_dict['resources'] = _get_selected_resource_to_publish(package_dict, publish_log)
    # Clean up the package_dict as per destination schema requirement.
    if publish_log.destination == 'qld_dataset':
        pkg_dict = _build_and_clean_up_dataqld(pkg_dict)
    elif publish_log.destination == 'qld_cdp_dataset':
        pkg_dict = _build_and_clean_up_qld_cdp(pkg_dict)

    # Send to external schema.
    external_package_dict = {}
    success = False
    try:
        external_package_dict = destination.action.package_create(**pkg_dict)
        success = True
        details = {
            'external_package_dict': external_package_dict,
            'external_resource_id': external_package_dict.get('resources')[0].get('id')
        }
    except Exception as e:
        if 'error_dict' in dir(e):
            details = e.error_dict
        else:
            log.error(pformat(dir(e)))
            details = {'error': str(e)}

    return constants.PUBLISH_STATUS_SUCCESS if success else constants.PUBLISH_STATUS_FAILED, details, external_package_dict


def _update_external_dataset(publish_log, destination, external_pkg_dict, package_dict, recent_publish_log, delete_distribution=False):
    pkg_dict = package_dict.copy()
    if not delete_distribution:
        pkg_dict['resources'] = _get_selected_resource_to_publish(pkg_dict, publish_log)
        # Modify the external_pkg_dict.
        if publish_log.destination == 'qld_dataset':
            pkg_dict = _build_and_clean_up_dataqld(pkg_dict, external_pkg_dict, recent_publish_log)
        elif publish_log.destination == 'qld_cdp_dataset':
            pkg_dict = _build_and_clean_up_qld_cdp(pkg_dict, external_pkg_dict, recent_publish_log)

    # Send the modified dict to external schema.
    external_package_dict = {}
    success = False
    try:
        external_package_dict = destination.action.package_update(**pkg_dict)

        # Load external resource id. Since this is update,
        # the possibility external_package_dict has multiple resources are big.
        # Let's pull the same resource id as tracked on previous publish log.
        updated_external_resource_id = ''
        if not delete_distribution:
            if recent_publish_log:
                recent_publish_log_detail = json.loads(recent_publish_log.details)
                updated_external_resource_id = recent_publish_log_detail.get('external_resource_id')

            if not updated_external_resource_id or not _check_resource_id_exist(updated_external_resource_id, external_package_dict.get('resources', [])):
                # Return the last list, and record the external resource id.
                last_resource = external_package_dict.get('resources', [])[-1]
                updated_external_resource_id = last_resource.get('id')

        success = True
        details = {
            'external_package_dict': external_package_dict,
            'external_resource_id': updated_external_resource_id
        }
    except Exception as e:
        if 'error_dict' in dir(e):
            details = e.error_dict
        else:
            details = {'error': str(e)}

    return constants.PUBLISH_STATUS_SUCCESS if success else constants.PUBLISH_STATUS_FAILED, details, external_package_dict


def _build_and_clean_up_dataqld(des_package_dict, external_package_dict=None, recent_publish_log=None):
    # Variable is_update will be true when
    # there is a similar package name on external schema.
    is_update = True if external_package_dict else False

    # Variable has_recent_log will be True in case the dataset already published to external.
    # Case like, user add new resource but the other resource/dataset already published,
    # below variable will be False.
    has_recent_log = True if recent_publish_log else False

    updated_external_resource_id = None
    if is_update and has_recent_log:
        recent_publish_log_detail = json.loads(recent_publish_log.details)
        updated_external_resource_id = recent_publish_log_detail.get('external_resource_id', None) or None

        if not updated_external_resource_id:
            has_recent_log = False

        # Check if the updated_external_resource_id is exist in external_package_dict.
        external_resources = external_package_dict.get('resources', [])
        has_recent_log = _check_resource_id_exist(updated_external_resource_id, external_resources)

    # Load the schema.
    schema = scheming_helpers.scheming_get_dataset_schema(constants.PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA)

    # Get the mandatory fields.
    dataset_fields = [field.get('field_name') for field in schema.get('dataset_fields') if field.get('required', False)]
    resource_fields = [field.get('field_name') for field in schema.get('resource_fields') if
                       field.get('required', False)]

    # Set default value, use external package data on update.
    qld_pkg_dict = external_package_dict if is_update else {}
    qld_resources_dict = qld_pkg_dict.get('resources', []) if qld_pkg_dict else []
    qld_resource_dict = {}
    if is_update and has_recent_log:
        for resource in qld_resources_dict:
            # Need to set all resources nature_of_change because they all get sent in package_update
            resource['nature_of_change'] = 'edit-resource-with-no-new-data'
            if resource.get('id') == updated_external_resource_id:
                qld_resource_dict = resource

    # Build the package metadata.
    for field in dataset_fields:
        qld_pkg_dict[field] = des_package_dict.get(field)

    # Build resource.
    des_resource = des_package_dict.get('resources')
    for field in resource_fields:
        # It is always index 0, because each job will create/update single distribution.
        qld_resource_dict[field] = des_resource[0].get(field)
        if field == 'format':
            # Manually map resource format
            qld_resource_dict[field] = helpers.map_formats(des_resource[0].get(field),
                                                           constants.PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA)

    if is_update:
        new_resources = []
        if has_recent_log:
            # Example case, user update resource that already published.
            for resource in qld_resources_dict:
                if resource.get('id') == updated_external_resource_id:
                    new_resources.append(qld_resource_dict)
                else:
                    new_resources.append(resource)
        else:
            # Example case, when user add new resource
            # and the dataset already published,
            # that case we need to carry the other resource
            # that coming from external_package_dict.
            new_resources = qld_resources_dict
            new_resources.append(qld_resource_dict)

        qld_pkg_dict['resources'] = new_resources
    else:
        # Add the resource to package.
        qld_pkg_dict['resources'] = [qld_resource_dict]

    # Set resource package_id for resources
    for resource in qld_pkg_dict.get('resources'):
        if not resource.get('package_id'):
            resource['package_id'] = qld_pkg_dict.get('id')

    # Manual Mapping for dataset field.
    update_freq = helpers.map_update_schedule(des_package_dict['update_schedule'],
                                              constants.PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA)
    qld_pkg_dict['update_frequency'] = update_freq if update_freq else 'not-updated'

    qld_pkg_dict['license_id'] = helpers.map_license(des_package_dict['license_id'],
                                                     constants.PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA)

    qld_pkg_dict['owner_org'] = os.getenv(
        constants.get_owner_org(constants.PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA))
    qld_pkg_dict['author_email'] = 'opendata@des.qld.gov.au'
    qld_pkg_dict['security_classification'] = 'PUBLIC'
    qld_pkg_dict['data_driven_application'] = 'NO'
    qld_pkg_dict['version'] = '1'
    qld_pkg_dict['de_identified_data'] = 'NO'
    qld_pkg_dict['next_update_due'] = None

    return qld_pkg_dict


def _build_and_clean_up_qld_cdp(des_package_dict, external_package_dict=None, recent_publish_log=None):
    # Variable is_update will be true when
    # there is a similar package name on external schema.
    site_user = get_action(u'get_site_user')({u'ignore_auth': True}, {})
    is_update = True if external_package_dict else False

    # Variable has_recent_log will be True in case the dataset already published to external.
    # Case like, user add new resource but the other resource/dataset already published,
    # below variable will be False.
    has_recent_log = True if recent_publish_log else False

    updated_external_resource_id = None
    if is_update and has_recent_log:
        recent_publish_log_detail = json.loads(recent_publish_log.details)
        updated_external_resource_id = recent_publish_log_detail.get('external_resource_id', None) or None

        if not updated_external_resource_id:
            has_recent_log = False

        # Check if the updated_external_resource_id is exist in external_package_dict.
        external_resources = external_package_dict.get('resources', [])
        has_recent_log = _check_resource_id_exist(updated_external_resource_id, external_resources)

    # Load the schema.
    schema = scheming_helpers.scheming_get_dataset_schema(constants.PUBLISH_EXTERNAL_IDENTIFIER_QLD_CDP_SCHEMA)

    # Get the mandatory fields.
    dataset_fields = [field.get('field_name') for field in schema.get('dataset_fields') if field.get('required', False)]
    resource_fields = [field.get('field_name') for field in schema.get('resource_fields') if field.get('required', False)]

    # Set default value, use external package data on update.
    qld_cdp_pkg_dict = external_package_dict if is_update else {}
    qld_cdp_resources_dict = qld_cdp_pkg_dict.get('resources', []) if qld_cdp_pkg_dict else []
    qld_cdp_resource_dict = {}
    if is_update and has_recent_log:
        for resource in qld_cdp_resources_dict:
            if resource.get('id') == updated_external_resource_id:
                qld_cdp_resource_dict = resource

    # Build the package metadata.
    for field in dataset_fields:
        qld_cdp_pkg_dict[field] = des_package_dict.get(field)

    # Build resource.
    # It is always index 0, because each job will create/update single distribution.
    des_resource = des_package_dict.get('resources')[0]
    for field in resource_fields:
        qld_cdp_resource_dict[field] = des_resource.get(field)

    # Manual Mapping for resource fields.
    service_api_endpoint = toolkit.get_converter('json_or_string')(des_resource.get('service_api_endpoint'))
    url = service_api_endpoint[0] if isinstance(service_api_endpoint, list) else des_resource.get('url')
    qld_cdp_resource_dict['url'] = url
    qld_cdp_resource_dict['description'] = des_resource.get('description')
    qld_cdp_resource_dict['format'] = helpers.map_formats(des_resource.get('format'),
                                                          constants.PUBLISH_EXTERNAL_IDENTIFIER_QLD_CDP_SCHEMA)
    qld_cdp_resource_dict['size'] = des_resource.get('size')
    qld_cdp_resource_dict['date_published'] = des_package_dict.get('dataset_release_date')
    qld_cdp_resource_dict['date_modified'] = des_package_dict.get('dataset_last_modified_date')
    qld_cdp_resource_dict['license'] = helpers.map_license(des_resource.get('license'),
                                                           constants.PUBLISH_EXTERNAL_IDENTIFIER_QLD_CDP_SCHEMA)
    
    if is_update:
        new_resources = []
        if has_recent_log:
            # Example case, user update resource that already published.
            for resource in qld_cdp_resources_dict:
                if resource.get('id') == updated_external_resource_id:
                    new_resources.append(qld_cdp_resource_dict)
                else:
                    new_resources.append(resource)
        else:
            # Example case, when user add new resource
            # and the dataset already published,
            # that case we need to carry the other resource
            # that coming from external_package_dict.
            new_resources = qld_cdp_resources_dict
            new_resources.append(qld_cdp_resource_dict)

        qld_cdp_pkg_dict['resources'] = new_resources
    else:
        # Add the resource to package.
        qld_cdp_pkg_dict['resources'] = [qld_cdp_resource_dict]

    # Set resource package_id for resources
    for resource in qld_cdp_pkg_dict.get('resources'):
        if not resource.get('package_id'):
            resource['package_id'] = qld_cdp_pkg_dict.get('id')

    # Manual Mapping for dataset field.
    update_freq = helpers.map_update_schedule(des_package_dict['update_schedule'],
                                              constants.PUBLISH_EXTERNAL_IDENTIFIER_QLD_CDP_SCHEMA)
    if update_freq:
        qld_cdp_pkg_dict['update_frequency'] = update_freq
    else:
        qld_cdp_pkg_dict.pop('update_frequency', None)

    qld_cdp_pkg_dict['license_id'] = helpers.map_license(des_package_dict['license_id'],
                                                         constants.PUBLISH_EXTERNAL_IDENTIFIER_QLD_CDP_SCHEMA)
    qld_cdp_pkg_dict['owner_org'] = os.getenv(constants.get_owner_org(constants.PUBLISH_EXTERNAL_IDENTIFIER_QLD_CDP_SCHEMA))
    qld_cdp_pkg_dict['data_custodian'] = "department-of-environment-and-science"
    qld_cdp_pkg_dict['publisher'] = "Department of Environment and Science"
    contact_point = get_action('get_secure_vocabulary_record')({'user': site_user}, {'vocabulary_name': 'point-of-contact', 'query': des_package_dict.get('contact_point')})
    qld_cdp_pkg_dict.pop('contact_point', None)
    qld_cdp_pkg_dict['point_of_contact'] = contact_point.get("Name", None)
    qld_cdp_pkg_dict['point_of_contact_email'] = contact_point.get("Email", None)
    qld_cdp_pkg_dict['tags'] = des_package_dict.get('tags', [])
    qld_cdp_pkg_dict['temporal_coverage_from'] = des_package_dict.get('temporal_start', None)
    qld_cdp_pkg_dict['temporal_coverage_to'] = des_package_dict.get('temporal_end', None)
    qld_cdp_pkg_dict['security_classification'] = 'official-public'
    qld_cdp_pkg_dict['access_rights'] = des_package_dict.get('rights_statement', None)
    qld_cdp_pkg_dict['data_attributes'] = helpers.map_data_attributes(json.loads(des_package_dict.get('parameter', None)))
    qld_cdp_pkg_dict['purpose'] = des_package_dict.get('purpose', None)
    qld_cdp_pkg_dict['provenance'] = des_package_dict.get('lineage_description', None)
    qld_cdp_pkg_dict['data_quality'] = helpers.map_data_quality(json.loads(des_package_dict.get('quality_description', None)))
    qld_cdp_pkg_dict['themes'] = helpers.map_themes(json.loads(des_package_dict.get('topic', None)))

    return qld_cdp_pkg_dict


def _get_vocab_label(dataset_type, field_type, field_name, uri):
    schema = scheming_helpers.scheming_get_dataset_schema(dataset_type)
    schema_field = scheming_helpers.scheming_field_by_name(schema[field_type], field_name) if schema else []

    if schema_field:
        schema_field_choices = []

        for term in vocab_get_action.vocabulary_service_terms({}, schema_field.get('vocabulary_service_name')):
            schema_field_choices.append({'value': term.uri, 'label': term.label, 'title': term.definition})

        return scheming_helpers.scheming_choices_label(schema_field_choices, uri)

    return ''


def _update_activity_schema(publish_log, package_dict, status, user, unpublish=False):
    resource_name = ''
    resource_format = ''
    for resource in package_dict.get('resources', []):
        if resource.get('id') == publish_log.resource_id:
            resource_name = resource.get('name')
            resource_format = _get_vocab_label('dataset', 'resource_fields', 'format', resource.get('format'))

    site_user = get_action(u'get_site_user')({u'ignore_auth': True}, {})
    context = {u'user': site_user[u'name']}
    toolkit.get_action('activity_create')(context, {
        'user_id': user,
        'object_id': publish_log.dataset_id,
        'activity_type': 'publish external schema' if not unpublish else 'unpublish external schema',
        'data': {
            'package': package_dict,
            'status': 'successfully' if status == constants.PUBLISH_STATUS_SUCCESS else 'unsuccessfully',
            'distribution': resource_format + ' - ' + resource_name
        }
    })


def _update_publish_log(publish_log, status, detail, external_pkg_dict):
    publish_log.status = status
    publish_log.details = json.dumps(detail)

    if external_pkg_dict:
        publish_log.destination_identifier = external_pkg_dict.get('id')

    return get_action('update_publish_log')({}, dict(publish_log.as_dict()))


def _check_resource_id_exist(res_id, resources):
    for res in resources:
        if res.get('id') == res_id:
            return True

    return False

import ckan.logic as logic
import ckan.plugins.toolkit as toolkit
import ckanext.qdes_schema.constants as constants
import ckanext.scheming.helpers as scheming_helpers
import ckanext.vocabulary_services.helpers as vocabulary_service_helpers
import ckanext.vocabulary_services.logic.action.get as vocab_get_action
import json
import logging
import os
import sys

from ckan import model
from ckan.common import c
from ckan.plugins.toolkit import h
from ckanapi import RemoteCKAN, ValidationError
from ckanext.qdes_schema.model import PublishLog
from datetime import datetime
from pprint import pformat

Session = model.Session
get_action = logic.get_action
log = logging.getLogger(__name__)


def publish_to_external_catalogue(publish_log_id):
    u"""
    Background job for publishing schema to external.
    """
    # Load the publish_log.
    publish_log = PublishLog.get(publish_log_id)

    if not publish_log:
        return

    # Update publish_log processed time.
    publish_log.date_processed = datetime.utcnow()

    package_dict = get_action('package_show')({}, {'id': publish_log.dataset_id})

    # Get the api ket.
    api_key = os.getenv(constants.get_key_name(publish_log.destination))
    destination = _get_external_destination_ckan(publish_log.destination, api_key)

    # Get the dataset by name on external schema.
    external_pkg_dict = _get_external_dataset(package_dict.get('name'), destination)
    if external_pkg_dict:
        publish_log.action = 'update'
        publish_log.destination_identifier = external_pkg_dict.get('id')

        # Update external dataset.
        status, detail = _update_external_dataset(publish_log, external_pkg_dict, package_dict)
    else:
        publish_log.action = 'create'

        # Update external dataset.
        status, detail, external_pkg_dict = _create_external_dataset(publish_log, destination, package_dict)

    # Update publish log.
    _update_publish_log(publish_log, status, detail, external_pkg_dict)


def _get_external_destination_ckan(schema, api_key):
    url = os.getenv(constants.get_external_schema_url(schema))
    return RemoteCKAN(url, apikey=api_key)


def _get_external_dataset(dataset_name, destination):
    package_dict = []
    try:
        package_dict = destination.action.package_show(name_or_id=dataset_name)
    except Exception as e:
        log.error(str(e))

    return package_dict


def _create_external_dataset(publish_log, destination, package_dict):
    # Build new dataset and its resource.
    distribution = []
    for resource in package_dict.get('resources', []):
        if publish_log.resource_id == resource.get('id'):
            distribution.append(resource)

    package_dict['resources'] = distribution

    # Clean up the package_dict as per destination schema requirement.
    package_dict = _clean_up_dataqld(package_dict)

    # Send to external schema.
    external_package_dict = {}
    success = False
    try:
        external_package_dict = destination.action.package_create(**package_dict)
        success = True
        details = external_package_dict
    except Exception as e:
        if e.error_dict:
            log.error(pformat(e.error_dict))
            details = e.error_dict
        else:
            log.error(pformat(dir(e)))
            details = {'error': str(e)}

    return constants.PUBLISH_STATUS_SUCCESS if success else constants.PUBLISH_STATUS_FAILED, details, external_package_dict


def _update_external_dataset(publish_log, external_pkg_dict, package_dict):
    # Modify the external_pkg_dict.

    # Send the modified dict to external schema.

    return True, {}


def _update_publish_log(publish_log, status, detail, external_pkg_dict):
    publish_log.status = status
    publish_log.details = json.dumps(detail)
    publish_log.destination_identifier = external_pkg_dict.get('id')

    return get_action('update_publish_log')({}, dict(publish_log.as_dict()))


def _clean_up_dataqld(package_dict):
    # Load the schema.
    schema = scheming_helpers.scheming_get_dataset_schema(constants.PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA)

    # Get the mandatory fields.
    dataset_fields = [field.get('field_name') for field in schema.get('dataset_fields') if field.get('required', False)]
    resource_fields = [field.get('field_name') for field in schema.get('resource_fields') if
                       field.get('required', False)]

    # Build the package to be published to external schema.
    pkg_dict = {}
    resource_dict = {}
    resource = package_dict.get('resources')
    for field in dataset_fields:
        pkg_dict[field] = package_dict.get(field)
    for field in resource_fields:
        resource_dict[field] = resource[0].get(field)

        if field == 'format':
            resource_dict[field] = _get_vocab_label('dataset', 'resource_fields', field, resource_dict[field])

    pkg_dict['resources'] = [resource_dict]

    # Manual Mapping for dataset field.
    # @todo, vocab value is not accepted, need a new uri for vocab.
    # dataset_fields['update_frequency'] = dataset_fields['update_schedule']
    pkg_dict['update_frequency'] = 'near-realtime'

    # @todo, fix this hardcoded value here.
    pkg_dict['owner_org'] = '5e759cce-aa72-4908-987f-df61f7f8e44a'
    pkg_dict['author_email'] = 'awang@salsadigital.com.au'
    pkg_dict['security_classification'] = 'PUBLIC'
    pkg_dict['data_driven_application'] = 'NO'
    pkg_dict['version'] = '1'

    return pkg_dict


def _get_vocab_label(dataset_type, field_type, field_name, uri):
    schema = scheming_helpers.scheming_get_dataset_schema(dataset_type)
    schema_field = scheming_helpers.scheming_field_by_name(schema[field_type], field_name) if schema else []

    if schema_field:
        schema_field_choices = []

        for term in vocab_get_action.vocabulary_service_terms({}, schema_field.get('vocabulary_service_name')):
            schema_field_choices.append({'value': term.uri, 'label': term.label, 'title': term.definition})

        return scheming_helpers.scheming_choices_label(schema_field_choices, uri)

    return ''

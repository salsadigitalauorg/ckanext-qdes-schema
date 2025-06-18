import csv
import os
import json
import subprocess
import re

import ckan.lib.munge as munge
import ckanext.qdes_schema.constants as constants

from ckanext.qdes_schema.logic.helpers import harvest_helpers as helpers
from datetime import datetime, UTC, timedelta
from ckanapi import RemoteCKAN, NotFound
from pprint import pformat
from six import string_types

from ckan.config.middleware import make_app
from ckan.cli import CKANConfigLoader
from logging.config import fileConfig as loggingFileConfig
from ckan.plugins.toolkit import get_action

if os.environ.get(u'CKAN_INI'):
    config_path = os.environ[u'CKAN_INI']
else:
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), u'ckan.ini')

if not os.path.exists(config_path):
    raise RuntimeError(u'CKAN config option not found: {}'.format(config_path))

loggingFileConfig(config_path)
config = CKANConfigLoader(config_path).get_config()

application = make_app(config)


def generate_api_token():
    """
    Generate a new API token using CKAN CLI command.
    Returns the token string or None if failed.
    """
    try:
        # Run CKAN CLI command to create API token
        result = subprocess.run(
            ['ckan', 'user', 'token', 'add', 'des_sysadmin', 'import'],
            capture_output=True,
            text=True,
            cwd='/app'
        )

        if result.returncode == 0:
            # Parse the output to extract the token
            output = result.stdout
            # Look for the token pattern in the output
            token_match = re.search(r'API Token created:\s*([A-Za-z0-9._-]+)', output)
            if token_match:
                return token_match.group(1).strip()
            else:
                print("Could not find API token in CLI output")
                print("CLI output:", output)
                return None
        else:
            print(f"Error creating API token: {result.stderr}")
            return None
    except Exception as e:
        print(f"Exception while generating API token: {str(e)}")
        return None


# Generate new API token or use environment variable/fallback
site_url = 'http://localhost:8800'  # os.environ.get('LAGOON_ROUTE')
destination_api_key = os.environ.get('DESTINATION_API_KEY')

if not destination_api_key:
    print("No HARVEST_API_KEY environment variable found. Generating new API token...")
    destination_api_key = generate_api_token()
    if destination_api_key:
        print(f"Generated new API token: {destination_api_key}")
    else:
        print("Failed to generate API token. Using fallback token.")
else:
    print(f"Using DESTINATION_API_KEY from environment: {destination_api_key}")

source_api_key = os.environ.get('SOURCE_API_KEY')
dataservice_name = 'data-qld'
directory = os.path.dirname(os.path.abspath(__file__))

DEBUG = False
SOURCE_FILENAME = os.path.join(directory, 'Harvest List FINAL.csv')


def get_dataset_schema_fields():
    """
    Get all fields available on QDES dataset.
    """
    with open(os.path.join(os.path.dirname(directory), 'qdes_ckan_dataset.json')) as f:
        return json.load(f)


def dataset_mapping(dataset, source_dict):
    """
    Map QLD dataset to QDES dataset.
    """
    mapped_dataset = {}
    schema = get_dataset_schema_fields()

    try:

        # Manual field mapping.
        manual_fields = [
            'owner_org',
            'license_id',
            'url',
            'update_schedule',
            'classification_and_access_restrictions',
            'classification',
            'topic',
            'contact_point',
            'contact_publisher',
            'publication_status',
            'format',
            'tag_string',
            'identifiers',
            'lineage_description',
            'dataset_creation_date',
            'dataset_release_date',
            'metadata_review_date',
            'type',
            'dataset_last_modified_date'
        ]

        # Keeping track of license_id and license_url values
        license_id = dataset.get('license_id', None)
        if license_id not in unique_license_ids:
            unique_license_ids.append(license_id)
        license_url = dataset.get('license_url', None)
        if license_url not in unique_license_urls:
            unique_license_urls.append(license_url)

        # Mandatory field default values from CSV
        mapped_dataset['identifiers'] = json.dumps(
            [f"https://www.data.qld.gov.au/dataset/{dataset.get('id')}",
             f"https://www.data.qld.gov.au/dataset/{dataset.get('name')}"]
        )
        mapped_dataset['lineage_description'] = dataset.get('Description')
        mapped_dataset['dataset_creation_date'] = dataset.get('metadata_created').split('.')[0]
        mapped_dataset['dataset_release_date'] = dataset.get('metadata_created').split('.')[0]

        # Mandatory field default values hardcoded
        mapped_dataset['type'] = 'dataset'
        mapped_dataset['license_id'] = 'https://linked.data.gov.au/def/qld-data-licenses/cc-by-4.0'
        organisation_name = source_dict.get('Organisation')
        organisation = destination.action.organization_show(id=organisation_name)
        if organisation:
            mapped_dataset['owner_org'] = organisation.get('id')

        if not mapped_dataset['owner_org']:
            print(f'>>> No matching organisation found for: {organisation_name}')

        mapped_dataset['dataset_last_modified_date'] = dataset.get('metadata_modified').split('.')[0]
        mapped_dataset['metadata_review_date'] = (datetime.now(UTC) + timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%S')

        # TODO: Reinstate this and update mappings
        # mapped_dataset['update_schedule'] = helpers.get_mapped_update_frequency(dataset.get('update_frequency'))

        # Classification vocabulary service lookup
        classification = helpers.get_vocabulary_service_term(
            destination,
            source_dict.get('General classification of dataset type', 'Dataset').lower(),
            'classification')

        if classification:
            mapped_dataset['classification'] = json.dumps([classification])

        # Classification and access restrictions vocabulary service lookup
        class_and_access = helpers.get_vocabulary_service_term(
            destination,
            'OFFICIAL',
            'classification_and_access_restrictions')

        if class_and_access:
            mapped_dataset['classification_and_access_restrictions'] = json.dumps([class_and_access])

        # Topic/theme vocabulary service lookup
        source_topic = source_dict.get('Topic or theme', None) or None

        if source_topic:
            topic = helpers.get_vocabulary_service_term(
                destination,
                source_topic.lower().strip(),
                'topic')

            if topic:
                mapped_dataset['topic'] = json.dumps([topic])
            else:
                print('>>> No matching topic found for:')
                print('>>> source: {}'.format(pformat(source_dict)))
        else:
            print('>>> No source topic set for:')
            print('>>> source: {}'.format(pformat(source_dict)))

        # Point of Contact "secure" vocabulary look-up
        point_of_contact = helpers.get_secure_vocabulary_record(
            destination,
            source_dict.get('Point of Contact'),
            'point-of-contact',
            mapped_dataset['owner_org'])

        if point_of_contact:
            mapped_dataset['contact_point'] = point_of_contact
        else:
            print('>>> No matching point of contact found for: {}'.format(source_dict.get('Point of Contact')))

        # Publication status vocabulary service lookup
        publication_status = helpers.get_vocabulary_service_term(
            destination,
            'completed',
            'publication_status')

        if publication_status:
            mapped_dataset['publication_status'] = publication_status

        mapped_dataset['contact_publisher'] = helpers.get_vocabulary_service_term(
            destination,
            'Department of Environment and Science',
            'contact_publisher')

        # @TODO: Should this be set in here??? i.e. Dataset schema does not have a `format` field
        # mapped_dataset['format'] = 'https://www.iana.org/assignments/media-types/application/1d-interleaved-parityfec'

        # Build the rest of the values.
        for field in schema.get('dataset_fields'):
            field_name = field.get('field_name')

            # Do not process if the field already added via manual mapping or empty.
            if field_name not in manual_fields and dataset.get(field_name, None):
                mapped_dataset[field_name] = dataset.get(field_name, '')

        return mapped_dataset
    except Exception as e:
        print('>>> Exception raised in dataset_mapping')
        print(str(e))
        raise


def resource_mapping(res, source_dict):
    """
    Clean up resource.
    """
    try:
        # Keeping track of unique formats from Data.Qld to map to DES controlled vocab
        source_format = res.get('format', None)
        if source_format not in unique_formats:
            unique_formats.append(source_format)

        mapped_resource = {
            'data_services': json.dumps([data_service.get('id')]),
            'size': helpers.convert_size_to_bytes(res.get('size', 0)),
            'format': helpers.get_mapped_format(res.get('format', '')),
            # TODO: Should url be service_api_endpoint
        }
        if not mapped_resource['format']:
            print('>>> No matching format found for: {}'.format(res.get('format', '')))
            if res.get('format', '').lower() == 'zip':
                print(f'Setting format to ZIP for: {source_dict.get("Dataset URL")} - {res.get("name")}')
                if res.get('name') == 'Climatic regions for stormwater management design objectives - Queensland':
                    mapped_resource['format'] = 'http://publications.europa.eu/resource/authority/file-type/SHP'
                elif res.get('name') == 'Botanical Dictionary for Queensland 2022':
                    mapped_resource['format'] = 'http://publications.europa.eu/resource/authority/file-type/TXT'
                elif res.get('name') == 'Ground lidar scans and ancillary data directory':
                    mapped_resource['format'] = 'http://publications.europa.eu/resource/authority/file-type/SHP'

        if int(mapped_resource['size']) < 1:
            print(f'Setting size to 0 for: {source_dict.get("Dataset URL")} - {res.get("name")}')
            mapped_resource['size'] = 1

        # Manual field mapping.
        manual_fields = [
            'size',
            'format',
            'data_services'
        ]

        # Get all fields available on QDES dataset.
        schema = get_dataset_schema_fields()

        # Build the rest of the value.
        for field in schema.get('resource_fields'):
            field_name = field.get('field_name')

            # Do not process if the field already added via manual mapping or empty.
            if field_name not in manual_fields and res.get(field_name, None):
                mapped_resource[field_name] = res.get(field_name, '')

        # Encode url if exist.
        if mapped_resource['url']:
            mapped_resource['url'] = helpers.fix_url(mapped_resource['url'])

        if not mapped_resource['format']:
            print('>>> No matching format found for: {}'.format(res.get('format', '')))

        if DEBUG:
            print('Got mapped_resource: {}'.format(pformat(mapped_resource)))
        return mapped_resource
    except Exception as e:
        print('>>> Exception raised in resource_mapping')
        print(f'>>> Input: {res}')
        print(str(e))
        raise e


def resource_to_dataset_mapping(res, parent_dataset, source_dict):
    """
    Map resource to dataset for series.
    """
    mapped_dataset = {}
    schema = get_dataset_schema_fields()

    try:
        # Manual field mapping.
        mandatory_fields = [
            'classification',
            'classification_and_access_restrictions',
            'contact_point',
            'contact_publisher',
            'license_id',
            'publication_status',
            'topic',
            'owner_owg'
        ]
        # Loop the parent, get the data from resource first and if none, use the parent data.
        for field in schema.get('dataset_fields'):
            field_name = field.get('field_name')
            value = res.get(field_name)

            if field_name == 'name':
                value = munge.munge_title_to_name(value)

            if not value and field_name in mandatory_fields:
                value = parent_dataset.get(field_name)

            if value:
                mapped_dataset[field_name] = value

        # Set title.
        mapped_dataset['title'] = res.get('name')

        # Set organisation.
        mapped_dataset['owner_org'] = parent_dataset.get('owner_org')

        # Set the new dataset's notes (description) field to the resource description
        resource_description = res.get('description', None) or None
        mapped_dataset['notes'] = resource_description if resource_description else parent_dataset.get('notes', '')

        # Set isPartOf relationship.
        mapped_dataset['series_or_collection'] = json.dumps([{"id": parent_dataset.get('name'), "text": parent_dataset.get('title')}])

        # Create a resource for the dataset based on the resource we are working with
        # AND connect it to the data service
        mapped_dataset['resources'] = [resource_mapping(res, source_dict)]

        # Encode url if exist.
        if mapped_dataset['url']:
            mapped_dataset['url'] = helpers.fix_url(mapped_dataset['url'])

        return mapped_dataset

    except Exception as e:
        print('>>> Exception raised in resource_to_dataset_mapping')
        print(str(e))
        raise


def append_error(dataset_name, errors, source_url):
    error_log.append({
        'package_id': dataset_name,
        'errors': errors,
        'source_url': source_url,
    })


def append_migration_log(dataset, resource, action):
    migration_log.append(f'{dataset},"{resource}",{action}')


def create_publish_logs(new_package_dict, package_dict):
    """
    Create publish logs for all resources in a package.

    Args:
        new_package_dict: The newly created package dictionary
        package_dict: The original package dictionary from source

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a published log
        for resource in new_package_dict.get('resources', []):
            # Get the external resource
            external_resource = next((r for r in package_dict.get('resources', []) if r.get('id') ==
                                      resource.get('id') or r.get('name') == resource.get('name')), None)
            details = {
                'external_package_dict': package_dict,
                'external_resource_id': external_resource.get('id') if external_resource else None,
            }

            get_action('create_publish_log')({"ignore_auth": True, "user": "des_sysadmin"}, {
                'dataset_id': new_package_dict.get('id'),
                'resource_id': resource.get('id'),
                'destination_identifier': package_dict.get('id'),
                'trigger': constants.PUBLISH_TRIGGER_MANUAL,
                'destination': constants.PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA,
                'status': constants.PUBLISH_STATUS_SUCCESS,
                'action': constants.PUBLISH_ACTION_CREATE,
                'date_processed': datetime.now(UTC),
                'details': json.dumps(details)
            })

        success_log.append({
            'package_id': dataset_name,
            'message': 'Published log created.'
        })
        return True
    except Exception as e:
        print(f'Error creating publish logs for {dataset_name}: {str(e)}')
        return False


def add_dataservice(resource_match):
    update_package = False
    # Add data-qld dataservice to existing  data_services
    if isinstance(resource_match.get('data_services', []), string_types):
        existing_data_services = json.loads(resource_match.get('data_services', [])) or []
    else:
        existing_data_services = resource_match.get('data_services', []) or []

    if data_service.get('id') not in existing_data_services:
        existing_data_services.append(data_service.get('id'))
        resource_match['data_services'] = json.dumps(existing_data_services)
        update_package = True
        append_migration_log(dataset_name, resource_match.get('name', None),
                             'Resource is a duplicate of existing QSpatial resource. New resource not created. Existing resource updated.')
    return update_package


def add_new_resource_to_existing_package(dataset_name, existing_package, resource, row):
    # Create new resources
    new_resource = resource_mapping(resource, row)
    existing_package['resources'].append(new_resource)
    append_migration_log(dataset_name, new_resource.get('name', None), 'Resource added to existing QSpatial record.')

    return True


def check_for_existing_package(dataset_name, package_dict):
    existing_package = None
    try:
        update_existing_package = False
        existing_package = destination.action.package_show(id=dataset_name)
        # Package already exists so lets update it
        existing_identifiers = json.loads(existing_package.get('identifiers', [])) or []
        if row.get('Dataset URL') not in existing_identifiers:
            existing_identifiers.append(row.get('Dataset URL'))
            existing_package['identifiers'] = json.dumps(existing_identifiers)
            update_existing_package = True

        if 'series' in package_dict['title'].lower():

            # Create individual package for each resource that belong to above series dataset.
            if ('resources' in package_dict):
                for resource in package_dict.get('resources'):
                    resource_name = munge.munge_title_to_name(resource.get('name'))
                    try:
                        existing_series_package = destination.action.package_show(id=resource_name)
                        update_existing_series_package = False
                        # Find matching resources using resource name and URLs
                        resource_match = next(
                            (
                                series_resource for series_resource in existing_series_package.get('resources', [])
                                if series_resource.get('name', None) == resource.get('name', None)
                                # and helpers.fix_url(resource.get('url', '')) == json.loads(existing_resource.get('url', '[""]'))[0]
                            ), None)
                        if resource_match:
                            if 'qldspatial.information.qld.gov.au' in resource.get('url', None):
                                result = add_dataservice(resource_match)
                                if result and not update_existing_series_package:
                                    update_existing_series_package = True
                            elif resource_match.get('url', None) != resource.get('url', None):
                                result = add_new_resource_to_existing_package(dataset_name, existing_series_package, resource, row)
                                if result and not update_existing_series_package:
                                    update_existing_series_package = True
                        else:
                            # If resource has 'metadata' in the name and a qspatial rest API url, do not create it
                            metadata_url_check = ('qldspatial.information.qld.gov.au/catalogueadmin/'
                                                  'rest/document?id=' in resource.get('url', ''))
                            if 'metadata' in resource.get('name').lower() and metadata_url_check:
                                append_migration_log(dataset_name, resource.get('name', None),
                                                     'Resource is a metadata XML of existing QSpatial record. Resource not created.')
                            else:
                                result = add_new_resource_to_existing_package(dataset_name, existing_series_package, resource, row)
                                if result and not update_existing_series_package:
                                    update_existing_series_package = True

                        if update_existing_series_package:
                            destination.action.package_update(**existing_series_package)
                            success_log.append({
                                'package_id': dataset_name,
                                'message': 'Successfully updated.'
                            })
                        # Package already exists and key info has been updated so lets move on to the next
                        continue
                    except NotFound:
                        pass

                    # Package does not exists
                    #  If resource has 'metadata' in the name and a qspatial rest API url, do not create it
                    if 'metadata' in resource.get('name').lower() and 'qldspatial.information.qld.gov.au/catalogueadmin/rest/document?id=' in resource.get('url'):
                        append_migration_log(dataset_name, resource.get('name', None),
                                             'Resource is a metadata XML of existing QSpatial record. Resource not created.')
                    else:
                        # Create new package from series resource
                        new_series_package_dict = resource_to_dataset_mapping(resource, existing_package, row)
                        try:
                            new_series_package_dict = destination.action.package_create(**new_series_package_dict)
                            append_migration_log(dataset_name, resource.get('name', None), 'New dataset created for QSpatial series')
                            success_log.append({
                                'package_id': dataset_name,
                                'message': 'Successfully migrated.'
                            })
                        except Exception as e:
                            print(e)
                            append_error(new_series_package_dict.get('name'), str(e), source_url)
        else:
            # Update existing resources
            for resource in package_dict.get('resources', []):
                # Find matching resources using resource name and URLs
                resource_match = next(
                    (
                        existing_resource for existing_resource in existing_package.get('resources', [])
                        if existing_resource.get('name', None) == resource.get('name', None)
                        # and helpers.fix_url(resource.get('url', '')) == json.loads(existing_resource.get('url', '[""]'))[0]
                    ), None)

                if resource_match:
                    if 'qldspatial.information.qld.gov.au' in resource.get('url', None):
                        result = add_dataservice(resource_match)
                        if result and not update_existing_package:
                            update_existing_package = True
                    elif resource_match.get('url', None) != resource.get('url', None):
                        result = add_new_resource_to_existing_package(dataset_name, existing_package, resource, row)
                        if result and not update_existing_package:
                            update_existing_package = True
                else:
                    # If resource has 'metadata' in the name and a qspatial rest API url, do not create it
                    metadata_url_check2 = ('qldspatial.information.qld.gov.au/catalogueadmin/'
                                           'rest/document?id=' in resource.get('url', ''))
                    if 'metadata' in resource.get('name').lower() and metadata_url_check2:
                        append_migration_log(dataset_name, resource.get('name', None),
                                             'Resource is a metadata XML of existing QSpatial record. Resource not created.')
                    else:
                        result = add_new_resource_to_existing_package(dataset_name, existing_package, resource, row)
                        if result and not update_existing_package:
                            update_existing_package = True

        if update_existing_package:
            destination.action.package_update(**existing_package)
            success_log.append({
                'package_id': dataset_name,
                'message': 'Successfully updated.'
            })
    except NotFound:
        existing_package = None

    return existing_package and isinstance(existing_package, dict)


# Set the import source and destination.
source = RemoteCKAN('https://www.data.qld.gov.au', apikey=source_api_key)
destination = RemoteCKAN(site_url, apikey=destination_api_key)
data_service = destination.action.package_show(id=dataservice_name)
error_log = []
success_log = []
migration_log = []
append_migration_log('Dataset', 'Resource', 'Action')
unique_formats = []
unique_license_ids = []
unique_license_urls = []

# Open CSV file.
with open(SOURCE_FILENAME, "rt") as file:
    data = file.read().split('\n')

csv_reader = csv.DictReader(data)

count = 0
limit = 5

if not os.path.exists(os.path.join(directory, 'json_files')):
    os.makedirs(os.path.join(directory, 'json_files'))

for row in csv_reader:
    count += 1

    if DEBUG and count > limit:
        break

    # Get dataset name.
    source_url = row.get('Dataset URL', None)

    if not source_url:
        append_error('Row {}'.format(count), 'URL not set (URL is case sensitive)', None)
        continue

    dataset_name = source_url.split('/')[-1]
    print('Fetching dataset: {}'.format(dataset_name))
    # Fetch package from Data.Qld.
    package_dict = []
    existing_package_found = False
    try:
        json_file_path = os.path.join(directory, 'json_files', f'{dataset_name}.json')
        if os.path.exists(json_file_path):
            package_dict = json.load(open(json_file_path, 'r'))
        else:
            package_dict = source.action.package_show(id=dataset_name)
            with open(json_file_path, 'w') as json_file:
                json_file.write(json.dumps(package_dict, indent=2))

        existing_package_found = check_for_existing_package(dataset_name, package_dict)
    except Exception as e:
        print(f'Error fetching package {dataset_name}')
        append_error(dataset_name, str(e), source_url)
        continue

    # If existing package was found and updated move on to the next package
    if existing_package_found:
        continue

    # Map dataset.
    new_package_dict = dataset_mapping(package_dict, row)

    if DEBUG:
        print('Got package_dict: {}'.format(pformat(package_dict)))
        print('Mapped to package_dict: {}'.format(pformat(new_package_dict)))

    if 'series' in package_dict['title'].lower():
        # This will be resource-less package.
        new_package_dict['resources'] = []
        error = False

        # Create the parent of series dataset.
        try:
            new_package_dict = destination.action.package_create(**new_package_dict)
            append_migration_log(dataset_name, new_package_dict.get('name', None), 'New parent of series dataset created for DataQLD')
            success_log.append({
                'package_id': dataset_name,
                'message': 'Successfully migrated.'
            })
        except Exception as e:
            append_error(dataset_name, str(e), source_url)
            continue

        # Create individual package for each resource that belong to above series dataset.
        if ('resources' in package_dict) and not error:
            # Filter out resource names with meta in them
            for resource in [resource for resource in package_dict.get('resources') if 'meta' not in resource.get('name').lower()]:
                new_series_package_dict = resource_to_dataset_mapping(resource, new_package_dict, row)

                try:
                    new_series_package_dict_id = destination.action.package_create(**new_series_package_dict)
                    append_migration_log(dataset_name, new_series_package_dict.get('name', None),
                                         f'New child of series dataset created for DataQLD parent series {new_package_dict.get("name")}')
                    success_log.append({
                        'package_id': dataset_name,
                        'message': 'Successfully migrated.'
                    })
                except Exception as e:
                    append_error(new_series_package_dict.get('name'), str(e), source_url)
    else:
        # Map Resources.
        new_package_dict['resources'] = []

        try:
            if 'resources' in package_dict:
                # Filter out resource names with meta in them
                for resource in [resource for resource in package_dict.get('resources') if 'meta' not in resource.get('name').lower()]:
                    new_package_dict['resources'].append(resource_mapping(resource, row))

            new_package_dict = destination.action.package_create(**new_package_dict)
            append_migration_log(dataset_name, new_package_dict.get('name', None), 'New DataQLD dataset created')
            success_log.append({
                'package_id': dataset_name,
                'message': 'Successfully migrated.'
            })
            # Create a published log
            create_publish_logs(new_package_dict, package_dict)
        except Exception as e:
            append_error(dataset_name, str(e), source_url)

if success_log:
    # print(pformat(success_log))
    if not os.path.exists(os.path.join(directory, 'logs')):
        os.makedirs(os.path.join(directory, 'logs'))
    with open(os.path.join(directory, 'logs', f'success-{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv'), 'w') as log_csv:
        for log in success_log:
            log_csv.write(f'{log}\n')

if error_log:
    print(pformat(error_log))
    if not os.path.exists(os.path.join(directory, 'logs')):
        os.makedirs(os.path.join(directory, 'logs'))
    with open(os.path.join(directory, 'logs', f'errors-{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv'), 'w') as log_csv:
        for log in error_log:
            log_csv.write(f'{log}\n')

if migration_log:
    if not os.path.exists(os.path.join(directory, 'logs')):
        os.makedirs(os.path.join(directory, 'logs'))
    with open(os.path.join(directory, 'logs', f'migration-{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv'), 'w') as log_csv:
        for log in migration_log:
            log_csv.write(f'{log}\n')

print('>>> Unique license_id values from Data.Qld:')
print(pformat(unique_license_ids))

print('>>> Unique license_url values from Data.Qld:')
print(pformat(unique_license_urls))

print(f'\nRows in CSV: {count}')

print(f'\nRows migrated: {len(success_log)}')

print(f'\nRows failed: {len(error_log)}')

print('>>> Unique formats from Data.Qld:')
print(pformat(unique_formats))

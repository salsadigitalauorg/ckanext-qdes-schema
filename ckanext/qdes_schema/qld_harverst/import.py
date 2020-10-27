import csv
import os
import json
import re

from datetime import datetime
from ckanapi import RemoteCKAN
from pprint import pformat

owner_org = os.environ['OWNER_ORG']
apiKey = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJYeHVTSTRXTDdSS1FwM0hIYVJKS0Q3RmNIQjFnR2pSQVZGZlFSR21SdVJfRVhLR0lkNXpMTjRxZEJoTzkzUlppNHAtWWVHQ0JQeHlydHVDayIsImlhdCI6MTYwMzcwNDIwOX0.ee3V6xluDQzGDiagrjX-jZXMrOow6KAUeLjmD2Tw6LU'


def convert_size_to_bytes(size_str):
    """
    Convert human file-sizes to bytes.
    """
    multipliers = {
        'kib': 1024,
        'mib': 1024 ** 2,
        'gib': 1024 ** 3,
    }

    for suffix in multipliers:
        size_str = size_str.lower().strip().strip('s')
        if size_str.lower().endswith(suffix):
            return int(float(size_str[0:-len(suffix)]) * multipliers[suffix])
    else:
        if size_str.endswith('b'):
            size_str = size_str[0:-1]
        elif size_str.endswith('byte'):
            size_str = size_str[0:-4]
    return int(size_str)


def get_all_fields():
    """
    Get all fields available on QDES dataset.
    """
    with open('../qdes_ckan_dataset.json') as f:
        return json.load(f)


def dataset_mapping(dataset):
    """
    Map QLD dataset to QDES dataset.
    """
    mapped_dataset = {}
    scheme = get_all_fields()

    # Added default fields specific to the QDES dataset.
    mapped_dataset['package'] = 'dataset'
    mapped_dataset['owner_org'] = owner_org
    today = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    mapped_dataset['dataset_creation_date'] = today
    mapped_dataset['dataset_release_date'] = today
    mapped_dataset['dataset_last_modified_date'] = today

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
    ]

    # Map license, license_id on QLD only a fraction of the vocab data that controlled QDES field.
    # @todo: fix this.
    mapped_dataset['license_id'] = 'http://registry.it.csiro.au/licence/cc-by-4.0'

    # Map URL, if the URL is not available on source, give it default value.
    mapped_dataset['url'] = dataset.get('url') if len(dataset.get('url', '')) > 0 else 'http://data.qld.gov.au'

    # Map Update frequency, we can't use get_vocab_value because some of the values are custom (can't be matched 1:1).
    # The below frequency value to filter based on this value, use below
    # https://www.data.qld.gov.au/organization/a3cdcdcb-201c-4360-9fa6-98e361c89279?update_frequency=not-updated.
    # @todo: fix this.
    frequency_map = {
        'near-real-time': 'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/continual',
        'hourly': '',
        'daily': 'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/daily',
        'weekly': 'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/weekly',
        'fortnightly': 'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/fortnightly',
        'monthly': 'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/monthly',
        'quarterly': 'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/quarterly',
        'half-yearly': 'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/biannually',
        'annually': 'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/annually',
        'non-regular': 'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/irregular',
        'not-updated': 'http://registry.it.csiro.au/def/isotc211/MD_MaintenanceFrequencyCode/notPlanned',
    }
    mapped_dataset['update_schedule'] = frequency_map.get(dataset.get('update_frequency'), '')

    # Map keyword (tag_string).
    mapped_dataset['tag_string'] = []

    # Map csv fields to QDES.
    csv_field_col = {
        'classification_and_access_restrictions': 1,
        'classification': 2,
        'topic': 3,
        'contact_point': 4,
        'contact_publisher': 5,
        'publication_status': 6,
        'format': 7,
    }
    # Map classification_and_access_restrictions.
    # @todo: fix this after the data is confirmed in csv, maybe can introduce the new param to this function.
    mapped_dataset['classification_and_access_restrictions'] = json.dumps(['http://registry.it.csiro.au/def/isotc211/MD_ClassificationCode/confidential'])
    mapped_dataset['classification'] = json.dumps(['http://registry.it.csiro.au/def/datacite/resourceType/Audiovisual'])
    mapped_dataset['topic'] = json.dumps(['https://gcmdservices.gsfc.nasa.gov/kms/concept/feef8827-92a6-4d1d-b6a5-ecda38a32656'])

    mapped_dataset['contact_point'] = 'http://linked.data.gov.au/def/iso19115-1/RoleCode/author'
    mapped_dataset['contact_publisher'] = 'http://linked.data.gov.au/def/organisation-type/family-partnership'
    mapped_dataset['publication_status'] = 'http://registry.it.csiro.au/def/isotc211/MD_ProgressCode/accepted'
    mapped_dataset['format'] = 'https://www.iana.org/assignments/media-types/application/1d-interleaved-parityfec'

    # Build the rest of the value.
    for field in scheme.get('dataset_fields'):
        field_name = field.get('field_name')
        process = False

        # Do not process if the field already added via manual mapping or empty.
        if (not field.get('field_name') in manual_fields) and dataset.get(field_name, None):
            process = True

        if process:
            mapped_dataset[field_name] = dataset.get(field_name, '')

    return mapped_dataset


def resource_mapping(res):
    """
    Clean up resource.
    """
    mapped_resource = {}

    # Manual field mapping.
    manual_fields = [
        'size',
        'format',
    ]

    # Map size.
    mapped_resource['size'] = convert_size_to_bytes(res.get('size', 0))

    # Map format.
    # @todo: fix this. issue example: on source there is "JSON" as value, but the format has many JSON types.
    mapped_resource['format'] = 'https://www.iana.org/assignments/media-types/application/alto-directory+json'

    # Strip out unnecessary fields.
    remove_fields = [
        'archiver',
        'package_id'
    ]
    for f_name in remove_fields:
        if f_name in res:
            res.pop(f_name)

    # Get all fields available on QDES dataset.
    with open('../qdes_ckan_dataset.json') as f:
        scheme = json.load(f)

    # Build the rest of the value.
    for field in scheme.get('resource_fields'):
        field_name = field.get('field_name')

        # Do not process if field value is empty.
        if (res.get(field_name, None)) and (not field_name in manual_fields):
            mapped_resource[field_name] = res.get(field_name, '')

    return mapped_resource


def resource_to_dataset_mapping(res, parent_dataset, parent_dataset_id):
    """
    Map resource to dataset for series.
    """
    mapped_dataset = {}
    scheme = get_all_fields()

    # Loop the parent, get the data from resource first and if none, use the parent data.
    for field in scheme.get('dataset_fields'):
        field_name = field.get('field_name')
        value = res.get(field_name)

        if field_name == 'name':
            value = re.sub('[^0-9a-zA-Z]+', '-', value.lower())
            # No value longer than 100 chars, we will add the last 8 chars with current uuid,
            # otherwise it will have possibility conflict with other series.
            value = (value[:92] + res.get('id')[:8]) if len(value) > 100 else value

        if not value:
            value = parent_dataset.get(field_name)

        mapped_dataset[field_name] = value

    # Set title.
    mapped_dataset['title'] = res.get('name')

    # Set isPartOf relationship.
    mapped_dataset['series_or_collection'] = json.dumps([{"id": parent_dataset_id.get('id'), "text": parent_dataset_id.get('title')}])

    return mapped_dataset


# Set the import source and destination.
source = RemoteCKAN('https://www.data.qld.gov.au')
destination = RemoteCKAN(os.environ['LAGOON_ROUTE'], apikey=apiKey)

# Open CSV file.
filename = 'dataset.csv'

error_log = []
with open(filename, "rt") as file:
    data = file.read().split('\n')

csv_reader = csv.reader(data)
headers = next(csv_reader)

for row in csv_reader:
    # Get dataset name.
    url = row[0]
    dataset_name = url.split('/')[-1]

    # Fetch package from Data.Qld.
    package_dict = []
    try:
        package_dict = source.action.package_show(id=dataset_name)
    except Exception as e:
        error_response = {
            'package_id': dataset_name,
            'errors': ['Not able to load the package from source.']
        }
        error_log.append(error_response)

    if not package_dict:
        error_response = {
            'package_id': dataset_name,
            'errors': ['Not able to load the package from source.']
        }
        error_log.append(error_response)
        continue

    # Map dataset.
    new_package_dict = dataset_mapping(package_dict)

    if 'series' in package_dict['title']:
        # This will be resource-less package.
        new_package_dict['resources'] = []
        error = False
        new_package_dict_id = {}

        # Create the parent of series dataset.
        try:
            new_package_dict_id = destination.action.package_create(**new_package_dict)
        except Exception as e:
            error = True
            error_response = {
                'package_id': dataset_name,
                'errors': e.error_dict
            }
            error_log.append(error_response)

        # Create individual package for each resource that belong to above series dataset.
        if ('resources' in package_dict) and not error:
            for resource in package_dict.get('resources'):
                new_series_package_dict = resource_to_dataset_mapping(resource, new_package_dict, new_package_dict_id)

                try:
                    new_series_package_dict_id = destination.action.package_create(**new_series_package_dict)
                except Exception as e:
                    error_response = {
                        'resource_id': resource.get('id'),
                        'errors': e.error_dict
                    }
                    error_log.append(error_response)
    else:
        # Map Resources.
        new_package_dict['resources'] = []
        if 'resources' in package_dict:
            for resource in package_dict.get('resources'):
                new_package_dict['resources'].append(resource_mapping(resource))

        try:
            new_package_dict_id = destination.action.package_create(**new_package_dict)
        except Exception as e:
            error_response = {
                'package_id': dataset_name,
                'errors': e.error_dict
            }
            error_log.append(error_response)

if error_log:
    print(pformat(error_log))

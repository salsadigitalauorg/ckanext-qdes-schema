import csv
import os
import json

from ckanapi import RemoteCKAN
from pprint import pformat


def get_vocab_value(value, f_name):
    """
    @todo
    Some value is only fraction of the URI, some of them are the label, and others are URI.
    This function will return the data in following order.
    - Search by the full URI
    - Search by the fraction of URI with either space, dash or camel case.
    - Search by the label
    """
    return value


def dataset_mapping(dataset, row):
    """
    Map QLD dataset to QDES dataset.
    """
    mapped_dataset = {}

    # Get all fields available on QDES dataset.
    with open('../qdes_ckan_dataset.json') as f:
        scheme = json.load(f)

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

    # Map owner_org. @todo: fix this.
    mapped_dataset['owner_org'] = 'yolo'

    # Map license, license_id on QLD only a fraction of the vocab data that controlled QDES field.
    # mapped_dataset['license_id'] = get_vocab_value(dataset.get('license_id'), 'license')
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
    # Map classification_and_access_restrictions. @todo: fix this.
    mapped_dataset['classification_and_access_restrictions'] = 'http://registry.it.csiro.au/def/isotc211/MD_ClassificationCode/confidential'

    # @todo: this should be json.
    mapped_dataset['classification'] = 'http://registry.it.csiro.au/def/datacite/resourceType/Audiovisual'
    mapped_dataset['topic'] = 'https://gcmdservices.gsfc.nasa.gov/kms/concept/feef8827-92a6-4d1d-b6a5-ecda38a32656'

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

    # Map size. @todo: source has bytes, KiBytes, etc. destination only accept integer in bytes.
    mapped_resource['size'] = 0

    # Map format. @todo: fix this. issue example: on source there is "JSON" as value, but the format has many JSON.
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


# Set the import source and destination.
source = RemoteCKAN('https://www.data.qld.gov.au')
destination = RemoteCKAN(
    os.environ['LAGOON_ROUTE'],
    apikey='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJYeHVTSTRXTDdSS1FwM0hIYVJKS0Q3RmNIQjFnR2pSQVZGZlFSR21SdVJfRVhLR0lkNXpMTjRxZEJoTzkzUlppNHAtWWVHQ0JQeHlydHVDayIsImlhdCI6MTYwMzcwNDIwOX0.ee3V6xluDQzGDiagrjX-jZXMrOow6KAUeLjmD2Tw6LU')

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
        error_log.append([url, str(e)])

    if not package_dict:
        continue

    # Strip out unnecessary fields.
    strip_out_fields = [
        'archiver',
        'qa',
        'data_driven_application'
    ]
    for strip_out_field in strip_out_fields:
        if strip_out_field in package_dict:
            package_dict.pop(strip_out_field)

    if 'series' in package_dict['title']:
        pass
    else:
        # Map dataset.
        new_package_dict = dataset_mapping(package_dict, row)

        # Added default field.
        new_package_dict['package'] = 'dataset'

        # Map Resources.
        if 'resources' in package_dict:
            new_package_dict['resources'] = []
            for resource in package_dict.get('resources'):
                new_package_dict['resources'].append(resource_mapping(resource))

        try:
            # print(pformat(package_dict.get('notes')))
            new_package_dict_id = destination.action.package_create(**new_package_dict)
        except Exception as e:
            print(e)
            error_log.append(e)

    # print(new_dataset['resources'])

    # break

if error_log:
    print(error_log)

# print(headers)

# for row in csv_rows:
#     # row = https://www.data.qld.gov.au/dataset/sali-soil-chemistry-api
#     dataset_name = row.split('/')[:-1]
#     # Fetch package from Data.Qld
#     # e.g. https://www.data.qld.gov.au/api/action/package_show?id=matters-of-state-environmental-significance-queensland-series
#     package_dict = source.action.package_show(id=dataset_name)
#     # Strip out unnecessary fields, e.g.
#     archiver
#     qa
#     data_driven_application
#     # for each resource
#     # strip out: archiver, qa, datastore_*
#     # This dataset on the source is the parent of a series
#     if 'series' in package_dict['title'].lower():
#         resources = package_dict['resources']
#         package_dict.pop('resources')
#         # Do field mapping here
#         # Set any mandatory field defaults
#         # Create a dataset in DES
#         try:
#             # This will be a resource-less dataset
#             # new_package_dict_id = destination.action.package_create(**new_package_dict)
#             for resource in resources:
#                 # Do field mapping here
#                 # Set any mandatory field defaults
#                 try:
#                     child_package_dict_id = destination.action.package_create(**new_child_package_dict)
#                     # create "isPartOf" relation between child_package_dict_id (subject_package_id) and new_package_dict_id (object_package_id)
#                     # https://docs.ckan.org/en/2.9/api/#ckan.logic.action.create.package_relationship_create
#                     # destination.action.package_relationship_create(subject=child_package_dict_id, object=new_package_dict_id, type="isPartOf")
#                 except Exception as e:
#                     error_log.append(str(e))
#         except Exception as e:
#             error_log.append(str(e))
#     else:
#         # NOT A SERIES DATASET
#         new_package_dict = package_dict
#         # @TODO: What to do with groups?
#         # Do field mapping here
#         # Set any mandatory field defaults
#         # Create a dataset in DES
#         try:
#         # new_package_dict_id = destination.action.package_create(**new_package_dict)
#         except Exception as e:
#             error_log.append(str(e))
# Park this until we get confirmation from DES
# Iterate through the series list and create:
# a new dataset (child) for each resource in the series parent dataset
# create "isPart" relationships between the series parent, and it's children...

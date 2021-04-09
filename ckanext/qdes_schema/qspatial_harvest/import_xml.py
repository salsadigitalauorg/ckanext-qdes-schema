import glob
import json
import os
import csv
import pdb

from ckanapi import RemoteCKAN
from qspatial_object import QSpatialObject
from pprint import pformat, pprint
from datetime import datetime as dt


def get_remote_ckan():
    remoteCKAN = RemoteCKAN(
        os.environ['LAGOON_ROUTE'],
        os.environ['HARVEST_API_KEY']
    )
    return remoteCKAN


def get_ckan_packages():
    ckan_packages = []

    files = glob.glob('xml_files/*.xml')
    log_file = 'logs/{0}.txt'.format(dt.now().strftime("%Y%m%d-%H%M%S"))
    count = 0
    csv_rows = [row for row in csv.DictReader(open('DES_Datasets_QSpatial_v1.csv', "r"))]
    with get_remote_ckan() as remoteCKAN:
        data_service = remoteCKAN.action.package_show(id='qspatial')
        owner_org = os.environ['OWNER_ORG']
        for file in files:
            count += 1
            if count > 1000:
                break
            # Get dataset identifier from file name
            # Bit of a hack bt easier then doing a regex
            identifier = file.replace('xml_files/', '').replace('.xml', '')
            csv_row = next((row for row in csv_rows if identifier in row.get('URL')), None)
            try:
                print(f"Creating QSpatial object for {csv_row.get('Title')}")
                obj = QSpatialObject(file, csv_row, remoteCKAN, log_file, data_service, owner_org, True)
                ckan_packages.append(obj.get_ckan_package_dict())
            except Exception as ex:
                print(f'ERROR: {pformat(ex)}')
                append_error(csv_row.get('Title'), 'Error creating QSpatialObject', {'url': csv_row.get('URL')})
    return ckan_packages


def create_package(remoteCKAN, package):
    # print(pformat(package))

    try:
        print(f"Creating CKAN package for {package.get('title', None)}")
        result = remoteCKAN.action.package_create(**package)
        package['id'] = result.get('id')
    except Exception as e:
        append_error(package.get('title'), str(e), package)


def append_error(dataset_title, error, package):
    # log =  {'error': str(error)}
    # error_log.append(log) if log not in error_log else error_log
    log = [dataset_title, package.get('url'), error]
    error_log.append(log) if log not in error_log else error_log


def main():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    packages = get_ckan_packages()

    with get_remote_ckan() as remoteCKAN:
        distinct_package_fields = {}
        package_fields = [
            # 'parent_identifier'
            # 'classification',
            # 'topic',
            # 'contact_point',
            # 'contact_publisher',
            # 'contact_other_party',
            # 'publication_status',
            # 'classification_and_access_restrictions',
            # 'license_id',
            # 'owner_org',
            # 'dataset_language',
            # 'temporal_start',
            # 'temporal_end',
            # 'tag_string',
            # 'spatial_lower_left',
            # 'spatial_upper_right',
            # 'spatial_content_resolution',
            # 'spatial_representation',
            # 'spatial_datum_crs',
            # 'dataset_release_date',
            # 'update_schedule',
            # 'quality_description',
            # 'url',
            # 'lineage_description',
            # 'rights_statement'
        ]

        distinct_resource_fields = {}
        resource_fields = [
            # 'format',
            # 'size',
            # 'service_api_endpoint',
            # 'rights_statement',
            # 'license',
            # 'data_services'
        ]
        for check_field in package_fields:
            distinct_package_fields[check_field] = []

        for check_field in resource_fields:
            distinct_resource_fields[check_field] = []

        parent_packages = [package for package in packages if package.get('parent_identifier', None) == None]
        child_packages = [package for package in packages if package.get('parent_identifier', None) != None]
        # Create parent packages first to get package id
        for package in parent_packages:
            for field in package:
                if field in distinct_package_fields:
                    distinct_package_fields[field].append(package.get(field)) if package.get(field) not in distinct_package_fields[field] else distinct_package_fields[field]

            for resource in package.get('resources', []):
                for field in resource:
                    if field in distinct_resource_fields:
                        distinct_resource_fields[field].append(resource.get(field)) if resource.get(field) not in distinct_resource_fields[field] else distinct_resource_fields[field]

            # pprint(package)
            # Parent package is a series dataset with no resources so we need to remove them
            package.pop('resources')
            create_package(remoteCKAN, package)

        # Create child packages with parent package id
        for package in child_packages:
            for field in package:
                if field in distinct_package_fields:
                    distinct_package_fields[field].append(package.get(field)) if package.get(field) not in distinct_package_fields[field] else distinct_package_fields[field]

            for resource in package.get('resources', []):
                for field in resource:
                    if field in distinct_resource_fields:
                        distinct_resource_fields[field].append(resource.get(field)) if resource.get(field) not in distinct_resource_fields[field] else distinct_resource_fields[field]

            parent_package = next((parent_package for parent_package in parent_packages if package.get('parent_identifier', None) == parent_package.get('file_identifier', None)), None)
            if parent_package:
                # print('{0}: parent package found {1} for {2}'.format(parent_package.get('id'), parent_package.get('title'), package.get('title')))
                package['series_or_collection'] = json.dumps([{"id": parent_package.get('id'), "text": parent_package.get('title')}])

            # pprint(package)
            create_package(remoteCKAN, package)

        pprint(distinct_package_fields)
        pprint(distinct_resource_fields)

    if error_log:
        pprint(json.dumps(error_log, indent=2))
        log_file = 'logs/error_{0}.csv'.format(dt.now().strftime("%Y%m%d-%H%M%S"))
        error_log_file = open(log_file, 'a')
        error_log_file.write("Dataset Title, URL, Error\n")
        for error in error_log:
            error_log_file.write(f"{error[0]},{error[1]},{json.dumps(error[2],indent=2)}\n")
        error_log_file.close()


error_log = []

if __name__ == '__main__':
    main()

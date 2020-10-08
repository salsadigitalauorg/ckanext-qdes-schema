import glob
import json

from ckanapi import LocalCKAN, ValidationError
from ckanapi import RemoteCKAN, NotAuthorized
from qspatial_object import QSpatialObject
from pprint import pformat


def get_ckan_packages():
    ckan_packages = []

    files = glob.glob('xml_files/*.xml')
    for file in files:
        obj = QSpatialObject(file)
        ckan_packages.append(obj.get_ckan_package_dict())

    return ckan_packages


def create_package(package):
    print(pformat(package))

    # registry = LocalCKAN(username='salsa')
    registry = RemoteCKAN(
        'http://qdes-ckan-29.docker.amazee.io',
        apikey='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJmcXBmWjNCX0l4cTVBLWtQVkxzZnlvZ1l1aUxOZ3ljVDJKVFJmU0tISUR1dVpCd1dOYVhWTE9uM29VSlVTc2lRMW5wbEpYcFhCVXBBQ19jciIsImlhdCI6MTYwMjExOTk0MX0.27b7grSskCFljyuerAj7iW5a_peQUtU0IRKAPUHestI'
    )
    try:
        registry.action.package_create(**package)
    except Exception as e:
        print(str(e))


def main():
    packages = get_ckan_packages()

    counter = 0

    for package in packages:
        if counter < 3:
            create_package(package)
        counter += 1

if __name__ == '__main__':
    main()

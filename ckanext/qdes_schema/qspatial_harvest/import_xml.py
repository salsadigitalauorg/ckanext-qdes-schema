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
    registry = RemoteCKAN('http://qdes-ckan-29.docker.amazee.io', apikey='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJTb3VySmhveFZ1U3dXUy16Slh6ZUcwcFFVT3hpendMNS05SVJJWHRfc0xOdUVtdXFyNTQ3VHFUTHZkejI2NkpBd196YVh0OUZpLW8ycjhWQiIsImlhdCI6MTYwMTI4Njg5N30.yXi8dmH1b8RRF_S50F5yzUF_pYAD7pme45DbjSouJXQ')
    try:
        registry.action.package_create(**package)
    except Exception as e:
        print(str(e))


def main():
    packages = get_ckan_packages()

    for package in packages:
        create_package(package)

if __name__ == '__main__':
    main()

import glob
import os

from ckanapi import RemoteCKAN
from qspatial_object import QSpatialObject
from pprint import pformat
from datetime import datetime as dt


def get_remote_ckan():
    remoteCKAN = RemoteCKAN(
        'http://qdes-ckan-29.docker.amazee.io',
        apikey='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJGX0IzNUhRSGlHVHNWWXV4eWZHYm10bzVxNDZ2dWNrSVVlTV9pcERQeWJfMWU1cFQxZk9vMWl6WnVqUkZrMkZzMWJHZENOOFgwNllqQ1Y4RSIsImlhdCI6MTYwNDAwMzMxMX0.qvZ-trs4sKRy4wyj774BtefV-8-7auoMpHSkLrP8B8c'
    )
    return remoteCKAN


def get_ckan_packages(remoteCKAN):
    ckan_packages = []

    files = glob.glob('xml_files/*.xml')
    log_file = 'logs/{0}.txt'.format(dt.now().strftime("%Y%m%d-%H%M%S"))
    count = 0
    for file in files:
        count += 1
        if count > 1000:
            break
        obj = QSpatialObject(file, remoteCKAN, log_file, False)
        ckan_packages.append(obj.get_ckan_package_dict())

    return ckan_packages


def delete_package(remoteCKAN, package):
    print(package.get('name'))

    try:
        remoteCKAN.action.dataset_purge(id=package.get('name'))
    except Exception as e:
        print(str(e))


def main():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    with get_remote_ckan() as remoteCKAN:
        packages = get_ckan_packages(remoteCKAN)
        for package in packages:
            delete_package(remoteCKAN, package)


if __name__ == '__main__':
    main()

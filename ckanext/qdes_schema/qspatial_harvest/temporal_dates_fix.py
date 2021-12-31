from __future__ import print_function
from __future__ import absolute_import
import argparse
import json
import os


import ckan.plugins.toolkit as tk
from ckanext.qdes_schema.logic.helpers import dataservice_helpers as dataservice_helpers
import ckan.model as model


_context = None

def get_context():
    global _context
    if not _context:
        user = tk.get_action(u'get_site_user')(
            {u'model': model, u'ignore_auth': True}, {})
        _context = {u'model': model, u'session': model.Session,
                    u'user': user[u'name']}
    return _context

def get_ckan_packages():
    """
    Get all packages from CKAN.
    """
    dataservice = tk.get_action('package_show')(get_context, {'id': 'qspatial'})
    packages = dataservice_helpers.datasets_available_as_list(dataservice)
    for package in packages:
        print(package)
    breakpoint()
    return packages


def convert_dates_for_package(package):
    """
    Convert dates to ISO format.
    """
    if package.get('temporal_start'):
        date = package['temporal_start']
        

def main():
    packages = get_ckan_packages()

    for package in packages:
        convert_dates_for_package(package)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument(u'-c', u'--config', help=u'CKAN config file (.ini)')
    args = parser.parse_args()
    assert args.config, u'You must supply a --config'
    print(u'Loading config')
    try:
        from ckan.cli import load_config
        from ckan.config.middleware import make_app
        make_app(load_config(args.config))
    except ImportError:
       raise "Import error"
    print("Collect datasets")
    main()
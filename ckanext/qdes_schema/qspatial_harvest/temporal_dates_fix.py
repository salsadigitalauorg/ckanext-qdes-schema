from __future__ import print_function
from __future__ import absolute_import
import argparse
import json
import os
import datetime


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
    context = get_context()
    dataservice = tk.get_action('package_show')(context, {'id': 'qspatial'})
    return dataservice_helpers.datasets_available_as_list(dataservice)


def convert_dates_for_package(package):
    """
    Convert dates to ISO format.
    """
    context = get_context()
    pkg_data = {}
    try:
        pkg = tk.get_action('package_show')(context, {'id': package})
        pkg_data['id'] = pkg['id']
        if pkg.get('temporal_start', None):
            date = pkg['temporal_start']
            if len(date) < 10:
                date = date + '-01-01'
            dt = datetime.datetime.strptime(date, '%Y-%m-%d')
            pkg_data['temporal_start'] = dt.strftime('%Y-%m-%d')
        if pkg.get('temporal_end', None):
            date = pkg['temporal_end']
            if len(date) < 10:
                date = date + '-01-01'
            dt = datetime.datetime.strptime(date, '%Y-%m-%d')
            pkg_data['temporal_end'] = dt.strftime('%Y-%m-%d')
        tk.get_action('package_patch')(context, pkg_data)
    except tk.ObjectNotFound as e:
        raise e
    
        

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
       raise "Import config error"
    print("Collect datasets")
    main()
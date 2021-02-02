import ckan.plugins.toolkit as toolkit
import logging

from ckan.common import g
from pprint import pformat

log = logging.getLogger(__name__)
get_action = toolkit.get_action
request = toolkit.request


def data_service_admin_only(data_dict):
    if g.userobj:
        admins = g.userobj.sysadmin or g.userobj.get_groups('organization', 'admin')

        if not admins:
            if g.controller == 'dataservice':
                return {'success': False}
            elif data_dict:
                if data_dict.get('type') == 'dataservice':
                    return {'success': False}
                elif data_dict.get('id'):
                    try:
                        pkg = get_action('package_show')({}, {'id': data_dict.get('id')})
                        if pkg.get('type') == 'dataservice':
                            return {'success': False}
                    except Exception as e:
                        log.error(str(e))

    return {'success': True}


@toolkit.auth_allow_anonymous_access
def site_read(context, data_dict):
    return data_service_admin_only(data_dict)


def package_create(context, data_dict):
    return data_service_admin_only(data_dict)


def package_update(context, data_dict):
    return data_service_admin_only(data_dict)


def package_patch(context, data_dict):
    return data_service_admin_only(data_dict)


def package_delete(context, data_dict):
    return data_service_admin_only(data_dict)

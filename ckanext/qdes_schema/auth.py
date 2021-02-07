import ckan.authz as authz
import ckan.plugins.toolkit as toolkit
import logging

_ = toolkit._
log = logging.getLogger(__name__)


def user_can_manage_dataservices(next_auth, context, data_dict=None):
    # Use the context['user'] as per CKAN core logic/auth/create.py -> package_create
    user = context['user']

    if not data_dict or not isinstance(data_dict, dict):
        data_dict = {}

    # We only want our auth function to take effect if we are dealing with a data service
    # and the user is not an admin of some group - otherwise fall back to default CKAN
    # auth function
    package_type = data_dict.get('type')

    if 'dataservice' in [toolkit.get_endpoint()[0], package_type] \
            and not authz.has_user_permission_for_some_org(user, 'admin'):
        return {'success': False, 'msg': _('User not authorized to perform action')}

    return next_auth(context, data_dict)


@toolkit.chained_auth_function
def package_create(next_auth, context, data_dict):
    return user_can_manage_dataservices(next_auth, context, data_dict)


@toolkit.chained_auth_function
def package_update(next_auth, context, data_dict):
    return user_can_manage_dataservices(next_auth, context, data_dict)


@toolkit.chained_auth_function
def package_patch(next_auth, context, data_dict):
    return user_can_manage_dataservices(next_auth, context, data_dict)


@toolkit.chained_auth_function
def package_delete(next_auth, context, data_dict):
    return user_can_manage_dataservices(next_auth, context, data_dict)


def dataservice_index(context, data_dict):
    # Use the context['user'] as per CKAN core logic/auth/create.py -> package_create
    user = context['user']

    if not authz.has_user_permission_for_some_org(user, 'admin'):
        return {'success': False, 'msg': _('User not authorized to perform action')}
    return {'success': True}

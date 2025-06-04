import ckan.authz as authz
import ckan.plugins.toolkit as toolkit
import logging

from ckan.logic.auth import get_package_object

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
            and not authz.is_sysadmin(user):
        return {'success': False, 'msg': _('User not authorized to perform action')}

    return next_auth(context, data_dict)


@toolkit.chained_auth_function
def package_show(next_auth, context, data_dict):
    result = next_auth(context, data_dict)

    if not result.get('success', False):
        # Check to see if the dataset is private
        package = get_package_object(context, data_dict)
        if package and package.private:
            # Allow access for the related datasets tab to view the private dataset
            if toolkit.get_endpoint() == ('qdes_schema', 'related_datasets'):
                return {'success': True}
            # Make sure the call is coming from dataset view instead of api view
            elif toolkit.get_endpoint()[0] == 'dataset':
                toolkit.abort(403, 'Record not accessible')

    # return default ckan package_show auth result
    return result


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

    if not authz.is_sysadmin(user):
        return {'success': False, 'msg': _('User not authorized to perform action')}
    return {'success': True}

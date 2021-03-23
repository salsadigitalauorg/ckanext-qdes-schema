import logging
import json

from ckan.plugins import toolkit
from ckanext.qdes_schema.logic.helpers import dataservice_helpers, resource_helpers
from pprint import pformat

log = logging.getLogger(__name__)

get_action = toolkit.get_action


def dataservice_purge(context, data_dict):
    # CKAN only calls dataset_purge, when doing single purge.
    # See ckan/ckan_core/ckan/views/admin.py:L209
    # It calls [package_type]_purge, this action for handling those custom dataservice.
    get_action('dataset_purge')(context, data_dict)


@toolkit.chained_action
def dataset_purge(original_action, context, data_dict):
    # We need to remove dataservice that listed in any resources.
    try:
        pkg_dict = get_action('package_show')(context, {'id': data_dict.get('id')})

        if pkg_dict.get('type') == 'dataservice':
            resource_helpers.delete_resource_dataservice(
                context,
                data_dict.get('id'),
                dataservice_helpers.datasets_available_as_list(pkg_dict)
            )
    except Exception as e:
        log.error(str(e))

    return original_action(context, data_dict)


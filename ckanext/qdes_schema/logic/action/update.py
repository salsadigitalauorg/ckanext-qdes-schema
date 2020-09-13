import logging
import json

from ckan.plugins.toolkit import get_action, h
from ckanext.qdes_schema.logic.helpers import (
    dataservice_helpers as ds_helpers,
    resource_helpers as res_helpers)

log = logging.getLogger(__name__)


def dataservice_datasets_available(context, resource):
    """
    Update datasets_available field for a dataservice.
    This will be triggered by the following events:
    - dataset resource created
    - dataset resource updated
    - @TODO: dataset resource deleted
    - @TODO: data service updated
    - @TODO: data service deleted
    """
    pkg_dict = res_helpers.get_resource_package(context, resource['package_id'])

    if pkg_dict.get('type', None) == 'dataset':
        try:
            for dataservice in res_helpers.data_services_as_list(resource):

                dataservice_dict = ds_helpers.get_dataservice_from_uri(context, dataservice)

                if dataservice_dict:
                    datasets_available = ds_helpers.datasets_available_as_list(dataservice_dict)

                    dataset_url = h.url_for('dataset.read', id=pkg_dict['name'], _external=True)

                    # Update dataservice.
                    dataservice_dict['datasets_available'] = json.dumps(list(set([dataset_url] + datasets_available)))

                    # ref.: https://docs.ckan.org/en/2.9/api/#ckan.logic.action.patch.package_update
                    # "You must be authorized to edit the dataset and the groups that it belongs to."
                    context['ignore_auth'] = True
                    # package_patch seems to be failing validation here
                    get_action('package_update')(context, dataservice_dict)
        except Exception as e:
            log.error(str(e))

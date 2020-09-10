import logging
import requests
import json

from pprint import pformat
from ckan.plugins.toolkit import get_action
from ckan import model
from ckan.lib import helpers
from ckan.model import meta

log = logging.getLogger(__name__)

def update_datasets_available(context, pkg_dict):
    """
    Update datasets_available field on dataservice,
    this will be triggered on after_update and after_create of datsaset.
    """
    # Check if current package is dataset.
    type = context['package'].type if 'package' in context else None

    if (type is not None) and (type == 'dataset') and ('resources' in pkg_dict):
        # Load the resources.
        dataset_resources = pkg_dict['resources'] if len(pkg_dict['resources']) > 0 else ''

        if len(dataset_resources) > 0:
            # Get current dataset url.
            host = helpers.get_site_protocol_and_host()
            dataset_url = host[0] + '://' + host[1] + '/dataset/' + pkg_dict['name'] if len(host) > 0 else ''

            for resource in dataset_resources:
                if len(resource['data_services']) > 0:
                    # Load the dataservice json.
                    dataservices = None
                    try:
                        dataservices = json.loads(resource['data_services'])
                    except Exception as e:
                        log.error('Not able to load json from data_services.')

                    if dataservices is not None and len(dataservices) > 0:
                        for dataservice in dataservices:
                            # Load dataservice.
                            dataservice_name = dataservice.split('/')[-1]
                            dataservice_dict = get_action('package_show')(context, {'name_or_id': dataservice_name})

                            if len(dataservice_dict) > 0:
                                # Update dataservice.
                                current_datasets_available = []
                                try:
                                    if len(dataservice_dict['datasets_available']) > 0:
                                        current_datasets_available = json.loads(dataservice_dict['datasets_available'])
                                except Exception as e:
                                    log.error('Not able to load json from datasets_available.')

                                dataservice_dict['datasets_available'] = json.dumps(list(set([dataset_url] + current_datasets_available)))
                                get_action('package_update')(context, dataservice_dict)


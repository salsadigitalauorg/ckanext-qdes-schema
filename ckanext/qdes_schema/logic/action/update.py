import logging
import json

from ckan.plugins.toolkit import get_action, h, check_access
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


def update_related_resources(context, data_dict):
    """
    Update dataset related_resources metadata field
    """
    check_access('package_update', context, data_dict)

    dataset_id = data_dict.get('id', None)
    if dataset_id:
        model = context.get('model')
        try:
            dataset = model.Package.get(dataset_id)
            if dataset:
                current_related_resources = dataset._extras.get('related_resources', None)
                new_related_resources_value = json.dumps(data_dict.get('related_resources', None)) if isinstance(
                    data_dict.get('related_resources', None), dict) else data_dict.get('related_resources', None)
                if current_related_resources and current_related_resources.value != new_related_resources_value:
                    current_related_resources.value = new_related_resources_value
                # Always set the below values to None as they should have been included above in related_resources
                series_or_collection = dataset._extras.get('series_or_collection', None)
                if series_or_collection:
                    series_or_collection.value = None
                related_datasets = dataset._extras.get('related_datasets', None)
                if related_datasets:
                    related_datasets.value = None

                dataset.commit()

        except Exception as e:
            log.error(str(e))

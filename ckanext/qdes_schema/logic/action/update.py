import logging
import json

from ckan.plugins.toolkit import get_action, h, check_access, get_converter
from ckanext.qdes_schema.model import PublishLog
from ckanext.qdes_schema.logic.helpers import (
    dataservice_helpers as ds_helpers,
    resource_helpers as res_helpers)
from pprint import pformat

log = logging.getLogger(__name__)


def dataservice_datasets_available(context, data):
    """
    Update datasets_available field for a dataservice.
    This will be triggered by the following events:
    - dataset resource created
    - dataset resource updated
    - dataset resource deleted
    - @TODO: data service updated
    - @TODO: data service deleted

    On delete event, resource_deleted need to be True and resources are needed.
    """
    resource = data.get('resource', None)
    resource_deleted = data.get('resource_deleted', False)
    resources = data.get('resources', {})
    pkg_dict = res_helpers.get_resource_package(context, resource['package_id'])

    if pkg_dict.get('type', None) == 'dataset':
        try:
            for dataservice in res_helpers.data_services_as_list(resource):
                dataservice_dict = get_action('package_show')(context, {'name_or_id': dataservice})

                if dataservice_dict:
                    datasets_available = ds_helpers.datasets_available_as_list(dataservice_dict)

                    # Resource is about to be deleted, and it is associated with data service.
                    if resource_deleted:
                        # If this is the only one resource, remove the dataset from datasets_available field.
                        if len(resources) == 1:
                            datasets_available.remove(pkg_dict['id'])
                        else:
                            # Iterate to all other resources,
                            # and check if the resource is associated with current dataservice_dict.
                            remove_from_dataset_available = True
                            for res in resources:
                                if not res.get('id') == resource.get('id'):
                                    data_service_list = res.get('data_services', [])

                                    if dataservice_dict.get('id') in data_service_list:
                                        remove_from_dataset_available = False

                            if remove_from_dataset_available:
                                datasets_available.remove(pkg_dict['id'])

                        dataservice_dict['datasets_available'] = json.dumps(list(datasets_available))
                    else:
                        # Update dataservice.
                        dataservice_dict['datasets_available'] = json.dumps(
                            list(set([pkg_dict['id']] + datasets_available)))

                    # ref.: https://docs.ckan.org/en/2.9/api/#ckan.logic.action.patch.package_update
                    # "You must be authorized to edit the dataset and the groups that it belongs to."
                    site_user = get_action(u'get_site_user')({u'ignore_auth': True}, {})
                    ctx = {u'user': site_user[u'name'], 'ignore_auth': True}
                    get_action('package_update')(ctx, dataservice_dict)
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
                # The below values are only used on the form to compile into a list of relationships to add
                # Once the package has been created/updated the method helpers.update_related_resources will use the below fields to reconcile the relationships
                # We do not need to keep these values any more which can be potentially causing other undesired issues
                current_related_resources = dataset._extras.get('related_resources', None)
                if current_related_resources:
                    current_related_resources.value = None
                series_or_collection = dataset._extras.get('series_or_collection', None)
                if series_or_collection:
                    series_or_collection.value = None
                related_datasets = dataset._extras.get('related_datasets', None)
                if related_datasets:
                    related_datasets.value = None
                related_services = dataset._extras.get('related_services', None)
                if related_services:
                    related_services.value = None

                dataset.commit()

        except Exception as e:
            log.error(str(e))


def publish_log(context, data_dict):
    u"""
    Create publish_log.
    """
    try:
        publish_log_data = PublishLog.get(data_dict.get('id'))
        for key in data_dict:
            setattr(publish_log_data, key, data_dict[key])

        publish_log_data.save()

        return publish_log_data
    except Exception as e:
        log.error(e)
        return None

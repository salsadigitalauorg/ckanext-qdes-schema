import logging
import json

from ckan.plugins.toolkit import get_action, h, check_access, get_converter
from ckanext.qdes_schema.logic.helpers import (
    dataservice_helpers as ds_helpers,
    resource_helpers as res_helpers)

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
                        log.error('resource_deleted')
                        # If this is the only one resource, remove the dataset from datasets_available field.
                        if len(resources) == 1:
                            log.error('resources.length == 1')
                            datasets_available.remove(pkg_dict['id'])
                        else:
                            log.error('resources.length > 1')
                            # Iterate to all other resources,
                            # and check if the resource is associated with current dataservice_dict.
                            remove_from_dataset_available = True
                            for res in resources:
                                if not res.get('id') ==  resource.get('id'):
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
                # Create related_resources from datasets relationships as they are the source of truth
                relationships = h.get_subject_package_relationship_objects(dataset_id)
                related_resources = []
                if relationships:
                    for relationship in relationships:
                        id = relationship['object'] if relationship['object'] else relationship['comment']
                        text = relationship['title'] if relationship['object'] else relationship['comment']
                        type = relationship['type']
                        related_resources.append({"resource": {"id": id, "text": text}, "relationship": type})

                log.debug('related_resources: {}'.format(related_resources))

                if len(related_resources) > 0:
                    new_related_resources_value = json.dumps(related_resources)
                else:
                    new_related_resources_value = ''

                current_related_resources = dataset._extras.get('related_resources', None)
                if not current_related_resources:
                    # Create a new PackageExtra object for related_resources
                    dataset._extras['related_resources'] = model.PackageExtra(key='related_resources', value=new_related_resources_value)
                else:
                    current_related_resources.value = new_related_resources_value
                # Always set the below values to None as they should have been included above in related_resources
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

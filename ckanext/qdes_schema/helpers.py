import datetime
import logging

from ckan.plugins.toolkit import config, h, get_action, get_converter, get_validator, Invalid, request

log = logging.getLogger(__name__)


def is_legacy_ckan():
    return False if h.ckan_version() > '2.9' else True


def set_first_option(options, first_option):
    """Find the option (case insensitive) from the options text property and move it to the start of the list at index 0"""
    option = next((option for option in options if option.get('text').lower() == first_option.lower()), None)
    if option:
        old_index = options.index(option)
        options.insert(0, options.pop(old_index))
    return options


def get_current_datetime():
    """
    Returns current datetime.
    """
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')


def qdes_dataservice_choices(field):
    """
    Return choices for dataservice dropdown.
    """
    choices = []

    try:
        for data in get_action('get_dataservice')({}):
            choices.append({
                'value': config.get('ckan.site_url', None) + '/dataservice/' + data.name,
                'label': data.title
            })
    except Exception as e:
        log.error(str(e))

    return choices


def qdes_relationship_types_choices(field):
    """
    Return choices for dataset relationship types.
    """
    choices = []

    try:
        for data in h.get_relationship_types():
            #log.debug('qdes_relationship_types_choices: {0}'.format(data))
            choices.append({
                'value': data[0],
                'label': data[0]
            })
    except Exception as e:
        log.error(str(e))

    return choices


def update_related_resources(context, pkg_dict, reconcile_relationships=False):
    if reconcile_relationships:
        # Combine existing related_resources and new related_resources together
        existing_related_resources = get_converter('json_or_string')(request.form.get('existing_related_resources', '')) or []
        new_related_resources = get_converter('json_or_string')(pkg_dict.get('related_resources', '')) or []
        combined_related_resources = existing_related_resources + new_related_resources
        pkg_dict['related_resources'] = h.dump_json(combined_related_resources)

        remove_duplicate_related_resources(pkg_dict)
        reconcile_package_relationships(context, pkg_dict['id'], pkg_dict.get('related_resources', None))

    create_series_or_collection_relationships(context, pkg_dict)
    create_related_datasets_relationships(context, pkg_dict)
    create_related_resource_relationships(context, pkg_dict)
    data_dict = {"id": pkg_dict.get('id'), "related_resources": pkg_dict.get('related_resources')}
    get_action('update_related_resources')(context, data_dict)


def create_series_or_collection_relationships(context, pkg_dict):
    datasets = get_converter('json_or_string')(pkg_dict.get('series_or_collection', []))
    relationship_type = 'isPartOf'
    add_related_resources(pkg_dict, datasets, relationship_type)


def create_related_datasets_relationships(context, pkg_dict):
    datasets = get_converter('json_or_string')(pkg_dict.get('related_datasets', []))
    relationship_type = 'unspecified relationship'
    add_related_resources(pkg_dict, datasets, relationship_type)


def add_related_resources(pkg_dict, datasets, relationship_type):
    if not datasets or not isinstance(datasets, list):
        return
    related_resources = get_converter('json_or_string')(pkg_dict.get('related_resources', []))
    if not related_resources:
        related_resources = []

    for dataset in datasets:
        # Only add related_resource if it does not already exist
        if not any(resource for resource in related_resources
                   if resource.get('resource', {}).get('id', '') == dataset.get('id', '')
                   and resource.get('relationship', '') == relationship_type):
            related_resource = {}
            related_resource["resource"] = dataset
            related_resource["relationship"] = relationship_type
            related_resources.append(related_resource)
            log.debug('add_related_resources: {}'.format(related_resource))

    pkg_dict['related_resources'] =  h.dump_json(related_resources)


def create_related_resource_relationships(context, pkg_dict):
    remove_duplicate_related_resources(pkg_dict)
    related_resources = get_converter('json_or_string')(pkg_dict.get('related_resources', []))
    if related_resources and isinstance(related_resources, list):
        dataset_id = pkg_dict.get('id')
        create_relationships(context, dataset_id, related_resources)


def create_relationships(context, dataset_id, datasets):
    try:
        for dataset in datasets:
            relationship_type = dataset.get('relationship')
            relationship_dataset, relationship_url = get_dataset_relationship(context, dataset.get('resource'))

            if relationship_dataset or relationship_url:
                relationship = get_action('package_relationship_create')(context, {
                    'subject': dataset_id,
                    'object': relationship_dataset,
                    'type': relationship_type,
                    'comment': relationship_url,
                })
    except Exception as e:
        log.debug('create_relationships error: {0}'.format(e))
        raise


def get_dataset_relationship(context, dataset):
    relationship_dataset = None
    relationship_url = None
    dataset_id = dataset.get('id', '')
    try:
        get_validator('package_id_exists')(dataset_id, context)
        relationship_dataset = dataset_id
    except Invalid:
        # Dataset does not exist so must be an external dataset URL
        # Validation should have already happened in validator 'qdes_validate_related_dataset' so the dataset should be a URL to external dataset
        relationship_url = dataset_id

    return (relationship_dataset, relationship_url)


def reconcile_package_relationships(context, pkg_id, related_resources):
    """
    Only delete package relationships for the dataset when the relationship
    no longer exists in the `related_resources` field

    Called on IPackageController `after_update`

    :param context:
    :param pkg_id: package/dataset ID
    :return:
    """
    model = context.get('model')
    existing_relationships = get_action('subject_package_relationship_objects')(context, {'id': pkg_id})

    # `related_resources` might be an empty string
    related_resources = related_resources or None

    # If `related_resources` is empty - it indicates that all related resources have been removed from the dataset
    if not related_resources:
        # Delete ALL existing relationships for this dataset
        log.debug('Deleting ALL package_relationship records for dataset id {0}'.format(pkg_id))
        get_action('package_relationship_delete_all')(context, {'id': pkg_id})
    else:
        # Convert the `related_resources` JSON string into a more usable structure
        related_resources = get_converter('json_or_string')(related_resources)
        # Check each existing relationship to see if it still exists in the dataset's related_resources
        # if not, delete it.
        for relationship in existing_relationships:
            matching_related_resource = None

            # If it's an external URI we can process straight away
            if not relationship.object_package_id:
                matching_related_resource = [resource for resource in related_resources
                                             if resource['relationship'] == relationship.type
                                             and resource['resource'] == relationship.comment]
            else:
                try:
                    matching_related_resource = [resource for resource in related_resources
                                                 if resource['relationship'] == relationship.type
                                                 and resource['resource'] == relationship.object_package_id]
                except Exception as e:
                    log.error(str(e))

            if not matching_related_resource:
                # Delete the existing relationship from `package_relationships` as it no longer exists in the dataset
                relationship.purge()
                model.meta.Session.commit()


def remove_duplicate_related_resources(pkg_dict):
    related_resources = get_converter('json_or_string')(pkg_dict.get('related_resources', []))
    if related_resources and isinstance(related_resources, list):
        distinct_list = []
        for related_resource in related_resources:
            dataset_id = related_resource.get('resource', {}).get('id', '')
            relationship_type = related_resource.get('relationship', '')

            if not any(distinct_dataset for distinct_dataset in distinct_list
                       if distinct_dataset.get('resource', {}).get('id', '') == dataset_id
                       and distinct_dataset.get('relationship', '') == relationship_type):
                distinct_list.append(related_resource)
       
        pkg_dict['related_resources'] = h.dump_json(distinct_list)


def get_related_versions(id):
    """
    Get related versions of dataset, index 0 is the current version.
    """
    successors = get_action('get_all_successor_versions')({}, {'id': id})
    predecessors = get_action('get_all_predecessor_versions')({}, {'id': id})

    versions = []
    try:
        # Load provided version.
        package_dict = get_action('package_show')({}, {'id': id})

        # Build versions list.
        versions = successors + [package_dict] + predecessors
    except Exception as e:
        log.error(str(e))

    return list(version for version in versions if version.get('state') != 'deleted')


def get_all_relationships(id):
    return get_action('get_all_relationships')({}, id)

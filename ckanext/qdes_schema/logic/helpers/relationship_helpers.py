import ckan.plugins.toolkit as toolkit
import json
import logging

log = logging.getLogger(__name__)


def convert_related_resources(related_resources):
    """
    Adds the source property to 
    If resource is a URL the source is 'external' otherwise the source is 'ckan' dataset
    """
    related_resources = toolkit.get_converter('json_or_string')(related_resources)
    if isinstance(related_resources, list):
        for related_resource in related_resources:
            if related_resource['resource'].startswith('http'):
                related_resource['source'] = 'external'
            else:
                related_resource['source'] = 'ckan'

    return related_resources


def convert_related_resources_to_dict_list(related_resources):
    """
    The package.related_resources field is stored as a JSON string
    and currently stores related resources in the form:
        {"resources":["http://www.google.com","dataset-a","first-dataset"],"relationships":["isPartOf","unspecified relationship","unspecified relationship"],"count":3}
    to make it easier to process related resources when processing relationships
    we convert it to a list of dict objects, where each dict contains 1 relationship, e.g.
        [
            {'resource': 'http://www.google.com', 'relationship': 'isPartOf', 'source': 'external'},
            {'resource': 'dataset-a', 'relationship': 'unspecified relationship', 'source': 'ckan'},
            ...
        ]
    :param related_resources:
    :return:
    """
    dict_list = []
    related_resources = toolkit.get_converter('json_or_string')(related_resources)
    if isinstance(related_resources, dict):
        for i in range(0, related_resources.get('count', 0)):
            data_dict = {
                'resource': related_resources['resources'][i],
                'relationship': related_resources['relationships'][i],
                'source': 'ckan'
            }
            if data_dict['resource'].startswith('http'):
                data_dict['source'] = 'external'
            dict_list.append(data_dict)
    return dict_list


def get_superseded_versions(related_resources, versions):
    superseded_versions = []

    if 'replaces' in related_resources:
        # Adding a check here for when the JSON format of `related_resources` changes
        # from:
        #   {"resources": ["one", "two"], "relationships": ["isPartOf", "replaces"], "count": 2}
        # to:
        #   [
        #       {"resource": "one", "relationship": "isPartOf"},
        #       {"resource": "two", "relationship": "replaces"},
        #   ]
        try:
            if related_resources.startswith('{'):
                related_resources_dict = convert_related_resources_to_dict_list(related_resources)
            else:
                related_resources_dict = json.loads(related_resources)

            superseded_dataset_id = None

            # Find the related resource that has been superseded
            for related_resource in related_resources_dict:
                if related_resource['relationship'] == 'replaces':
                    superseded_dataset_id = related_resource['resource']
                    break

            if superseded_dataset_id:
                # Loop through versions and get the details for display
                for version in versions:
                    if version['name'] == superseded_dataset_id \
                            or version['id'] == superseded_dataset_id:
                        superseded_versions.append({
                            'id': version['id'],
                            'name': version['name'],
                            'title': version['title'],
                            'publication_status': version['publication_status'],
                        })
                        break
        except Exception as e:
            log.error(str(e))

    return superseded_versions

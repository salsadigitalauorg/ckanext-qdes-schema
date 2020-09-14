import ckan.plugins.toolkit as toolkit
import logging

log = logging.getLogger(__name__)


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

import ckan.plugins.toolkit as toolkit
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

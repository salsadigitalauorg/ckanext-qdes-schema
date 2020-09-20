import datetime
import logging

from ckan.plugins.toolkit import config, h, get_action
from pprint import pformat


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

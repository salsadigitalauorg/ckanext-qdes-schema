import logging
import json

from ckan.logic import NotFound
from ckan.plugins.toolkit import get_action

log = logging.getLogger(__name__)


def get_dataset_from_uri(context, uri):
    # `package_show` action will raise a NotFound exception if dataset does not exist
    try:
        return get_action('package_show')(context, {
            'name_or_id': uri.split('/')[-1]
        })
    except NotFound as e:
        log.error(e)

    return {}

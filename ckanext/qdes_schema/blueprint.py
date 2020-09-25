import ckan.lib.base as base
import ckan.logic as logic
import ckan.plugins.toolkit as toolkit
import logging

from ckan.common import _, c, request
from ckanext.qdes_schema import helpers
from flask import Blueprint
from pprint import pformat

abort = base.abort
get_action = logic.get_action
log = logging.getLogger(__name__)
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
render = toolkit.render

qdes_schema = Blueprint('qdes_schema', __name__)


def related_datasets(id):
    try:
        related = []
        all_relationships = helpers.get_all_relationships(id)

        for relationship in all_relationships:
            if relationship.get('type') not in ['isPartOf', 'hasPart']:
                related.append(relationship)

        extra_vars = {}
        extra_vars['pkg_dict'] = get_action('package_show')({}, {'id': id})
        extra_vars['related'] = related

        return render('package/related_datasets.html', extra_vars=extra_vars)
    except (NotFound, NotAuthorized):
        abort(404, _('Related dataset not found'))


qdes_schema.add_url_rule(u'/dataset/<id>/related-datasets', view_func=related_datasets)

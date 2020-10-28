import ckan.lib.base as base
import ckan.logic as logic
import ckan.plugins.toolkit as toolkit
import logging

from ckan.common import _, c, request
from ckanext.qdes_schema import helpers
from flask import Blueprint
from pprint import pformat
from ckanext.qdes_schema.logic.helpers import (
    dataservice_helpers as dataservice_helpers, dataset_helpers as dataset_helpers)

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


def dataset_metadata(id):
    try:
        extra_vars = {}
        extra_vars['pkg_dict'] = get_action('package_show')({}, {'id': id})

        return render('package/metadata.html', extra_vars=extra_vars)
    except (NotFound, NotAuthorized):
        abort(404, _('Dataset metadata not found'))


def resource_metadata(id, resource_id):
    try:
        extra_vars = {}
        extra_vars['pkg_dict'] = get_action('package_show')({}, {'id': id})
        extra_vars['package'] = extra_vars['pkg_dict']
        extra_vars['resource'] = []
        extra_vars['current_resource_view'] = None

        for resource in extra_vars['package'].get('resources', []):
            if resource['id'] == resource_id:
                extra_vars['resource'] = resource
                break
        if not extra_vars['resource']:
            abort(404, _('Resource not found'))

        return render('scheming/package/resource_metadata.html', extra_vars=extra_vars)
    except (NotFound, NotAuthorized):
        abort(404, _('Resource metadata not found'))


def datasets_available(id):
    try:
        dataservice = get_action('package_show')({}, {'id': id})
        extra_vars = {}
        extra_vars['pkg_dict'] = dataservice
        datasets_available = []
        for dataset_url in dataservice_helpers.datasets_available_as_list(dataservice):
            dataset = dataset_helpers.get_dataset_from_uri({}, dataset_url)
            datasets_available.append({'title': dataset.get('title', None), 'url': dataset_url})

        extra_vars['datasets_available'] = datasets_available
        return render('package/available_datasets.html', extra_vars=extra_vars)
    except (NotFound, NotAuthorized):
        abort(404, _('Available datasets not found'))


qdes_schema.add_url_rule(u'/dataset/<id>/related-datasets', view_func=related_datasets)
qdes_schema.add_url_rule(u'/dataset/<id>/metadata', view_func=dataset_metadata)
qdes_schema.add_url_rule(u'/dataservice/<id>/metadata', endpoint='dataservice_metadata', view_func=dataset_metadata)
qdes_schema.add_url_rule(u'/dataset/<id>/resource/<resource_id>/metadata', view_func=resource_metadata)
qdes_schema.add_url_rule(u'/dataservice/<id>/datasets-available', view_func=datasets_available)

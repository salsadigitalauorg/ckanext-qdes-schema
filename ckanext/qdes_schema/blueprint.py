import ckan.lib.base as base
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckanext.qdes_schema.constants as constants
import logging

from ckan.common import _, c, request
from ckanext.qdes_schema import helpers
from flask import Blueprint
from pprint import pformat
from ckanext.qdes_schema.logic.helpers import dataservice_helpers as dataservice_helpers

abort = base.abort
get_action = logic.get_action
log = logging.getLogger(__name__)
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
render = toolkit.render
h = toolkit.h
clean_dict = logic.clean_dict
tuplize_dict = logic.tuplize_dict
parse_params = logic.parse_params

qdes_schema = Blueprint('qdes_schema', __name__)


def related_datasets(id_or_name):
    try:
        related = []

        pkg_dict = get_action('package_show')({}, {'id': id_or_name})

        all_relationships = helpers.get_all_relationships(pkg_dict['id'])

        for relationship in all_relationships:
            if relationship.get('type') not in ['isPartOf', 'hasPart']:
                related.append(relationship)

        extra_vars = {
            'pkg_dict': pkg_dict,
            'related': related
        }

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
        for dataset_id in dataservice_helpers.datasets_available_as_list(dataservice):
            dataset = get_action('package_show')({}, {'id': dataset_id})
            dataset_url = h.url_for('dataset.read', id=dataset_id)
            datasets_available.append({'title': dataset.get('title', None), 'url': dataset_url})

        extra_vars['datasets_available'] = datasets_available
        return render('package/available_datasets.html', extra_vars=extra_vars)
    except (NotFound, NotAuthorized):
        abort(404, _('Available datasets not found'))


def datasets_schema_validation(id):
    extra_vars = {}
    pkg = get_action('package_show')({}, {'id': id})
    pkg_validated = pkg.copy()
    extra_vars['pkg_errors'] = []
    extra_vars['res_errors'] = []
    extra_vars['pkg_dict'] = pkg
    extra_vars['data'] = []
    extra_vars['options'] = [
        {'text': 'Select publishing portal', 'value': 'none'},
        {'text': 'Opendata Portal', 'value': constants.PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA},
        # {'text': 'QSpatial', 'value': constants.PUBLISH_EXTERNAL_IDENTIFIER_QSPATIAL_SCHEMA},
        # {'text': 'SIR', 'value': constants.PUBLISH_EXTERNAL_IDENTIFIER_SIR_SCHEMA}
    ]
    extra_vars['selected_opt'] = {}
    extra_vars['valid'] = 0
    extra_vars['publication_message'] = {}

    if request.method == 'POST':
        data = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(
            request.form))))

        extra_vars['data'] = data

        if not data.get('schema') == 'none':
            if data.get('action') == 'validate':
                extra_vars = helpers.schema_validate(extra_vars, pkg_validated, data)
            elif data.get('action') == 'publish':
                publish_log = helpers.schema_publish(pkg, data)
                extra_vars['publication_message'] = {
                    'text': 'The distribution has been queued for publishing.',
                    'cls': 'alert-success'
                }
                if not publish_log:
                    extra_vars['publication_message'] = {
                        'text': 'The distribution could not be queued for publishing.',
                        'cls': 'alert-error'
                    }

        if not extra_vars['pkg_errors'] and not extra_vars['res_errors'] and not extra_vars['publication_message']:
            extra_vars['valid'] = 1

    return render('package/publish_metadata.html', extra_vars=extra_vars)


qdes_schema.add_url_rule(u'/dataset/<id_or_name>/related-datasets', view_func=related_datasets)
qdes_schema.add_url_rule(u'/dataset/<id>/metadata', view_func=dataset_metadata)
qdes_schema.add_url_rule(u'/dataservice/<id>/metadata', endpoint='dataservice_metadata', view_func=dataset_metadata)
qdes_schema.add_url_rule(u'/dataset/<id>/resource/<resource_id>/metadata', view_func=resource_metadata)
qdes_schema.add_url_rule(u'/dataservice/<id>/datasets-available', view_func=datasets_available)
qdes_schema.add_url_rule(u'/dataset/<id>/publish', methods=[u'GET', u'POST'],
                         view_func=datasets_schema_validation)

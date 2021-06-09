import ckan.lib.base as base
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckanext.qdes_schema.constants as constants
import ckanext.qdes_schema.jobs as jobs
import logging
import six
import json

from ckan.common import _, c, request
from ckanext.qdes_schema import helpers
from flask import Blueprint
from pprint import pformat
from ckanext.qdes_schema.logic.helpers import dataservice_helpers as dataservice_helpers
from flask import send_file

abort = toolkit.abort
get_action = toolkit.get_action
log = logging.getLogger(__name__)
NotFound = toolkit.ObjectNotFound
NotAuthorized = toolkit.NotAuthorized
ValidationError = toolkit.ValidationError
render = toolkit.render
h = toolkit.h
clean_dict = logic.clean_dict
tuplize_dict = logic.tuplize_dict
parse_params = logic.parse_params

qdes_schema = Blueprint('qdes_schema', __name__)


def related_datasets(id_or_name):
    try:
        context = {
            u'model': model,
            u'user': toolkit.g.user,
            u'auth_user_obj': toolkit.g.userobj
        }

        related = []

        pkg_dict = get_action('package_show')({}, {'id': id_or_name})

        all_relationships = helpers.get_all_relationships(pkg_dict['id'])

        for relationship in all_relationships:
            if relationship.get('type') not in ['Is Part Of', 'Has Part']:
                # Check for access, don't show to user if user has no permission
                # Example, non logged-in user should not see delete package.
                try:
                    # Only do check_access on internal datasets not external
                    # Internal datasets will have a pkg_id where external datasets do not
                    if relationship.get('pkg_id'):
                        toolkit.check_access('package_show', context, {'id': relationship.get('pkg_id')})
                    related.append(relationship)
                except (NotFound, NotAuthorized, ValidationError) as e:
                    # Let's continue to the next list.
                    log.warning(f"related_datasets: Relationship dataset {relationship.get('pkg_id')} access check error = {e}")
                    pass

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
            try:
                dataset = get_action('package_show')({}, {'id': dataset_id})
                dataset_url = h.url_for('dataset.read', id=dataset_id)
                dataset_title = h.get_pkg_title(dataset_id, dataset)
                datasets_available.append({'title': dataset_title, 'url': dataset_url})
            except (NotFound, NotAuthorized):
                # Let's continue to the next list.
                pass
            except Exception as e:
                log.error('datasets_available - Exception loading package ID {}'.format(dataset_id))
                log.error(str(e))
        extra_vars['datasets_available'] = datasets_available
        return render('package/available_datasets.html', extra_vars=extra_vars)
    except (NotFound, NotAuthorized):
        abort(404, _('Available datasets not found'))


def datasets_schema_validation(id):
    # Check the user has permission to clone the dataset
    context = {
        'model': model,
        'user': c.user,
        'auth_user_obj': c.userobj
    }
    toolkit.check_access('package_update', context, {'id': id})

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

    # Load publish_log data.
    extra_vars['publish_activities'] = helpers.get_publish_activities(pkg)

    # Process unpublish status.
    unpublish_log_id = request.params.get('unpublish', None)
    if unpublish_log_id == "0":
        extra_vars['unpublish'] = 0
    elif unpublish_log_id:
        extra_vars['unpublish'] = 1 if helpers.is_unpublish_pending(unpublish_log_id) else ''

    return render('package/publish_metadata.html', extra_vars=extra_vars)


def unpublish_external_dataset_resource(id):
    # Check the user has permission to clone the dataset
    context = {
        'model': model,
        'user': c.user,
        'auth_user_obj': c.userobj
    }
    toolkit.check_access('package_update', context, {'id': id})

    if not request.method == 'POST':
        return

    data = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(
        request.form))))

    pkg = get_action('package_show')({}, {'id': id})

    # Create job.
    resource_to_unpublish = {}
    for resource in pkg.get('resources', []):
        if resource.get('id') == data.get('unpublish_resource'):
            resource_to_unpublish = resource

    # Add to publish log.
    unpublish = 0
    try:
        publish_log = get_action('create_publish_log')({}, {
            'dataset_id': pkg.get('id'),
            'resource_id': resource_to_unpublish.get('id'),
            'trigger': constants.PUBLISH_TRIGGER_MANUAL,
            'destination': data.get('schema'),
            'status': constants.PUBLISH_STATUS_PENDING,
            'action': constants.PUBLISH_ACTION_DELETE
        })

        # Add to job worker queue.
        if publish_log:
            # Improvements for job worker visibility when troubleshooting via logs
            job_title = f'Unpublish external dataset resource: dataset_id={publish_log.dataset_id}, resource_id={publish_log.resource_id}, destination={publish_log.destination}'
            toolkit.enqueue_job(jobs.unpublish_external_distribution, [publish_log.id, c.user], title=job_title)
            unpublish = publish_log.id

    except Exception as e:
        log.error(str(e))

    return h.redirect_to('/dataset/{}/publish?unpublish={}'.format(id, unpublish))


def dataset_export(id, format):
    try:
        context = {
            u'model': model,
            u'user': toolkit.g.user,
            u'auth_user_obj': toolkit.g.userobj
        }
        if context.get('__auth_audit', None):
            context['__auth_audit'].pop()
        dataset = get_action('package_show')(context, {'id': id})
        # TODO: We might need to load some vocab serivce as objects to get label etc
        # if dataset['contact_publisher']:
        #     term = get_action('get_vocabulary_service_term')(context, {'term_uri': dataset['contact_publisher']})
        #     if term:
        #         dataset['contact_publisher'] = term
        all_relationships = helpers.get_all_relationships(dataset['id'])
        relationships = []
        
        for relationship in all_relationships:
            if relationship.get('type') in ['Is Part Of']:
                relationships.append(relationship)
                
        # TODO: Need to load all secure vocabs as dict objects
        # Load vocabualry service contact_point
        if dataset['contact_point']:
            secure_vocabulary_record = get_action('get_secure_vocabulary_record')(
                context, {'vocabulary_name': 'point-of-contact', 'query': dataset['contact_point']})
            if secure_vocabulary_record:
                dataset['contact_point'] = secure_vocabulary_record

        # if dataset['contact_creator']:
        #     secure_vocabulary_record = get_action('get_secure_vocabulary_record')(
        #         context, {'vocabulary_name': 'point-of-contact', 'query': dataset['contact_creator']})
        #     if secure_vocabulary_record:
        #         dataset['contact_creator'] = secure_vocabulary_record
        # Load vocabualry service spatial_representation
        if dataset.get('spatial_representation', None):
            secure_vocabulary_record = get_action('get_vocabulary_service_term')(
                {}, {'vocabulary_name': 'spatial_representation', 'term_uri': dataset['spatial_representation']})
            if secure_vocabulary_record:
                dataset['spatial_representation'] = secure_vocabulary_record
        # Load vocabualry service spatial_datum_crs
        if dataset.get('spatial_datum_crs',None):
            secure_vocabulary_record = get_action('get_vocabulary_service_term')(
                {}, {'vocabulary_name': 'spatial_datum_crs', 'term_uri': dataset['spatial_datum_crs']})
            if secure_vocabulary_record:
                dataset['spatial_datum_crs'] = secure_vocabulary_record

        # Get the identifiers 
        dataset['additional_info'] = json.loads(dataset.get('additional_info', []))
        dataset['identifiers'] = h.get_multi_textarea_values(dataset.get('identifiers', []))
        dataset['topic'] = h.get_multi_textarea_values(dataset.get('topic', []))
        dataset['quality_measure'] = json.loads(dataset.get('quality_measure', []))
        dataset['quality_description'] = json.loads(dataset.get('quality_description', []))
        dataset['lineage_description'] = h.get_multi_textarea_values(dataset.get('lineage_description', []))
        dataset['lineage_plan'] = h.get_multi_textarea_values(dataset.get('lineage_plan', []))
        dataset['lineage_inputs'] = json.loads(dataset.get('lineage_inputs', []))
        dataset['lineage_sensor'] = json.loads(dataset.get('lineage_sensor', []))
        dataset['cited_in'] = json.loads(dataset.get('cited_in', []))
        dataset['classification_and_access_restrictions'] = json.loads(dataset.get('classification_and_access_restrictions', []))
        dataset['rights_statement'] = list(dataset.get('rights_statement', []))
        dataset['series_or_relationships'] = relationships

        extra_vars = {}
        extra_vars['dataset'] = dataset
        data = None
        if format == 'XML (ISO-19139)':
            data = render(f'package/export/{format}.xml.j2', extra_vars=extra_vars)
        else:
            abort(400, _('Invalid export format'))

        if data:
            return send_file(six.BytesIO(data.encode('utf8')),
                             as_attachment=True,
                             attachment_filename=f'{dataset.get("title")}.xml')
    except (NotFound, NotAuthorized):
        abort(404, _('Dataset not found'))


qdes_schema.add_url_rule(u'/dataset/<id_or_name>/related-datasets', view_func=related_datasets)
qdes_schema.add_url_rule(u'/dataset/<id>/metadata', view_func=dataset_metadata)
qdes_schema.add_url_rule(u'/dataservice/<id>/metadata', endpoint='dataservice_metadata', view_func=dataset_metadata)
qdes_schema.add_url_rule(u'/dataset/<id>/resource/<resource_id>/metadata', view_func=resource_metadata)
qdes_schema.add_url_rule(u'/dataservice/<id>/datasets-available', view_func=datasets_available)
qdes_schema.add_url_rule(u'/dataset/<id>/publish', methods=[u'GET', u'POST'],
                         view_func=datasets_schema_validation)
qdes_schema.add_url_rule(u'/dataset/<id>/unpublish-external', methods=[u'POST'],
                         view_func=unpublish_external_dataset_resource)
qdes_schema.add_url_rule(u'/dataset/<id>/export/<format>',
                         view_func=dataset_export)

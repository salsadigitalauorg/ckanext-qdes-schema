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
import xml.dom.minidom
import os
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic

from ckan.common import _, c, request
from ckanext.qdes_schema import helpers
from flask import Blueprint
from pprint import pformat
from ckanext.qdes_schema.logic.helpers import dataservice_helpers as dataservice_helpers
from flask import send_file
from ckan.views import dataset as dataset_view
from ckan.lib.search import SearchIndexError
from six import text_type

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
check_access = toolkit.check_access
g = check_access = toolkit.g
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

        # Load existing relationship.
        relationships = h.get_subject_package_relationship_objects(extra_vars['pkg_dict'].get('id'))
        if relationships:
            extra_vars['pkg_dict']['related_resources'] = h.convert_relationships_to_related_resources(relationships)

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
    pkg_type = pkg.get('type') or 'dataset'
    if pkg_type == 'dataservice':
        return abort(404, _('The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.'))
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


def _get_term_obj(field_value, vocab_service_name):
    if isinstance(field_value, list):
        terms = []
        for uri in field_value:
            term = get_action('get_vocabulary_service_term')({}, {'vocabulary_service_name': vocab_service_name, 'term_uri': uri})
            if term:
                terms.append(dict(term))

        if terms:
            field_value = terms
    else:
        term = get_action('get_vocabulary_service_term')({}, {
            'vocabulary_service_name': vocab_service_name,
            'term_uri': field_value
        })

        if term:
            field_value = dict(term)

    return field_value


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
        vocab_value = {}
        if len(dataset.get('contact_point', '')) > 0:
            secure_vocabulary_record = get_action('get_secure_vocabulary_record')(
                context, {'vocabulary_name': 'point-of-contact', 'query': dataset['contact_point']})
            if secure_vocabulary_record:
                vocab_value = secure_vocabulary_record

        dataset['contact_point'] = vocab_value

        vocab_value = {}
        if len(dataset.get('metadata_contact_point', '')) > 0:
            secure_vocabulary_record = get_action('get_secure_vocabulary_record')(
                context, {'vocabulary_name': 'point-of-contact', 'query': dataset['metadata_contact_point']})
            if secure_vocabulary_record:
                vocab_value = secure_vocabulary_record

        dataset['metadata_contact_point'] = vocab_value

        # Get the identifiers
        dataset['additional_info'] = h.get_multi_textarea_values(dataset.get('additional_info', []))
        dataset['identifiers'] = h.get_multi_textarea_values(dataset.get('identifiers', []))
        dataset['topic'] = h.get_multi_textarea_values(dataset.get('topic', []))
        dataset['quality_measure'] = h.get_multi_textarea_values(dataset.get('quality_measure', []))
        dataset['quality_description'] = h.get_multi_textarea_values(dataset.get('quality_description', []))
        dataset['conforms_to'] = h.get_multi_textarea_values(dataset.get('conforms_to', []))
        dataset['lineage_inputs'] = h.get_multi_textarea_values(dataset.get('lineage_inputs', []))
        dataset['lineage_sensor'] = h.get_multi_textarea_values(dataset.get('lineage_sensor', []))
        dataset['lineage_responsible_party'] = h.get_multi_textarea_values(dataset.get('lineage_responsible_party', []))
        dataset['cited_in'] = h.get_multi_textarea_values(dataset.get('cited_in', []))
        dataset['classification_and_access_restrictions'] = h.get_multi_textarea_values(dataset.get('classification_and_access_restrictions', []))
        dataset['series_or_relationships'] = relationships

        # Load schema.
        single_multi_vocab_fields = [
            'topic',
            'spatial_representation',
            'spatial_datum_crs',
            'spatial_resolution',
            'contact_publisher',
            'publication_status',
            'update_schedule',
            'classification_and_access_restrictions',
            'license_id',
        ]

        group_vocab_fields = {
            'quality_measure': ['measurement'],
            'quality_description': ['dimension'],
        }

        res_single_multi_vocab_fields = [
            'format',
            'compression',
            'packaging'
        ]

        schema = h.scheming_get_dataset_schema(dataset.get('type'))
        for field in schema.get('dataset_fields', {}):
            if group_vocab_fields.get(field.get('field_name'), None):
                group = group_vocab_fields.get(field.get('field_name'))
                values = []
                for item in dataset.get(field.get('field_name')):
                    for group_vocab_field in group:
                        if item and item.get(group_vocab_field, None):
                            for field_group in field.get('field_group', {}):
                                if field_group.get('field_name') == group_vocab_field:
                                    group_field_value = item.get(group_vocab_field, {})
                                    group_field_vocab_name = field_group.get('vocabulary_service_name')
                                    item[group_vocab_field] = _get_term_obj(group_field_value, group_field_vocab_name)
                                    values.append(item)

            if field.get('vocabulary_service_name'):
                if field.get('field_name') in single_multi_vocab_fields:
                    dataset[field.get('field_name')] = _get_term_obj(dataset.get(field.get('field_name')), field.get('vocabulary_service_name'))

        new_resources = []
        for res in dataset.get('resources'):
            for field in schema.get('resource_fields', {}):
                if field.get('field_name') in res_single_multi_vocab_fields:
                    res[field.get('field_name')] = _get_term_obj(res.get(field.get('field_name')), field.get('vocabulary_service_name'))

            dataservices = []
            for id in h.get_multi_textarea_values(res.get('data_services', [])):
                if id:
                    dataservices.append(get_action('package_show')(context, {'id': id}))

            res['data_services'] = dataservices

            new_resources.append(res)

        if new_resources:
            dataset['resources'] = new_resources

        extra_vars = {}
        extra_vars['dataset'] = dataset
        data = None
        if format == 'XML (ISO-19139)':
            data = render(f'package/export/{format}.xml.j2', extra_vars=extra_vars)
        else:
            abort(400, _('Invalid export format'))

        if data:
            # Pretty print.
            dom = xml.dom.minidom.parseString(data)
            pretty_xml_as_string = dom.toprettyxml()

            # Remove weird whitespace.
            pretty_xml = os.linesep.join([s for s in pretty_xml_as_string.splitlines() if s.strip()])

            return send_file(six.BytesIO(pretty_xml.encode('utf8')),
                             as_attachment=True,
                             attachment_filename=f'{dataset.get("title")}.xml')
    except (NotFound, NotAuthorized):
        abort(404, _('Dataset not found'))


class CreateView(dataset_view.CreateView):
    def post(self, package_type):
        # If _ckan_phase is set to 'save_record' and pkg_name exists, set the dataset to active, save and redirect to dataset read page
        if request.form.get(u'_ckan_phase') == 'save_record' and len(request.form.get(u'pkg_name', '')) > 0:
            # Copied from https://github.com/ckan/ckan/blob/b123155c0fe1cd07736375ee5cf97abcd0a5fcf5/ckan/views/dataset.py#L542
            # Please make sure to keep up to date on any new CKAN release

            # The staged add dataset used the new functionality when the dataset is
            # partially created so we need to know if we actually are updating or
            # this is a real new.
            context = self._prepare()
            is_an_update = False
            try:
                data_dict = clean_dict(
                    dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
                )
            except dict_fns.DataError:
                return base.abort(400, _(u'Integrity Error'))
            try:
                # prevent clearing of groups etc
                context[u'allow_partial_update'] = True
                # sort the tags
                if u'tag_string' in data_dict:
                    data_dict[u'tags'] = dataset_view._tag_string_to_list(
                        data_dict[u'tag_string']
                    )
                if data_dict.get(u'pkg_name'):
                    is_an_update = True
                    # This is actually an update not a save
                    data_dict[u'id'] = data_dict[u'pkg_name']
                    del data_dict[u'pkg_name']
                    # QDES modification begins
                    data_dict[u'state'] = u'active'
                    # QDES modification ends
                    # this is actually an edit not a save
                    pkg_dict = get_action(u'package_update')(
                        context, data_dict
                    )
                    # QDES modification begins
                    return dataset_view._form_save_redirect(
                        pkg_dict[u'name'], u'new', package_type=package_type
                    )
                    # QDES modification ends
            except NotAuthorized:
                return base.abort(403, _(u'Unauthorized to read package'))
            except NotFound as e:
                return base.abort(404, _(u'Dataset not found'))
            except SearchIndexError as e:
                try:
                    exc_str = text_type(repr(e.args))
                except Exception:  # We don't like bare excepts
                    exc_str = text_type(str(e))
                return base.abort(
                    500,
                    _(u'Unable to add package to search index.') + exc_str
                )
            except ValidationError as e:
                errors = e.error_dict
                error_summary = e.error_summary
                if is_an_update:
                    # we need to get the state of the dataset to show the stage we
                    # are on.
                    pkg_dict = get_action(u'package_show')(context, data_dict)
                    data_dict[u'state'] = pkg_dict[u'state']
                    return dataset_view.EditView().get(
                        package_type,
                        data_dict[u'id'],
                        data_dict,
                        errors,
                        error_summary
                    )
                data_dict[u'state'] = u'none'
                return self.get(package_type, data_dict, errors, error_summary)
        else:
            # Continue to CKAN core CreateView.post code workflow
            return super().post(package_type)


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
qdes_schema.add_url_rule(u'/dataset/new', defaults={u'package_type': u'dataset'},
                         view_func=CreateView.as_view(str(u'new')))

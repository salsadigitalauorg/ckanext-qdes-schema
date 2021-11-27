import ckan.lib.navl.dictization_functions as df
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckanext.qdes.logic.helpers.report_helpers as qdes_report_helpers
import geojson
import json
import logging
import re

from datetime import datetime as dt
from ckan.common import config
from ckanext.scheming.validation import scheming_validator, scheming_choices
from pprint import pformat

log = logging.getLogger(__name__)
get_action = logic.get_action
h = toolkit.h
Invalid = toolkit.Invalid
missing = df.missing
StopOnError = df.StopOnError


def qdes_temporal_start_end_date(key, flattened_data, errors, context):
    """
    Validate the start and date.

    It will raise an error, when:
    - If the either start or end date is empty.
    - If the start date < end date.
    """
    error = None

    temporal_start_value = flattened_data.get(('temporal_start',), None)
    if temporal_start_value:
        split = temporal_start_value.split('T')
        temporal_start_value = split[0] if len(split) > 1 else temporal_start_value

    temporal_end_value = flattened_data.get(('temporal_end',), None)
    if temporal_end_value:
        split = temporal_end_value.split('T')
        temporal_end_value = split[0] if len(split) > 1 else temporal_end_value

    if (temporal_start_value is missing or temporal_start_value is None) and (temporal_end_value is missing or temporal_end_value is None):
        flattened_data.pop(key, None)
        raise StopOnError

    try:
        if ((len(temporal_start_value) > 0) != (len(temporal_end_value) > 0)) and (len(flattened_data.get(key)) == 0):
            error = 'This field should not be empty'

        if (len(temporal_start_value) > 0) and (len(temporal_end_value) > 0):
            if dt.strptime(temporal_start_value, '%Y-%m-%d') > dt.strptime(temporal_end_value, '%Y-%m-%d'):
                if key == ('temporal_start',):
                    error = 'Must be earlier than end date.'
                elif key == ('temporal_end',):
                    error = 'Must be later than start date.'

    except Exception as e:
        log.error(str(e), exc_info=True)

    if error:
        raise Invalid(error)


def qdes_dataset_current_date_later_than_creation(key, flattened_data, errors, context):
    """
    Validate current date field against dataset_creation_date/service_creation_date field.

    It will raise an error, when current date value < dataset_creation_date.
    """
    # Get date values.
    creation_date_value = None
    if ('dataset_creation_date',) in flattened_data:
        creation_date_value = flattened_data[('dataset_creation_date',)]
    elif ('service_creation_date',) in flattened_data:
        creation_date_value = flattened_data[('service_creation_date',)]
    current_date_value = flattened_data[key]

    # Need to make sure current date date >= creation date.
    if (creation_date_value is not None) and (current_date_value is not None):
        if len(current_date_value) > 0:
            dt_creation = dt.strptime(creation_date_value, '%Y-%m-%dT%H:%M:%S')
            dt_current_date = dt.strptime(current_date_value, '%Y-%m-%dT%H:%M:%S')

            if dt_current_date < dt_creation:
                raise toolkit.Invalid('Must be later than creation date.')


def qdes_dataset_last_modified_date_before_today(key, flattened_data, errors, context):
    qdes_dataset_current_date_later_than_creation(key, flattened_data, errors, context)

    # Get date values.
    current_date_value = flattened_data[key]
    if current_date_value is not None and len(current_date_value) > 0:
        dt_current = dt.strptime(current_date_value, '%Y-%m-%dT%H:%M:%S')
        if not dt_current <= dt.today():
            raise toolkit.Invalid('Last modified date must be on or earlier than today.')


def qdes_uri_validator(value):
    """
    Validate the uri either it is accessible or not.
    @TODO https://it-partners.atlassian.net/browse/DDCI-122
    This should work for repeatable field as well.

    For now it will return the value.
    """
    return value


def qdes_validate_decimal(value):
    """
    Validate the string provided is float, decimal or integer.
    """
    if len(value) > 0:
        try:
            float(value)
        except:
            raise toolkit.Invalid('Not a valid decimal value.')

    return value


def qdes_validate_decimal_positive(value):
    """
    Validate the string provided is float, decimal or integer and must be positive.
    """
    if len(value) > 0:
        try:
            val = float(value)
        except:
            raise toolkit.Invalid('Not a valid decimal value.')

        if val < 0:
            raise toolkit.Invalid('Value must be positive.')

    return value


def qdes_validate_positive_integer(value, context):
    value = logic.validators.int_validator(value, context)

    if value is not None and value < 1:
        raise Invalid('Must be a positive integer')
    return value


def qdes_validate_geojson(value):
    """
    Validate the format of GeoJSON.
    """
    if len(value) > 0:
        try:
            # Load JSON string to geojson object.
            geojson_obj = geojson.loads(value)
        except:
            raise toolkit.Invalid('GeoJSON is not valid.')

        if (not 'is_valid' in dir(geojson_obj)) or (not geojson_obj.is_valid):
            raise toolkit.Invalid('GeoJSON is not valid.')

    return value


def qdes_validate_geojson_point(value):
    """
    Validate the format of GeoJSON point.
    """
    if len(value) > 0:
        try:
            # Load JSON string to geojson object.
            geojson_obj = geojson.loads(value)
        except:
            raise toolkit.Invalid('Not a valid JSON string.')

        if geojson_obj.__class__.__name__ != 'Point':
            raise toolkit.Invalid('GeoJSON Point is needed.')

    return value


def qdes_validate_geojson_polygon(value):
    """
    Validate the format of GeoJSON point.
    """
    if len(value) > 0:
        try:
            # Load JSON string to geojson object.
            geojson_obj = geojson.loads(value)
        except:
            raise toolkit.Invalid('Not a valid JSON string.')

        if geojson_obj.__class__.__name__ != 'Polygon':
            raise toolkit.Invalid('GeoJSON Polygon is needed.')

    return value


def qdes_spatial_points_pair(key, flattened_data, errors, context):
    """
    Validate lower left and upper right.

    It will raise an error, when:
    - If one of the points is empty.
    """
    spatial_lower_left_value = flattened_data[('spatial_lower_left',)]
    spatial_upper_right_value = flattened_data[('spatial_upper_right',)]

    if ((len(spatial_lower_left_value) > 0) != (len(spatial_upper_right_value) > 0)) and (len(flattened_data.get(key)) == 0):
        raise toolkit.Invalid('This field should not be empty')


def qdes_within_au_bounding_box(value):
    """
    Validate the point is within Australia Bounding Box, only support rectangle.
    """
    if len(value) > 0:
        # Load AU bounding box.
        aubb = config.get('ckanext.qdes_schema.au_bounding_box', False)

        if len(aubb) > 0:
            try:
                # Load JSON string to geojson object.
                geojson_obj = geojson.loads(value)
                aubb_geojson_obj = geojson.loads(aubb)
            except:
                raise toolkit.Invalid('Not a valid JSON string.')

            if (aubb_geojson_obj.__class__.__name__ == 'Polygon') and (geojson_obj.__class__.__name__ == 'Point'):
                point_coord = list(geojson.utils.coords(geojson_obj))[0]
                aubb_coord = list(geojson.utils.coords(aubb_geojson_obj))

                p1 = aubb_coord[0]
                p2 = aubb_coord[2]

                if not ((point_coord[0] > p1[0]) and (point_coord[0] < p2[0]) and (point_coord[1] > p1[1]) and (
                        point_coord[1] < p2[1])):
                    raise toolkit.Invalid('This Point is not within Australia bounding box')

    return value


def qdes_validate_geojson_spatial(key, flattened_data, errors, context):
    """
    Generate box based on the lower left and upper right Points.

    If there is geometry value, use this geometry and
    update the lower left and upper right fields.
    """
    spatial_geometry_value = flattened_data[('spatial_geometry',)]
    if len(spatial_geometry_value) > 0:
        try:
            geometry = geojson.loads(spatial_geometry_value)
            geometry_coord = list(geojson.utils.coords(geometry))
            box = []
            for i in (0, 1):
                res = sorted(geometry_coord, key=lambda x: x[i])
                box.append((res[0][i], res[-1][i]))

            if box:
                point_lower_left_coord = geojson.Point((box[0][0], box[1][0]))
                point_upper_right_coord = geojson.Point((box[0][1], box[1][1]))

                # Assign above coords to respected field.
                flattened_data[('spatial_lower_left',)] = geojson.dumps(point_lower_left_coord)
                flattened_data[('spatial_upper_right',)] = geojson.dumps(point_upper_right_coord)
        except Exception as e:
            log.error(str(e))

    spatial_lower_left_value = flattened_data[('spatial_lower_left',)]
    spatial_upper_right_value = flattened_data[('spatial_upper_right',)]
    spatial_centroid_value = flattened_data[('spatial_centroid',)]

    if (len(spatial_lower_left_value) > 0) and (len(spatial_upper_right_value) > 0):
        # Get coordinates.
        try:
            point_lower_left = geojson.loads(spatial_lower_left_value)
            point_lower_left_coord = list(geojson.utils.coords(point_lower_left))[0]

            point_upper_right = geojson.loads(spatial_upper_right_value)
            point_upper_right_coord = list(geojson.utils.coords(point_upper_right))[0]

            # Create box.
            box = geojson.Polygon([[
                [point_lower_left_coord[0], point_upper_right_coord[1]],
                [point_upper_right_coord[0], point_upper_right_coord[1]],
                [point_upper_right_coord[0], point_lower_left_coord[1]],
                [point_lower_left_coord[0], point_lower_left_coord[1]],
                [point_lower_left_coord[0], point_upper_right_coord[1]],
            ]])

            flattened_data[key] = geojson.dumps(box)
        except Exception as e:
            log.error(str(e))
    elif len(spatial_centroid_value) > 0:
        flattened_data[key] = spatial_centroid_value
    else:
        flattened_data[key] = ''


def qdes_iso_8601_durations(key, flattened_data, errors, context):
    """
    Validate the value against iso 8601 duration.
    """
    has_error = False

    # Validate the positive number of each value.
    try:
        result_period = re.split(
            "(-)?P(?:([-.,\d]+)Y)?(?:([-.,\d]+)M)?(?:([-.,\d]+)W)?(?:([-.,\d]+)D)?",
            flattened_data[key])

        result_time = re.split("T(?:([-.,\d]+)H)?(?:([-.,\d]+)M)?(?:([-.,\d]+)S)?", flattened_data[key])

        result = result_period + result_time

        for index, value in enumerate(result):
            if (index > 1) and (index < 10) and (not index == 6) and (not index == 7):
                try:
                    if (value is None) or len(value) == 0:
                        value = 0

                    float_value = float(value)

                    if float_value < 0:
                        has_error = True
                except:
                    has_error = True
    except Exception as e:
        log.error(str(e), exc_info=True)

    if has_error:
        raise toolkit.Invalid('The value in each field needs to be positive number.')

    # Validate the pattern.
    result_pattern = re.split("^P(?=\d+[YMWD])(\d+Y)?(\d+M)?(\d+W)?(\d+D)?(T(?=\d+[HMS])(\d+H)?(\d+M)?(\d+S)?)?$", flattened_data[key])
    if len(result_pattern) <= 1:
        log.error(f'Invalid result_pattern: {result_pattern}')
        raise toolkit.Invalid('Incorrect ISO 8601 duration format')


@scheming_validator
def qdes_validate_multi_groups(field, schema):
    """
    Validates each multi group has no empty values
    """

    def validator(key, data, errors, context):
        key_data = data.get(key)
        field_groups = field.get('field_group')
        if key_data and field_groups:
            values = toolkit.get_converter('json_or_string')(key_data)
            if values and isinstance(values, list):
                for value in values:
                    for field_group in field_groups:
                        field_value = value.get(field_group.get('field_name', ''))
                        # Check if there are any missing empty values in the group
                        if field_value == None:
                            errors[key].append(toolkit._('{0} field should not be empty'.format(field_group.get('label'))))

    return validator


def qdes_validate_duplicate_replaces_relationships(value, context, package_id, package_title, data):
    """
    Validate replaces relationship, a dataset version can only be replaced by one version.
    Example case: we have v1, v2 and v3,
    v1 is replaced by v2, then v3 should not be able to replace v1.
    Two dataset can't replace the same dataset
    """
    relationship_type = value.get('relationship')
    if relationship_type == 'Is Replaced By' or relationship_type == 'Replaces':
        model = context['model']
        query = model.Session.query(model.PackageRelationship)
        replaced_by_dataset_title = ''
        target_title = ''
        target_id = None

        if relationship_type == 'Replaces':
            # This will happen when editor create/edit v3, and add relationship type 'replaces'.
            # Get the target id, in this example case, v1 information is available on value of the field.
            target_id = value.get('resource', {}).get('id', None)
            target_title = h.get_pkg_title(target_id)
            replaced_by_dataset_title = data.get(('title',), None)

        elif relationship_type == 'Is Replaced By' and package_id:
            # This will happen when editor edit v1, and add relationship type 'Is Replaced By'.
            # Get the target id, in this example case, v1 information is available the current package dict.
            target_id = package_id
            target_title = package_title
            replaced_by_dataset_id = value.get('resource', {}).get('id', None)
            replaced_by_dataset_title = get_action('package_show')(context, {'id': replaced_by_dataset_id}).get('title')

        if target_id:
            # Let's add a query to filter 'replaces' that has object_package_id of the target.
            query = query.filter(model.PackageRelationship.object_package_id == target_id)
            query = query.filter(model.PackageRelationship.type == 'Replaces')

            if package_id:
                # In case where we create a new dataset, new resource screen will be presented,
                # at this stage the package and its relationship is already created,
                # this filter will exclude the current dataset from the query.
                query = query.filter(model.PackageRelationship.subject_package_id != package_id)

            # Run the query.
            relationship = query.first()
            if relationship:
                # Get the dataset that already replaced the target.
                current_dataset_replacement_title = h.get_pkg_title(relationship.subject_package_id)
                current_dataset_replacement_url = h.url_for('dataset.read', id=relationship.subject_package_id)

                # If the v1 already has relationship, then throw an error.
                return 'Dataset {0} cannot replace {1}, because it has already been replaced by <a href="{2}">{3}</a>.'\
                    .format(replaced_by_dataset_title, target_title, current_dataset_replacement_url, current_dataset_replacement_title)

    return False


@scheming_validator
def qdes_validate_related_resources(field, schema):
    """
    Validates each multi group for related_resources
    Must not have empty values in group
    Must be either a valid CKAN dataset name or valid URL to external dataset
    """

    def validator(key, data, errors, context):
        # Don't run this validator when adding or editing a resource
        if toolkit.g and toolkit.g.controller == 'resource':
            return validator

        model = context['model']
        related_resources_data = data.get(key)
        field_groups = field.get('field_group')

        if related_resources_data and field_groups:
            values = toolkit.get_converter('json_or_string')(related_resources_data)
            if values and isinstance(values, list):
                field_group_errors = []
                field_group_error = {}
                for value in values:
                    for field_group in field_groups:
                        field_name = field_group.get('field_name')
                        field_value = value.get(field_group.get('field_name', ''))

                        if field_name == 'resource' and field_value:
                            val = field_value.get('id', None) or None
                            if not val:
                                field_value = val

                        # Check if there are any missing empty values in the group
                        if field_value is None:
                            field_group_error[field_name] = [toolkit._('{0} field should not be empty'.format(field_group.get('label')))]
                        elif field_name == 'resource':
                            # Check if dataset name exists or is a valid URL
                            try:
                                qdes_validate_related_dataset([field_value], context)
                            except toolkit.Invalid as e:
                                field_group_error[field_name] = [toolkit._(e.error)]

                    # Validates the dataset relationship to prevent circular references
                    # If there is no package_id it must be a new dataset so there will not be any previous relationships
                    package_id = data.get(('id',), None)
                    package_title = data.get(('title',), None)
                    related_dataset = toolkit.get_converter('json_or_string')(value)
                    dataset_id = related_dataset.get('resource', {}).get('id', None)
                    relationship_type = related_dataset.get('relationship', None)
                    if package_id and related_dataset and isinstance(related_dataset, dict):
                        try:
                            qdes_validate_circular_replaces_relationships(package_id, dataset_id, relationship_type, context)
                        except toolkit.Invalid as e:
                            if field_group_error.get('group', None) or None is None:
                                field_group_error['group'] = []

                            field_group_error['group'].append(toolkit._(e.error))

                    # Only forward relationship accepted.
                    try:
                        if related_dataset and isinstance(related_dataset, dict) and not relationship_type in model.PackageRelationship.get_forward_types():
                            raise toolkit.Invalid(toolkit._('Only forward relationship is accepted'))
                    except toolkit.Invalid as e:
                        if field_group_error.get('group', None) or None is None:
                            field_group_error['group'] = []

                        field_group_error['group'].append(toolkit._(e.error))

                    duplicate_replaces_relationships = qdes_validate_duplicate_replaces_relationships(value, context, package_id, package_title, data)
                    if duplicate_replaces_relationships:
                        if field_group_error.get('group', None) or None is None:
                            field_group_error['group'] = []
                        field_group_error['group'].append(toolkit._(duplicate_replaces_relationships))

                    if field_group_error:
                        field_group_errors.append(field_group_error)
                        field_group_error = {}
                    else:
                        field_group_errors.append({})

                # Only the first array is displayed at top of the screen,
                # so let's combine them.
                error_for_display = []
                for field_group_error in field_group_errors:
                    for err_key, value in field_group_error.items():
                        error_for_display.append(', '.join(value))

                if error_for_display:
                    # Multiple errors doesn't seems make sense and hard to read.
                    if len(error_for_display) > 1:
                        errors[key].append(toolkit._('Multiple errors occurred, please see the form for details.'))
                    else:
                        errors[key].append(', '.join(error_for_display))

                if field_group_errors and error_for_display:
                    errors[key].append({'field_groups': field_group_errors})

    return validator


def qdes_validate_related_dataset(value, context):
    """
    Validates each dataset name exists in CKAN or is a valid URL to external dataset
    """
    datasets = toolkit.get_converter('json_or_string')(value)
    if datasets and isinstance(datasets, list):
        for dataset in datasets:
            dataset_id = dataset.get('id', '')
            try:
                toolkit.get_validator('package_id_exists')(dataset_id, context)
            except toolkit.Invalid:
                # Package does not exists so lets check to see if there is a valid URI entereds
                data = {'url': dataset_id}
                errors = {'url': []}
                toolkit.get_validator('url_validator')('url', data, errors, context)
                if (len(errors['url']) > 0):
                    raise toolkit.Invalid(errors['url'][0])

                if not toolkit.get_validator('qdes_uri_validator')(dataset_id):
                    raise toolkit.Invalid('Unsuccessful connecting to URI {}'.format(dataset_id))

    return value


def qdes_validate_metadata_review_date(key, flattened_data, errors, context):
    """
    Set metadata_review_date value.
    """
    try:
        extras = flattened_data.get(('__extras',), {}) or None
        metadata_review_date_reviewed = extras.get('metadata_review_date_reviewed', None) if extras else None
        type = flattened_data.get(('type',))
        value = flattened_data.get(key)

        if (type in ['dataset', 'dataservice']) and (metadata_review_date_reviewed or value is missing or value is None or len(value) == 0):
            # If empty OR checkbox ticked.
            flattened_data[key] = dt.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    except Exception as e:
        log.error(str(e), exc_info=True)


def qdes_validate_circular_replaces_relationships(current_dataset_id, relationship_dataset_id, relationship_type, context):
    """
    Validates the dataset relationship to prevent circular references
    """
    # Check the value of relationship_dataset_id first
    # in case it is a URI - if it is, exit early
    data = {'url': relationship_dataset_id}
    errors = {'url': []}
    toolkit.get_validator('url_validator')('url', data, errors, context)
    if len(errors['url']) == 0:
        # If there are no errors it must be a valid URL so exit early
        return True

    try:
        relationship_dataset = toolkit.get_action('package_show')(context, {"id": relationship_dataset_id})
        relationship_dataset_title = relationship_dataset.get('title', None)
    except toolkit.ObjectNotFound:
        # Package does not exists so it must be a valid URI from external dataset
        return True

    if relationship_type in ['Replaces']:
        # This is to prevent circular replace relationships
        # Eg. If we are creating a relationship for DatasetA to replace DatasetC
        # We need to check if there is a relationship where DatasetC replaces DatasetB and DatasetB replaces DatasetA
        #
        model = context['model']
        dataset_chain = [relationship_dataset_id]
        # Lets go down the chain and see if DatasetC replaces any datasets
        for dataset_id in dataset_chain:
            query = model.Session.query(model.PackageRelationship)
            query = query.filter(model.PackageRelationship.subject_package_id == dataset_id)
            query = query.filter(model.PackageRelationship.type == relationship_type)
            relationship = query.first()
            if relationship:
                # Dataset replace relationship found eg. DatasetC replaces DatasetB or DatasetC replaces DatasetA or DatasetB replaces DatasetA
                if relationship.object_package_id == current_dataset_id:
                    # Dataset replaces current dataset eg. DatasetC replaces DatasetA or Dataset B replaces DatasetA
                    # This is a circular reference!!!
                    # Create message showing circular reference
                    current_dataset = get_action('package_show')(context, {'id': current_dataset_id})
                    current_dataset_url = h.url_for('dataset.read', id=current_dataset.get('name'))
                    current_dataset_title = current_dataset.get('title', None)
                    circular_references = [f'<a href="{current_dataset_url}">{current_dataset_title}</a>']

                    for dataset_id in dataset_chain:
                        subject_package = get_action('package_show')(context, {'id': dataset_id})
                        subject_package_url = h.url_for('dataset.read', id=subject_package.get('name'))
                        circular_references.append(f'<a href="{subject_package_url}">{subject_package.get("title", None)}</a>')

                    circular_references.append(f'<a href="{current_dataset_url}">{current_dataset_title}</a>')
                    circular_references_str = ' <i class="fa fa-long-arrow-right"></i> '.join(circular_references)

                    raise toolkit.Invalid(
                        f'{current_dataset_title} cannot replace {relationship_dataset_title}, '
                        f'because this will create a circular relationship {circular_references_str}')
                else:
                    # Move down the chain and check if this dataset replaces another dataset eg. Does DatasetB or DatasetA have a replace relationship
                    dataset_chain.append(relationship.object_package_id)

    return True


def qdes_validate_point_of_contact(value, context):
    """
    Validates whether position id is in secure vocab or not.
    """
    point_of_contact = qdes_report_helpers.get_point_of_contact(context, value)
    if not point_of_contact:
        raise toolkit.Invalid('Position ID is not found in secure vocabulary.')

    return value


@scheming_validator
def qdes_validate_multi_scheming_choices(field, schema):
    """
    Validates value against its choice_helper result.
    """
    scheming_choices_validator = scheming_choices(field, schema)

    def validator(value, context):
        values = toolkit.get_converter('json_or_string')(value)
        if values and isinstance(values, list):
            for val in values:
                scheming_choices_validator(val)

            return value

        raise toolkit.Invalid('Invalid JSON.')

    return validator


@scheming_validator
def qdes_validate_multi_pair_vocab_vocab(field, schema):
    """
    Validates the field group against its choice_helper result.
    """
    def validator(value, context):
        values = toolkit.get_converter('json_or_string')(value)
        if values and isinstance(values, list):
            for val in values:
                field_group = field.get('field_group', [])
                for item in field_group:
                    if 'choices_helper' in item:
                        scheming_choices_validator = scheming_choices(item, schema)
                        if item.get('field_name', None) is not None and len(val[item.get('field_name')]) > 0:
                            scheming_choices_validator(val[item.get('field_name')])

            return value

        raise toolkit.Invalid('Invalid JSON.')

    return validator


@scheming_validator
def qdes_validate_multi_pair_vocab_free_text(field, schema):
    return qdes_validate_multi_pair_vocab_vocab(field, schema)


def qdes_validate_data_service_is_exist(value, context):
    """
    Validates if the given package IDs are exist.
    """
    values = toolkit.get_converter('json_or_string')(value)
    if values and isinstance(values, list):
        for val in values:
            model = context['model']
            cls = model.Package
            data = model.Package().Session.query(cls).filter(cls.type == 'dataservice').filter(cls.id == val).all()
            if not data:
                raise toolkit.Invalid('Data service is not found.')

        return value

    raise toolkit.Invalid('Invalid JSON.')

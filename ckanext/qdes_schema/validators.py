import ckan.plugins.toolkit as toolkit
import geojson
import json
import logging

from datetime import datetime as dt
from ckan.common import config
from ckanext.scheming.validation import scheming_validator

log = logging.getLogger(__name__)


def qdes_temporal_start_end_date(key, flattened_data, errors, context):
    """
    Validate the start and date.

    It will raise an error, when:
    - If the either start or end date is empty.
    - If the start date < end date.
    """
    temporal_start_value = flattened_data[('temporal_start',)]
    temporal_end_value = flattened_data[('temporal_end',)]

    if ((len(temporal_start_value) > 0) != (len(temporal_end_value) > 0)) and (len(flattened_data.get(key)) == 0):
        raise toolkit.Invalid("This field should not be empty")

    if (len(temporal_start_value) > 0) and (len(temporal_end_value) > 0):
        if dt.strptime(temporal_start_value, '%Y-%m-%d') > dt.strptime(temporal_end_value, '%Y-%m-%d'):
            if key == ('temporal_start',):
                raise toolkit.Invalid('Must be earlier than end date.')
            elif key == ('temporal_end',):
                raise toolkit.Invalid('Must be later than start date.')


def qdes_dataset_creation_date(value):
    """
    Return current datetime in UTC when value is empty.
    """
    if value is None:
        return dt.utcnow().strftime('%Y-%m-%dT%H:%M:%S')

    return value


def qdes_dataset_current_date_later_than_creation(key, flattened_data, errors, context):
    """
    Validate current date field against dataset_creation_date field.

    It will raise an error, when current date value < dataset_creation_date.
    """
    # Get date values.
    dataset_creation_date_value = flattened_data[('dataset_creation_date',)]
    current_date_value = flattened_data[key]

    # Need to make sure current date date >= creation date.
    if (dataset_creation_date_value is not None) and (current_date_value is not None):
        if len(current_date_value) > 0:
            dt_creation = dt.strptime(dataset_creation_date_value, '%Y-%m-%dT%H:%M:%S')
            dt_release = dt.strptime(current_date_value, '%Y-%m-%dT%H:%M:%S')

            if dt_release < dt_creation:
                raise toolkit.Invalid('Must be later than creation date.')


def qdes_uri_validator(value):
    """
    Validate the uri either it is accessible or not.
    @TODO https://it-partners.atlassian.net/browse/DDCI-122

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


def qdes_validate_geojson(value):
    """
    Validate the format of GeoJSON.
    """
    if len(value) > 0:
        try:
            # Load JSON string to geojson object.
            geojson_obj = geojson.loads(value)

            if (not 'is_valid' in dir(geojson_obj)) or (not geojson_obj.is_valid):
                raise toolkit.Invalid('GeoJSON is not valid.')
        except:
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

            if geojson_obj.__class__.__name__ != 'Point':
                raise toolkit.Invalid('GeoJSON Point is needed.')
        except:
            raise toolkit.Invalid('Not a valid JSON string.')

    return value


def qdes_validate_geojson_polygon(value):
    """
    Validate the format of GeoJSON point.
    """
    if len(value) > 0:
        try:
            # Load JSON string to geojson object.
            geojson_obj = geojson.loads(value)

            if geojson_obj.__class__.__name__ != 'Polygon':
                raise toolkit.Invalid('GeoJSON Polygon is needed.')
        except:
            raise toolkit.Invalid('Not a valid JSON string.')

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
            # Load JSON string to geojson object.
            geojson_obj = geojson.loads(value)
            aubb_geojson_obj = geojson.loads(aubb)

            if (aubb_geojson_obj.__class__.__name__ == 'Polygon') and (geojson_obj.__class__.__name__ == 'Point'):
                point_coord = list(geojson.utils.coords(geojson_obj))[0]
                aubb_coord = list(geojson.utils.coords(aubb_geojson_obj))

                p1 = aubb_coord[0]
                p2 = aubb_coord[2]

                if not ((point_coord[0] > p1[0]) and (point_coord[0] < p2[0]) and (point_coord[1] > p1[1]) and (point_coord[1] < p2[1])):
                    raise toolkit.Invalid('This Point is not within Australia bounding box')

    return value


def qdes_validate_geojson_spatial(key, flattened_data, errors, context):
    """
    Generate box based on the lower left and upper right Points.
    """
    try:
        spatial_lower_left_value = flattened_data[('spatial_lower_left',)]
        spatial_upper_right_value = flattened_data[('spatial_upper_right',)]

        if (len(spatial_lower_left_value) > 0) and (len(spatial_upper_right_value) > 0):
            # Get coordinates.
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
    finally:
        pass


@scheming_validator
def qdes_validate_multi_groups(field, schema):
    """
    Validates each multi group has no empty values
    """

    def validator(key, data, errors, context):
        key_data = data.get(key)
        field_groups = field.get('field_group')
        if key_data and field_groups:
            values = toolkit.h.get_multi_textarea_values(key_data)
            for field_group in field_groups:
                group_values = values.get(field_group.get('field_name', ''), [])
                # Check if there are any missing empty values in the group
                if any(values for value in group_values if value == None or value.strip() == ''):
                    errors[key].append(toolkit._('{0} field should not be empty'.format(field_group.get('label'))))

    return validator

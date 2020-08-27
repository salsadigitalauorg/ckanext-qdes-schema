import ckan.plugins.toolkit as toolkit
from datetime import datetime as dt

def qdes_temporal_start_end_date(key, flattened_data, errors, context):
    """
    Validate the start and date.

    It will raise an error, when:
    - If the either start or end date is not empty.
    - If the start date < end date.
    """
    temporal_start_value = flattened_data[('temporal_start',)]
    temporal_end_value = flattened_data[('temporal_end',)]

    if ((len(temporal_start_value) > 0) != (len(temporal_end_value) > 0)) and (len(flattened_data.get(key)) == 0):
        raise toolkit.Invalid("This field should not be empty")

    if (len(temporal_start_value) > 0) and (len(temporal_end_value) > 0):
        if dt.strptime(temporal_start_value, '%Y-%m-%d') > dt.strptime(temporal_end_value, '%Y-%m-%d'):
            if key == ('temporal_start',):
                raise toolkit.Invalid("Must be earlier than end date.")
            elif key == ('temporal_end',):
                raise toolkit.Invalid("Must be later than start date.")

def qdes_dataset_creation_date(value):
    """
    Return current datetime in UTC when value is empty.
    """
    if value is None:
        return dt.utcnow().strftime('%Y-%m-%dT%H:%M')

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
                raise toolkit.Invalid("Must be later than creation date.")

def qdes_uri_validator(value):
    """
    Validate the uri either it is accessible or not.
    @TODO https://it-partners.atlassian.net/browse/DDCI-122

    For now it will return the value.
    """
    return value

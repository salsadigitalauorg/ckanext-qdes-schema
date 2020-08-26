import ckan.plugins.toolkit as toolkit
from datetime import datetime as dt

def qdes_temporal_start_end_date(key, flattened_data, errors, context):
    temporal_start_value = flattened_data[('temporal_start',)]
    temporal_end_value = flattened_data[('temporal_end',)]

    if ((len(temporal_start_value) > 0) != (len(temporal_end_value) > 0)) and (len(flattened_data.get(key)) == 0):
        raise toolkit.Invalid("This field should not be empty")


    if dt.strptime(temporal_start_value, '%Y-%m-%d') > dt.strptime(temporal_end_value, '%Y-%m-%d'):
        if key == ('temporal_start',):
            raise toolkit.Invalid("Start date must be less then end date.")
        elif key == ('temporal_end',):
            raise toolkit.Invalid("End date must be higher then start date.")

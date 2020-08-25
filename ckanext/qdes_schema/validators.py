import ckan.plugins.toolkit as toolkit


def qdes_temporal_start_end_date(field, schema):
    if len(field) > 300:
        raise toolkit.Invalid("Max chars should be 3 characters")
    return field

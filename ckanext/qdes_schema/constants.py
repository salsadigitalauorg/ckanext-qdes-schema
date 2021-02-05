PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA = 'dataqld_dataset'
PUBLISH_EXTERNAL_IDENTIFIER_QSPATIAL_SCHEMA = 'qspatial_dataset'
PUBLISH_EXTERNAL_IDENTIFIER_SIR_SCHEMA = 'sir_dataset'
PUBLISH_TRIGGER_MANUAL = 'manual'
PUBLISH_TRIGGER_AUTOMATED = 'automated'
PUBLISH_STATUS_PENDING = 'pending'
PUBLISH_STATUS_SUCCESS = 'success'
PUBLISH_STATUS_FAILED = 'failed'

def get_key_name(schema):
    if schema == PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA:
        return 'DATA_QLD_API_KEY'
    elif schema == PUBLISH_EXTERNAL_IDENTIFIER_QSPATIAL_SCHEMA:
        return 'QSPATIAL_API_KEY'
    elif schema == PUBLISH_EXTERNAL_IDENTIFIER_SIR_SCHEMA:
        return 'SIR_API_KEY'

    return ''

def get_external_schema_url(schema):
    if schema == PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA:
        return 'DATA_QLD_URL'
    elif schema == PUBLISH_EXTERNAL_IDENTIFIER_QSPATIAL_SCHEMA:
        return 'QSPATIAL_URL'
    elif schema == PUBLISH_EXTERNAL_IDENTIFIER_SIR_SCHEMA:
        return 'SIR_URL'

    return ''

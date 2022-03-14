PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA = 'dataqld_dataset'
PUBLISH_EXTERNAL_IDENTIFIER_QSPATIAL_SCHEMA = 'qspatial_dataset'
PUBLISH_EXTERNAL_IDENTIFIER_SIR_SCHEMA = 'sir_dataset'
PUBLISH_TRIGGER_MANUAL = 'manual'
PUBLISH_TRIGGER_AUTOMATED = 'automated'
PUBLISH_STATUS_PENDING = 'pending'
PUBLISH_STATUS_SUCCESS = 'success'
PUBLISH_STATUS_FAILED = 'failed'
PUBLISH_STATUS_VALIDATION_ERROR = 'validation_error'
PUBLISH_STATUS_VALIDATION_SUCCESS = 'validation_success'
PUBLISH_ACTION_CREATE = 'create'
PUBLISH_ACTION_UPDATE = 'update'
PUBLISH_ACTION_DELETE = 'delete'
PUBLISH_LOG_PENDING = 'Pending'
PUBLISH_LOG_PUBLISHED = 'Published'
PUBLISH_LOG_UNPUBLISHED = 'Unpublished'
PUBLISH_LOG_UNPUBLISH_ERROR = 'Unpublish error'
PUBLISH_LOG_PUBLISH_ERROR = 'Publish error'
PUBLISH_LOG_VALIDATION_ERROR = 'Validation error'
PUBLISH_LOG_NEED_REPUBLISH = 'Needs republishing'

def get_key_name(schema):
    if schema == PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA:
        return 'DATA_QLD_API_KEY'
    elif schema == PUBLISH_EXTERNAL_IDENTIFIER_QSPATIAL_SCHEMA:
        return 'QSPATIAL_API_KEY'
    elif schema == PUBLISH_EXTERNAL_IDENTIFIER_SIR_SCHEMA:
        return 'SIR_API_KEY'

    return ''


def get_owner_org(schema):
    if schema == PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA:
        return 'DATA_QLD_OWNER_ORG'
    elif schema == PUBLISH_EXTERNAL_IDENTIFIER_QSPATIAL_SCHEMA:
        return 'QSPATIAL_OWNER_ORG'
    elif schema == PUBLISH_EXTERNAL_IDENTIFIER_SIR_SCHEMA:
        return 'SIR_OWNER_ORG'

    return ''


def get_external_schema_url(schema):
    if schema == PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA:
        return 'DATA_QLD_URL'
    elif schema == PUBLISH_EXTERNAL_IDENTIFIER_QSPATIAL_SCHEMA:
        return 'QSPATIAL_URL'
    elif schema == PUBLISH_EXTERNAL_IDENTIFIER_SIR_SCHEMA:
        return 'SIR_URL'

    return ''


def get_dataservice_id(schema):
    if schema == PUBLISH_EXTERNAL_IDENTIFIER_DATA_QLD_SCHEMA:
        return 'ckanext.qdes_schema.publishing_portals.opendata'
    elif schema == PUBLISH_EXTERNAL_IDENTIFIER_QSPATIAL_SCHEMA:
        return 'ckanext.qdes_schema.publishing_portals.qspatial'
    elif schema == PUBLISH_EXTERNAL_IDENTIFIER_SIR_SCHEMA:
        return 'ckanext.qdes_schema.publishing_portals.sir'

    return ''

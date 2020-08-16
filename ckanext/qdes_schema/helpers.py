from ckan.plugins.toolkit import h


def is_legacy_ckan():
    return False if h.ckan_version() > '2.9' else True

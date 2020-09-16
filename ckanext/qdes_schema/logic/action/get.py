import logging
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.authz as authz
import ckan.lib.plugins as lib_plugins
import ckan.lib.search as search

log = logging.getLogger(__name__)
_check_access = toolkit.check_access


def dataservice(context, name):
    """
    Returns all dataservice where private is false.
    """
    data = []
    model = context['model']
    try:
        cls = model.Package
        data = model.Package().Session.query(cls).filter(cls.type == 'dataservice').filter(cls.private == 'f').all()
    except Exception as e:
        log.error(str(e))

    return data


@toolkit.chained_action
def package_autocomplete(original_action, context, data_dict):
    '''Return a list of datasets (packages) that match a string.

    Datasets with names or titles that contain the query string will be
    returned.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of resource formats to return (optional,
        default: ``10``)
    :type limit: int

    :rtype: list of dictionaries

    '''
    # Override of package_autocomplete
    # The only change is to only search on public datasets and ignore private datasets
    model = context.get('model')

    _check_access('package_autocomplete', context, data_dict)
    user = context.get('user')

    limit = data_dict.get('limit', 10)
    q = data_dict['q']

    data_dict = {
        'q': ' OR '.join([
            'name_ngram:{0}',
            'title_ngram:{0}',
            'name:{0}',
            'title:{0}',
        ]).format(search.query.solr_literal(q)),
        'fl': 'id,name,title',
        'fq': 'capacity:public',  # QDes Override: Only search on public datasets
        'rows': limit
    }
    query = search.query_for(model.Package)

    results = query.run(data_dict)['results']

    q_lower = q.lower()
    pkg_list = []
    for package in results:
        if q_lower in package['name']:
            match_field = 'name'
            match_displayed = package['name']
        else:
            match_field = 'title'
            match_displayed = '%s (%s)' % (package['title'], package['name'])
        result_dict = {
            'id': package['id'],
            'name': package['name'],
            'title': package['title'],
            'match_field': match_field,
            'match_displayed': match_displayed}
        pkg_list.append(result_dict)

    return pkg_list

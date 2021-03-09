import logging
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.authz as authz
import ckan.lib.plugins as lib_plugins
import ckan.lib.search as search
import psycopg2

from ckan.plugins.toolkit import get_action
from ckanext.relationships import constants
from pprint import pformat

log = logging.getLogger(__name__)
_check_access = toolkit.check_access
h = toolkit.h


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
    # QDes Override
    dataset_id = toolkit.request.args.get('dataset_id', None)
    id_query = ' AND NOT id:{} '.format(dataset_id) if dataset_id else ''
    dataset_type = toolkit.request.args.get('dataset_type', None)
    type_query = ' AND type:{} '.format(dataset_type) if dataset_type else ''

    data_dict = {
        'q': ' OR '.join([
            'name_ngram:{0}',
            'title_ngram:{0}',
            'name:{0}',
            'title:{0}'
        ]).format(search.query.solr_literal(q)),
        'fl': 'id,name,title',
        # QDes Override: Only search on public datasets, not its own dataset_id and filter by dataset_type
        'fq': 'capacity:public{id_query}{type_query}'.format(id_query=id_query, type_query=type_query),
        'rows': limit
    }
    log.debug('package_autocomplete data_dict:{0}'.format(data_dict))

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


def build_versions(tree):
    versions = []
    for version in tree:
        try:
            package_dict = get_action('package_show')({}, {'id': version.get('object')})
            versions.append(package_dict)
        except Exception as e:
            log.error(str(e))

    return versions


def all_successor_versions(context, id):
    """
    Load all the successor versions from provided dataset.
    """
    def load_successor_versions(data, id):
        """
        Recursively load the successor dataset.
        """
        try:
            # Load the relationship.
            relationships = get_action('package_relationships_list')(context, {'id': id})
        except Exception as e:
            log.error(str(e))
            return []

        # Load successor, this can be multiple items, let's use the index 0.
        successor_version = list(item for item in relationships if item.get('type') == 'Is Replaced By')
        if successor_version:
            return load_successor_versions([successor_version[0]] + data, successor_version[0].get('object'))
        else:
            return data

    successors = load_successor_versions([], id)

    return build_versions(successors)


def all_predecessor_versions(context, id):
    """
    Load all the predecessor versions from provided dataset.
    """
    def load_predecessor_versions(data, id):
        """
        Recursively load the predecessor dataset.
        """
        try:
            # Load the relationship.
            relationships = get_action('package_relationships_list')(context, {'id': id})
        except Exception as e:
            log.error(str(e))
            return []

        # Load predecessor, this can be multiple items, let's use the index 0.
        predecessor_version = list(item for item in relationships if item.get('type') == 'Replaces')
        if predecessor_version:
            return load_predecessor_versions(data + [predecessor_version[0]], predecessor_version[0].get('object'))
        else:
            return data

    predecessors = load_predecessor_versions([], id)

    return build_versions(predecessors)


def all_relationships(context, id):
    """
    Return all relationships with correct order and its nature.
    """
    def get_connection():
        from ckan.model import parse_db_config

        db_config = parse_db_config()

        try:
            return psycopg2.connect(
                user=db_config.get('db_user', None),
                password=db_config.get('db_pass', None),
                host=db_config.get('db_host', None),
                port=db_config.get('db_port', "5432") or "5432",
                database=db_config.get('db_name', None),
            )
        except (Exception, psycopg2.Error) as e:
            log.error(str(e))

    connection = None
    cursor = None
    result = []

    # Build query.
    """
        Example query as below:
        select 
            case 
                when pr.subject_package_id != <provided_pkg_id>
                    then 
                        case
                            when pr.type = 'hasPart' then 'isPartOf'
                            when pr.type = 'isPartOf' then 'hasPart'
                            when pr.type = 'isFormatOf' then 'hasFormat'
                            when pr.type = 'hasFormat' then 'isFormatOf'
                            when pr.type = 'isVersionOf' then 'hasVersion'
                            when pr.type = 'replaces' then 'isReplacedBy'
                            when pr.type = 'isReplacedBy' then 'replaces'
                            when pr.type = 'references' then 'isReferencedBy'
                            when pr.type = 'isReferencedBy' then 'references'
                            when pr.type = 'requires' then 'isRequiredBy'
                            when pr.type = 'isRequiredBy' then 'requires'
                        end
                    else pr.type 
            end "type",
            pr.comment,
            pr.state,
            pkg.id,
            pkg.title,
            pe."value" as dataset_creation_date

        from 
            package_relationship pr

        left join package pkg 
            on 
                case
                    when pr.subject_package_id != <provided_pkg_id>
                        then pkg.id = pr.subject_package_id
                        else pkg.id = pr.object_package_id
                end

        left join package_extra as pe
            on pe.package_id = pkg.id
            and pe."key" = 'dataset_creation_date'

        where
            pr.subject_package_id = <provided_pkg_id>
            or
            pr.object_package_id =  <provided_pkg_id>

        order by
            "type" asc,
            dataset_creation_date desc
    """
    query_type_case = ''
    for relationship in constants.RELATIONSHIP_TYPES:
        query_type_case += """WHEN pr.type = '""" + relationship[0] + """' THEN '""" + relationship[1] + """' """

    query_select_type = """
        CASE 
            WHEN pr.subject_package_id != '{0}'
                THEN case {1} end
                ELSE pr.type
        END "type"
    """
    query_select_type = query_select_type.format(id, query_type_case)

    query_select = """SELECT {0}, pr.comment, pr.state, pkg.id, pkg.title, pe."value" AS dataset_creation_date, pkg.state
        FROM package_relationship pr

        LEFT JOIN package pkg 
            ON 
                CASE
                    WHEN pr.subject_package_id != '{1}'
                        THEN pkg.id = pr.subject_package_id
                        ELSE pkg.id = pr.object_package_id
                END
        
        LEFT JOIN package_extra as pe
            ON pe.package_id = pkg.id AND pe."key" = 'dataset_creation_date'
        
        WHERE
            pr.subject_package_id = '{1}' OR pr.object_package_id =  '{1}'
        
        ORDER BY "type" ASC, dataset_creation_date ASC;
        """
    query_select = query_select.format(query_select_type, id)

    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(query_select)
        rows = cursor.fetchall()
        for row in rows:
            pkg_title = h.get_pkg_title(row[3])
            result.append({
                'type': row[0] or None,
                'comment': row[1] or None,
                'state': row[2] or None,
                'pkg_id': row[3] or None,
                'pkg_title': pkg_title,
                'dataset_creation_date': row[5] or None,
                'pkg_state': row[6] or None,
            })
    except (Exception, psycopg2.Error) as e:
        log.error(str(e))
    finally:
        # Closing database connection.
        if connection:
            cursor.close()
            connection.close()

    return result

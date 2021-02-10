import urllib as urllib


def get_mapped_update_frequency(update_frequency):
    # Map Update frequency, we can't use get_vocab_value because some of the values are custom (can't be matched 1:1).
    # The below frequency value to filter based on this value, use below
    # https://www.data.qld.gov.au/organization/a3cdcdcb-201c-4360-9fa6-98e361c89279?update_frequency=not-updated.
    # @todo: fix this, we maybe need to reuse helper.py:map_update_schedule(),
    # but then need to figure out how to map the non-regular, not-updated, fortnightly and non-regular,
    # currently they are mapped to multiple same URIs in DES, check DDCI-149.
    frequency_map = {
        'near-real-time': 'http://publications.europa.eu/resource/authority/continual',
        'hourly': '',
        'daily': 'http://publications.europa.eu/resource/authority/daily',
        'weekly': 'http://publications.europa.eu/resource/authority/weekly',
        'fortnightly': 'http://publications.europa.eu/resource/authority/fortnightly',
        'monthly': 'http://publications.europa.eu/resource/authority/monthly',
        'quarterly': 'http://publications.europa.eu/resource/authority/quarterly',
        'half-yearly': 'http://publications.europa.eu/resource/authority/biannually',
        'annually': 'http://publications.europa.eu/resource/authority/annually',
        'non-regular': 'http://publications.europa.eu/resource/authority/irregular',
        'not-updated': 'http://publications.europa.eu/resource/authority/notPlanned'
    }
    return frequency_map.get(update_frequency, '')


def get_secure_vocabulary_record(destination, query, vocabulary_name, debug=False):
    try:
        data_dict = {
            'query': query,
            'vocabulary_name': vocabulary_name
        }
        result = destination.action.get_secure_vocabulary_search(**data_dict)

        # If action fails it will return something like this {'success': False, 'msg': 'Not authorised'}, instead of a list of results.
        if result and 'success' in result and result.get('success') == False:
            print(result.get('msg'))
        # Only return the first result, as presumably the data in the CSV file will be a unique name
        if result and isinstance(result, list) and len(result) >= 1:
            return result[0].get('value', None)

        if debug:
            print('>>>')
            print('No secure vocabulary record found: {0} for query: {1}'.format(vocabulary_name, query))
            print('>>>')
    except Exception as e:
        print(str(e))


def get_vocabulary_service_term(destination, term_label, vocabulary_service_name, debug=False):
    try:
        data_dict = {
            'vocabulary_service_name': vocabulary_service_name,
            'term_label': term_label
        }
        result = destination.action.get_vocabulary_service_term(**data_dict)

        # Only return the first result, as presumably the data in the CSV file will be a unique name
        if result and isinstance(result, dict):
            return result.get('uri', None)

        if debug:
            print('>>>')
            print('No term found in vocabulary_service: {0} for term_label_or_uri: {1}'.format(vocabulary_service_name, term_label))
            print('>>>')
    except Exception as e:
        print(str(e))


def fix_url(url):
    parsed_url = urllib.parse.urlparse(url)

    if parsed_url.query:
        parsed_query_params = urllib.parse.parse_qs(parsed_url.query)
        query = urllib.parse.urlencode(parsed_query_params, doseq=True)

        return urllib.parse.urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            query,
            parsed_url.fragment,
        ))

    return url


def convert_size_to_bytes(size_str):
    """
    Convert human file-sizes to bytes.
    """
    multipliers = {
        'kib': 1024,
        'mib': 1024 ** 2,
        'gib': 1024 ** 3,
    }

    # Some Nones observed during migration
    if not size_str:
        return 0

    # Some Int values observed for size
    if isinstance(size_str, int):
        return size_str

    try:
        for suffix in multipliers:
            size_str = size_str.replace(',', '')
            size_str = size_str.lower().strip().strip('s')
            if size_str.lower().endswith(suffix):
                return int(float(size_str[0:-len(suffix)]) * multipliers[suffix])
        else:
            if size_str.endswith('b'):
                size_str = size_str[0:-1]
            elif size_str.endswith('byte'):
                size_str = size_str[0:-4]
        return int(size_str)
    except Exception as e:
        print('Exception raised in convert_size_to_bytes')
        print(f'>>> Input: {size_str}')
        print('Exception: {}'.format(str(e)))
        raise e

def get_mapped_format(format):
    format_map = {
        'xml': 'http://publications.europa.eu/resource/authority/file-type/XML',
        'csv': 'http://publications.europa.eu/resource/authority/file-type/CSV',
        'csv validation schema': 'http://publications.europa.eu/resource/authority/file-type/CSV',
        'txt': 'http://publications.europa.eu/resource/authority/file-type/TXT',
        'json': 'http://publications.europa.eu/resource/authority/file-type/JSON',
        'pdf': 'http://publications.europa.eu/resource/authority/file-type/PDF',
        'xls': 'http://publications.europa.eu/resource/authority/file-type/XLSX', #XLS
        'xlsx': 'http://publications.europa.eu/resource/authority/file-type/XLSX',
        'docx': 'http://publications.europa.eu/resource/authority/file-type/DOCX',
        'kmz': 'http://publications.europa.eu/resource/authority/file-type/KMZ',
        'kml': 'http://publications.europa.eu/resource/authority/file-type/KML',
        'shp': 'http://publications.europa.eu/resource/authority/file-type/SHP',
        'geotiff': 'http://publications.europa.eu/resource/authority/file-type/TIFF', #geotiff
        'tif': 'http://publications.europa.eu/resource/authority/file-type/TIFF',
        'rest': 'http://publications.europa.eu/resource/authority/file-type/REST',
        'geojson': 'http://publications.europa.eu/resource/authority/file-type/GEOJSON',
        'html': 'http://publications.europa.eu/resource/authority/file-type/HTML_SIMPL',
        'spatial data format': 'http://publications.europa.eu/resource/authority/file-type/GDB',
        'shp, tab, fgdb, kmz, gpkg': 'http://publications.europa.eu/resource/authority/file-type/GDB'
    }
    # ZIP needs to be handled manually
    return format_map.get(format.lower(), '')


	

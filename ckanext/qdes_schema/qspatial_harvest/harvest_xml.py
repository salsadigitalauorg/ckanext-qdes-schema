import requests
import json

from qspatial_object import QSpatialObject
from pprint import pformat

def gather_remote_packages(remote_url):
    """
    Gather all packages from QSpatial.

    @TODO, need to loop to all pages, currently only 1 page.
    """
    packages = []
    try:
        print('>>> Gathering remote packages')
        response = requests.get(remote_url)

        if response.status_code == 200:
            result = response.json()
            packages = result['response']['docs'] or []
    except Exception as e:
        print(str(e))

    return packages

def fetch_and_save_xml(package):
    print('>>> Fetching an xml file for id: %s' % package['id'])

    try:
        remote_url = 'http://qldspatial.information.qld.gov.au/catalogue/rest/document?id=' + package['sys.sync.foreign.id_s'] + '&f=xml'
        response = requests.get(remote_url)

        if response.status_code == 200:
            # Write the xml to file.
            file = open('xml_files/' + package['id'] + '.xml', 'w')
            file.write(response.text)
            file.close()

            return True
    except Exception as e:
        print(str(e))

    return False

def main():
    remote_url = 'http://qldspatial.information.qld.gov.au/catalogue/solrSearch?start=0&wt=json&facet=true&q=*%3A*&fq=id.table_s%3Atable.docindex&fq=contact.organizations_ss%3A%22Department+of+Environment+and+Science%22&facet.field=apiso.Type_s&facet.field=apiso.TopicCategory_ss&facet.field=contact.organizations_ss&f.apiso.Type_s.facet.mincount=1&f.apiso.Type_s.facet.limit=10&f.apiso.TopicCategory_ss.facet.mincount=1&f.apiso.TopicCategory_ss.facet.limit=10&f.contact.organizations_ss.facet.mincount=1&f.contact.organizations_ss.facet.limit=10'
    packages = gather_remote_packages(remote_url=remote_url)

    if not packages:
        print('>>> Not able to load remote packages.')
        return False

    print('>>> Successfully gathering %s packages from remote URL' % len(packages))

    for package in packages:
        fetch_and_save_xml(package)

    print('>>> Remote url harvested and xml files created, now you can execute import_xml.py')

if __name__ == '__main__':
    main()

import requests
import csv
import os

import urllib.parse as urlparse
from urllib.parse import parse_qs
from pprint import pformat


def gather_remote_packages(remote_url, csv_reader):
    """
    Gather all packages from QSpatial.

    @TODO, need to loop to all pages, currently only 1 page.
    """
    packages = []
    try:
        for row in csv_reader:
            print(row)
            title = row.get('Title')

            url = row.get('URL')
            fid = url
            print('>>> Gathering remote packages {}'.format(title))

            response = requests.get(remote_url.format(title=title))

            if response.status_code == 200:
                result = response.json()
                packages.append(result['response']['docs'][0] or [])
    except Exception as e:
        print(str(e))

    return packages


def fetch_and_save_xml(package):
    print('>>> Fetching an xml file for : %s' % package['title'])

    try:
        remote_url = 'http://qldspatial.information.qld.gov.au/catalogue/rest/document?id=' + package['fid'] + '&f=xml'
        response = requests.get(remote_url)

        if response.status_code == 200 and 'Unable to return the document associated with the supplied identifier' not in response.text:
            # Write the xml to file.
            file = open('xml_files/' + package['fid'] + '.xml', 'w')
            file.write(response.text)
            file.close()

            return True
        else:
            print(f"Failed to retrieve [{package['title']}] with identifier [{package['fid']}]")
            print(pformat(vars(response)))

    except Exception as e:
        print(pformat(e))

    return False


def main():
    if not os.path.exists('xml_files'):
        os.makedirs('xml_files')
    with open('DES_Datasets_QSpatial_v2.csv', "rt") as file:
        data = file.read().split('\n')

    csv_reader = csv.DictReader(data)
    # remote_url = 'http://qldspatial.information.qld.gov.au/catalogue/solrSearch?wt=json&q=%22{title}%22'
    # # remote_url = 'http://qldspatial.information.qld.gov.au/catalogue/solrSearch?start=0&wt=json&facet=true&q=*%3A*&fq=id.table_s%3Atable.docindex&fq=contact.organizations_ss%3A%22Department+of+Environment+and+Science%22&facet.field=apiso.Type_s&facet.field=apiso.TopicCategory_ss&facet.field=contact.organizations_ss&f.apiso.Type_s.facet.mincount=1&f.apiso.Type_s.facet.limit=10&f.apiso.TopicCategory_ss.facet.mincount=1&f.apiso.TopicCategory_ss.facet.limit=10&f.contact.organizations_ss.facet.mincount=1&f.contact.organizations_ss.facet.limit=10&q="Aquatic%20conservation%20assessment%20-%20Cape%20York%20catchments%20-%20non-riverine"'
    # packages = gather_remote_packages(remote_url, csv_reader)

    # if not packages:
    #     print('>>> Not able to load remote packages.')
    #     return False

    # print('>>> Successfully gathering %s packages from remote URL' % len(packages))
    count = 0
    for row in csv_reader:
        count += 1
        if count > 1000:
            break
        # print(row)
        title = row.get('Title')
        url = row.get('URL')
        parsed = urlparse.urlparse(url)
        fid = parse_qs(parsed.query)['fid'][0]
        package = {
            "title": title,
            "fid": fid
        }
        # print(package)
        fetch_and_save_xml(package)

    print('>>> Remote url harvested and xml files created, now you can execute import_xml.py')


if __name__ == '__main__':
    main()

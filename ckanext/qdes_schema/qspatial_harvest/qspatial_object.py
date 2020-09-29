import re

from xml.dom import minidom
from pprint import pformat

class QSpatialObject:
    """
    This class will do mapping from QSpatial XML to CKAN package dictionary.
    """
    xmldom = None
    package = {}

    def __init__(self, xml_filename):
        self.xmldom = minidom.parse(xml_filename)

    def get_ckan_package_dict(self):
        self.package.update(self.get_title())
        self.package.update(self.get_classification())
        self.package.update(self.get_notes())
        self.package.update(self.get_topic())
        self.package.update(self.get_contact_point())
        self.package.update(self.get_contact_publisher())
        self.package.update(self.get_publication_status())
        self.package.update(self.get_classification_and_access_restrictions())
        self.package.update(self.get_license_id())
        self.package.update({'name': re.sub('[^0-9a-zA-Z]+', '-', self.package['title']).lower()[:100]})

        return self.package

    @staticmethod
    def get_text(nodelist):
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return ''.join(rc)

    def get_title(self):
        identification_info = self.xmldom.getElementsByTagName('identificationInfo')
        citation = identification_info[0].getElementsByTagName('citation')
        title = citation[0].getElementsByTagName('gco:CharacterString')
        return {'title': self.get_text(title[0].childNodes)}

    def get_classification(self):
        return {'classification': 'classification'}

    def get_notes(self):
        return {'notes': 'notes'}

    def get_topic(self):
        return {'topic': 'topic'}

    def get_contact_point(self):
        return {'contact_point': 'contact_point'}

    def get_contact_publisher(self):
        return {'contact_publisher': 'contact_publisher'}

    def get_publication_status(self):
        return {'publication_status': 'publication_status'}

    def get_classification_and_access_restrictions(self):
        return {'classification_and_access_restrictions': 'classification_and_access_restrictions'}

    def get_license_id(self):
        return {'license_id': 'license_id'}

import re

from datetime import datetime as dt
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
        self.package.update(self.get_identifiers())
        self.package.update(self.get_classification())
        self.package.update(self.get_notes())
        self.package.update(self.get_topic())
        self.package.update(self.get_contact_point())
        self.package.update(self.get_contact_publisher())
        self.package.update(self.get_publication_status())
        self.package.update(self.get_classification_and_access_restrictions())
        self.package.update(self.get_license_id())
        self.package.update(self.get_owner_org())
        # @TODO: Adjust the truncation limit based on a sample of dataset titles observed
        self.package.update({'name': re.sub('[^0-9a-zA-Z]+', '-', self.package['title']).lower()[:100]})

        # Populate some of the other fields that throw errors from scheming validation
        self.package['metadata_review_date_reviewed'] = dt.utcnow().strftime('%Y-%m-%dT%H:%M:%S')

        # @TODO: These ones should probably have the ignore_missing validator added to themx
        for field in [
            'qdes_iso_8601_durations',
            'parameter',
            'contact_other_party',
            'lineage_inputs',
            'lineage_sensor',
            'url',
        ]:
            self.package[field] = None

        return self.package

    @staticmethod
    def get_text(nodelist):
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return ''.join(rc)

    def get_identifiers(self):
        fileidentifier = self.xmldom.getElementsByTagName('fileIdentifier')
        return {'identifiers': '["{}"]'.format(self.get_text(fileidentifier[0].getElementsByTagName('gco:CharacterString')[0].childNodes))}

    def get_title(self):
        identification_info = self.xmldom.getElementsByTagName('identificationInfo')
        citation = identification_info[0].getElementsByTagName('citation')
        title = citation[0].getElementsByTagName('gco:CharacterString')
        return {'title': self.get_text(title[0].childNodes)}

    def get_classification(self):
        return {'classification': 'classification'}

    def get_notes(self):
        identification_info = self.xmldom.getElementsByTagName('identificationInfo')
        abstract = identification_info[0].getElementsByTagName('abstract')
        return {'notes': self.get_text(abstract[0].getElementsByTagName('gco:CharacterString')[0].childNodes)}

    def get_topic(self):
        return {'topic': 'topic'}

    def get_contact_point(self):
        # @TODO: Grab the first term from the vocabulary_service for testing purposes
        return {'contact_point': 'http://linked.data.gov.au/def/iso19115-1/RoleCode/author'}

    def get_contact_publisher(self):
        # @TODO: Grab the first term from the vocabulary_service for testing purposes
        return {'contact_publisher': 'http://linked.data.gov.au/def/organisation-type/family-partnership'}

    def get_publication_status(self):
        # @TODO: Grab the first term from the vocabulary_service for testing purposes
        return {'publication_status': 'http://registry.it.csiro.au/def/isotc211/MD_ProgressCode/completed'}

    def get_classification_and_access_restrictions(self):
        # @TODO: Grab the first term from the vocabulary_service for testing purposes
        return {'classification_and_access_restrictions': 'classification_and_access_restrictions'}

    def get_license_id(self):
        # @TODO: Grab the first term from the vocabulary_service for testing purposes
        return {'license_id': 'http://registry.it.csiro.au/licence/csiro-binary-software-v1.0'}

    def get_owner_org(self):
        return {'owner_org': 'salsa-digital'}

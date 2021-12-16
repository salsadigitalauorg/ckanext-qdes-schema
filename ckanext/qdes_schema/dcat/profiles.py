
from rdflib import URIRef, BNode, Literal
from rdflib.namespace import Namespace, RDF, XSD, SKOS, RDFS
from ckanext.dcat.profiles import RDFProfile, URIRefOrLiteral

# Copied from ckanext-dcat/ckanext/dcat/profiles.py
DCT = Namespace("http://purl.org/dc/terms/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
ADMS = Namespace("http://www.w3.org/ns/adms#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SCHEMA = Namespace('http://schema.org/')
TIME = Namespace('http://www.w3.org/2006/time')
LOCN = Namespace('http://www.w3.org/ns/locn#')
GSP = Namespace('http://www.opengis.net/ont/geosparql#')
OWL = Namespace('http://www.w3.org/2002/07/owl#')
SPDX = Namespace('http://spdx.org/rdf/terms#')

GEOJSON_IMT = 'https://www.iana.org/assignments/media-types/application/vnd.geo+json'

namespaces = {
    'dct': DCT,
    'dcat': DCAT,
    'adms': ADMS,
    'vcard': VCARD,
    'foaf': FOAF,
    'schema': SCHEMA,
    'time': TIME,
    'skos': SKOS,
    'locn': LOCN,
    'gsp': GSP,
    'owl': OWL,
    'spdx': SPDX,
}


class QDESDCATProfile(RDFProfile):
    '''
    An RDF profile for the QDES DCAT recommendation for data portals
    '''


    def graph_from_dataset(self, dataset_dict, dataset_ref):

        # Basic fields
        items = [
            ('title', DCT.title, None, Literal),
            ('notes', DCT.description, None, Literal),
            ('url', DCAT.landingPage, None, URIRef),
            ('purpose', DCAT.purpose, None, Literal),
        ]
        self._add_triples_from_dict(dataset_dict, dataset_ref, items)

        #  Lists
        items = [
            ('identifiers', DCT.identifier, ['id'], Literal),
            ('classification', DCT.type, None, URIRef),
        ]
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, items)

import ckan.plugins.toolkit as toolkit
import ckan.model as model
import logging

from rdflib import URIRef, BNode, Literal
from rdflib.namespace import Namespace, RDF, XSD, SKOS, RDFS
from ckanext.dcat.profiles import RDFProfile, URIRefOrLiteral, CleanedURIRef, SCHEMA
from ckanext.dcat.utils import resource_uri
from ckanext.relationships import constants
from urllib.parse import urlparse, unquote, parse_qs

h = toolkit.h
get_action = toolkit.get_action
log = logging.getLogger(__name__)


DCTERMS = Namespace("http://purl.org/dc/terms/")
QDCAT = Namespace("https://linked.data.qld.gov.au/def/dcat#")
QDCATS = Namespace("http://linked.data.qld.gov.au/def/dcat-shapes#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
QUDT = Namespace("http://qudt.org/schema/qudt/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
GEOX = Namespace("http://linked.data.gov.au/def/geox#")
DQV = Namespace("http://www.w3.org/ns/dqv#")
OA = Namespace("http://www.w3.org/ns/oa#")
PROV = Namespace("http://www.w3.org/ns/prov#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
ADMS = Namespace("http://www.w3.org/ns/adms#")
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
LOCN = Namespace('http://www.w3.org/ns/locn#')

GEOJSON_IMT = 'https://www.iana.org/assignments/media-types/application/vnd.geo+json'

# Register/update namespaces.
namespaces = {
    'dcterms': DCTERMS,
    'qdcat': QDCAT,
    'qdcats': QDCATS,
    'rdfs': RDFS,
    'qudt': QUDT,
    'geo': GEO,
    'geox': GEOX,
    'dqv': DQV,
    'oa': OA,
    'prov': PROV,
    'sosa': SOSA,
    'adms': ADMS,
    'odrl': ODRL,
    'locn': LOCN,
}


class QDESDCATProfile(RDFProfile):
    '''
    An RDF profile for the QDES DCAT recommendation for data portals
    '''

    def graph_from_dataset(self, dataset_dict, dataset_ref):
        if dataset_dict.get('type') == 'dataset':
            self._dataset_graph(dataset_dict, dataset_ref)
        elif dataset_dict.get('type') == 'dataservice':
            self._dataservice_graph(dataset_dict, dataset_ref)


    def _dataset_graph(self, dataset_dict, dataset_ref):
        g = self.g

        # Let's update the namespace here.
        overridden_namespace = [
            DCTERMS,  # DCT prefix need to be DCTERMS as per spec
            GEO  # DCT prefix need to be DCTERMS as per spec
        ]
        for prefix, namespace in namespaces.items():
            override = False
            if namespace in overridden_namespace:
                override = True

            g.bind(prefix, namespace, override=override)

        items = [
            ('identifiers', DCTERMS.identifier, ['id'], Literal),
            ('classification', DCTERMS.type, None, URIRef),
        ]
        # Identification
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, items)

        # Field purpose => qdcat:purpose
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('purpose', QDCAT.purpose, None, Literal)])

        # Field additional_info => rdfs:comment.
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('additional_info', RDFS.comment, None, Literal)])

        # Field dataset_language => dcterms:language
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('dataset_language', DCTERMS.language, None, URIRef)])

        # Field topic => dcat:theme
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('topic', DCAT.theme, None, URIRef)])

        # Field license => dcterms:license
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('license_id', DCTERMS.license, None, URIRef)])

        # Field dataset_creation_date => dcterms:created
        dataset_creation_date = self._get_dataset_value(dataset_dict, 'dataset_creation_date')
        if dataset_creation_date:
            g.add((dataset_ref, DCTERMS.created, Literal(dataset_creation_date, datatype=XSD.dateTime)))
        # Field dataset_release_date => dcterms:issued
        g.remove((dataset_ref, DCTERMS.issued, None))
        dataset_release_date = self._get_dataset_value(dataset_dict, 'dataset_release_date')
        if dataset_release_date:
            g.add((dataset_ref, DCTERMS.issued, Literal(dataset_release_date, datatype=XSD.dateTime)))

        # Field dataset_last_modified_date => dcterms:modified
        g.remove((dataset_ref, DCTERMS.modified, None))
        dataset_last_modified_date = self._get_dataset_value(dataset_dict, 'dataset_last_modified_date')
        if dataset_last_modified_date:
            g.add((dataset_ref, DCTERMS.modified, Literal(dataset_last_modified_date, datatype=XSD.dateTime)))

        # Field group parameter => qudt:hasQuantity a qudt:Quantity
        # observed-property => qudt:hasQuantityKind
        # unit-of-measure => qudt:unit
        parameter = self._get_dataset_value(dataset_dict, 'parameter')
        if parameter:
            values = toolkit.get_converter('json_or_string')(parameter)
            if values and isinstance(values, list):
                for value in values:
                    node = BNode()
                    g.add((node, RDF.type, QUDT.Quantity))

                    self._add_list_triple(node, QUDT.hasQuantityKind, value.get('observed-property'), URIRef)
                    self._add_list_triple(node, QUDT.unit, value.get('unit-of-measure'), URIRef)

                    g.add((dataset_ref, QUDT.hasQuantity, node))

        
        # Remove temporal
        for s, p, o in g:
            if p == SCHEMA.startDate:
                g.remove((s, p, None))
            if p == SCHEMA.endDate:
                g.remove((s, p, None))
            if o == DCTERMS.PeriodOfTime:
                g.remove((s, p, o)) 
        g.remove((dataset_ref, DCTERMS.temporal, None))
        self._temporal_graph(dataset_dict, dataset_ref)
        # Field temporal_precision_spacing => qdcat:temporalResolution => ^^type xsd:duration
        temporal_precision_spacing = self._get_dataset_value(dataset_dict, 'temporal_precision_spacing')
        if temporal_precision_spacing:
            g.add((dataset_ref, QDCAT.temporalResolution, Literal(temporal_precision_spacing, datatype=XSD.duration)))

        # Field temporal_resolution_range => qdcat:temporalRange
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('temporal_resolution_range', QDCAT.temporalRange, None, URIRef)])

        # Field spatial_name_code => dcterms:spatial
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('spatial_name_code', DCTERMS.spatialName, None, URIRef)])

        spatial = self._get_dataset_value(dataset_dict, 'spatial')
        spatial_centroid = self._get_dataset_value(dataset_dict, 'spatial_centroid')
        spatial_geometry = self._get_dataset_value(dataset_dict, 'spatial_geometry')
        spatial_lower_left = self._get_dataset_value(dataset_dict, 'spatial_lower_left')
        spatial_upper_right = self._get_dataset_value(dataset_dict, 'spatial_upper_right')
        spatial_name_code = self._get_dataset_value(dataset_dict, 'spatial_name_code')

        # Remove data from Euro profile.
        for s, p, o in g:
            if p == LOCN.geometry:
                g.remove((s, p, None))

        for s, p, o in g:
            if p == RDF.type and o == DCTERMS.Location:
                g.remove((s, p, o))

        g.remove((dataset_ref, DCTERMS.spatial, None))

        if spatial or spatial_centroid or spatial_geometry or spatial_lower_left or spatial_upper_right or spatial_name_code:
            # Field spatial_name_code => dcterms:spatial
            if spatial_name_code:
                g.add((dataset_ref, DCTERMS.spatial, URIRef(spatial_name_code)))

            if spatial_centroid or spatial_geometry:
                location_node = BNode()
                g.add((location_node, RDF.type, DCTERMS.Location))

                # Field spatial_centroid => dcterms:Location => dcat:centroid
                if spatial_centroid:
                    spatial_centroid_dict = toolkit.get_converter('json_or_string')(spatial_centroid)
                    g.add((location_node, DCAT.centroid, Literal(spatial_centroid_dict, datatype=GEOJSON_IMT)))

                # Field spatial_centroid => dcterms:Location => geo:hasGeometry a geo:Geometry => qdcat:asGeoJSON
                if spatial_geometry:
                    has_geometry_node = BNode()
                    g.add((has_geometry_node, RDF.type, GEO.Geometry))
                    spatial_geometry_dict = toolkit.get_converter('json_or_string')(spatial_geometry)
                    g.add((has_geometry_node, QDCAT.asGeoJSON, Literal(spatial_geometry_dict, datatype=GEOJSON_IMT)))
                    g.add((location_node, GEO.hasGeometry, has_geometry_node))

                g.add((dataset_ref, DCTERMS.spatial, location_node))

            if spatial_lower_left or spatial_upper_right:
                bbox_node = BNode()
                g.add((bbox_node, RDF.type, QDCAT.BBox))

                # Field spatial_lower_left => dcterms:spatial a qdcat:BBox => qdcat:lowerLeft
                if spatial_lower_left:
                    spatial_lower_left_dict = toolkit.get_converter('json_or_string')(spatial_lower_left)
                    g.add((bbox_node, QDCAT.lowerLeft, Literal(spatial_lower_left_dict, datatype=GEOJSON_IMT)))

                # Field spatial_upper_right => dcterms:spatial a qdcat:BBox => qdcat:upperRight
                if spatial_upper_right:
                    spatial_upper_right_dict = toolkit.get_converter('json_or_string')(spatial_upper_right)
                    g.add((bbox_node, QDCAT.upperRight, Literal(spatial_upper_right_dict, datatype=GEOJSON_IMT)))

                g.add((dataset_ref, DCTERMS.spatial, bbox_node))
        

        # Field spatial_content_resolution => dcat:spatialResolutionInMeters
        spatial_content_resolution = self._get_dataset_value(dataset_dict, 'spatial_content_resolution')
        if spatial_content_resolution:
            g.add((dataset_ref, DCAT.spatialResolutionInMeters, Literal(spatial_content_resolution, datatype=XSD.decimal)))

        spatial_representation = self._get_dataset_value(dataset_dict, 'spatial_representation')
        spatial_resolution = self._get_dataset_value(dataset_dict, 'spatial_resolution')
        spatial_datum_crs = self._get_dataset_value(dataset_dict, 'spatial_datum_crs')
        if spatial_representation or spatial_resolution or spatial_datum_crs:
            location_node = BNode()
            g.add((location_node, RDF.type, QDCAT.SpatialRepresentation))

            # Field spatial_representation => dcterms:type
            if spatial_representation:
                g.add((location_node, DCTERMS.type, URIRef(spatial_representation)))

            # Field spatial_resolution => qdcat:spatialResolution
            if spatial_resolution:
                g.add((location_node, DCAT.spatialResolution, URIRef(spatial_resolution)))

            # Field spatial_datum_crs => geox:inCRS
            if spatial_datum_crs:
                g.add((location_node, GEOX.inCRS, URIRef(spatial_datum_crs)))

            # qdcat:hasSpatialRepresentation
            g.add((dataset_ref, QDCAT.hasSpatialRepresentation, location_node))

        # Field conforms_to => dcterms:conformsTo
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('conforms_to', DCTERMS.conformsTo, None, Literal)])

        quality_measure = self._get_dataset_value(dataset_dict, 'quality_measure')
        if quality_measure:
            values = toolkit.get_converter('json_or_string')(quality_measure)
            if values and isinstance(values, list):
                for value in values:
                    quality_measurement_node = BNode()
                    g.add((quality_measurement_node, RDF.type, DQV.QualityMeasurement))

                    # Field quality_measure.dimension => dqv:inDimension
                    self._add_list_triple(quality_measurement_node, DQV.inDimension, value.get('measurement'), URIRef)

                    # Field quality_measure.value => oa:bodyValue
                    self._add_list_triple(quality_measurement_node, OA.bodyValue, value.get('value'), Literal)

                    # dqv:hasQualityMeasurement a QualityMeasurement
                    g.add((dataset_ref, DQV.hasQualityMeasurement, quality_measurement_node))

        quality_description = self._get_dataset_value(dataset_dict, 'quality_description')
        if quality_description:
            values = toolkit.get_converter('json_or_string')(quality_description)
            if values and isinstance(values, list):
                for value in values:
                    quality_annotation_node = BNode()
                    g.add((quality_annotation_node, RDF.type, DQV.QualityAnnotation))

                    # Field quality_description.dimension => dqv:inDimension
                    self._add_list_triple(quality_annotation_node, DQV.inDimension, value.get('dimension'), URIRef)

                    # Field quality_description.value => oa:bodyValue
                    self._add_list_triple(quality_annotation_node, OA.bodyValue, value.get('value'), Literal)

                    # dqv:hasQualityAnnotation a dqv:QualityAnnotation
                    g.add((dataset_ref, DQV.hasQualityAnnotation, quality_annotation_node))

        # Relationship
        series_relationships = h.get_series_relationship(dataset_dict)
        if series_relationships:
            is_part_of = series_relationships.get('Is Part Of')
            if is_part_of:
                for dataset in is_part_of:
                    # Is Part Of.
                    g.add((dataset_ref, DCTERMS.isPartOf, URIRef(h.url_for('dataset.read', id=dataset.get('pkg_id'), _external=True))))

        # Related dataset
        self._get_related_dataset_node(dataset_dict, dataset_ref)

        lineage_description = self._get_dataset_value(dataset_dict, 'lineage_description')
        lineage_plan = self._get_dataset_value(dataset_dict, 'lineage_plan')
        lineage_inputs = self._get_dataset_value(dataset_dict, 'lineage_inputs')
        lineage_sensor = self._get_dataset_value(dataset_dict, 'lineage_sensor')
        lineage_responsible_party = self._get_dataset_value(dataset_dict, 'lineage_responsible_party')
        if lineage_description or lineage_plan or lineage_inputs or lineage_sensor or lineage_responsible_party:
            activity_node = BNode()
            g.add((activity_node, RDF.type, PROV.Activity))

            # Field lineage_description => dcterms:description
            if lineage_description:
                self._add_list_triple(activity_node, DCTERMS.description, lineage_description, Literal)

            # Field lineage_plan => prov:hadPlan
            if lineage_plan:
                self._add_list_triple(activity_node, PROV.hadPlan, lineage_plan, URIRef)

            # Field lineage_inputs => prov:used
            if lineage_inputs:
                values = toolkit.get_converter('json_or_string')(lineage_inputs)
                if values and isinstance(values, list):
                    for value in values:
                        self._add_list_triple(activity_node, PROV.used, value, URIRef)

            # Field lineage_sensor => sosa:madeBySensor
            if lineage_sensor:
                values = toolkit.get_converter('json_or_string')(lineage_sensor)
                if values and isinstance(values, list):
                    for value in values:
                        self._add_list_triple(activity_node, SOSA.madeBySensor, value, URIRef)

            # Field lineage_responsible_party => prov:wasAssociatedWith
            if lineage_responsible_party:
                values = toolkit.get_converter('json_or_string')(lineage_responsible_party)
                if values and isinstance(values, list):
                    for value in values:
                        self._add_list_triple(activity_node, PROV.wasAssociatedWith, value, Literal)

            # prov:wasGeneratedBy as prov:Activity
            g.add((dataset_ref, PROV.wasGeneratedBy, activity_node))

        # Field cited_in => dcterms:isReferencedBy
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('cited_in', DCTERMS.isReferencedBy, None, URIRef)])

        # Field contact_point => dcat:contactPoint
        dataset_dict['contact_point'] = _get_point_of_contact_name(dataset_dict['contact_point'])
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('contact_point', DCAT.contactPoint, None, Literal)])

        # Field contact_publisher => dcterms:publisher
        g.remove((dataset_ref, DCTERMS.publisher, None))
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('contact_publisher', DCTERMS.publisher, None, URIRef)])

        # Field contact_creator => dcterms:creator
        dataset_dict['contact_creator'] = _get_point_of_contact_name(dataset_dict['contact_creator'])
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('contact_creator', DCTERMS.creator, None, Literal)])

        # Field contact_other_party => prov:qualifiedAttribution
        self._get_contact_other_party_node(dataset_dict, dataset_ref)

        # Field acknowledgements => qdcat:acknowledgments
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('acknowledgements', QDCATS.acknowledgments, None, Literal)])

        # Field publication_status => adms:status
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('publication_status', ADMS.status, None, URIRef)])

        self._get_catalog_record(dataset_dict, dataset_ref)

        # Field update_schedule => dcterms:accrualPeriodicity
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('update_schedule', DCTERMS.accrualPeriodicity, None, URIRef)])

        # Field classification_and_access_restrictions => dcterms:accessRights
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('classification_and_access_restrictions', DCTERMS.accessRights, None, URIRef)])

        # Field rights_statement => dcterms:rights
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('rights_statement', DCTERMS.rights, None, Literal)])

        # Field specialized_license => odrl:hasPolicy
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('specialized_license', ODRL.hasPolicy, None, Literal)])

        # Field landing_page => dcat:landingPage
        g.remove((dataset_ref, DCAT.landingPage, None))
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('landing_page', DCAT.landingPage, None, URIRef)])

        # Distributions/resources
        for resource_dict in dataset_dict.get('resources', []):
            distribution = CleanedURIRef(resource_uri(resource_dict))

            # Field schema_standards => dcterms:conformsTo
            self._add_list_triples_from_dict(resource_dict, distribution, [('schema_standards', DCTERMS.conformsTo, None, URIRef)])

            # Field compression => dcat:compressFormat
            self._add_list_triples_from_dict(resource_dict, distribution, [('compression', DCAT.compressFormat, None, URIRef)])

            # Field packaging => dcat:packageFormat
            self._add_list_triples_from_dict(resource_dict, distribution, [('packaging', DCAT.packageFormat, None, URIRef)])

            # Field size => dcat:byteSize
            self._add_list_triples_from_dict(resource_dict, distribution, [('size', DCAT.packageFormat, None, Literal)])

            # Field url => dcat:downloadURL
            self._add_list_triples_from_dict(resource_dict, distribution, [('url', DCAT.downloadURL, None, URIRef)])

            # Field service_api_endpoint => dcat:accessURL
            self._add_list_triples_from_dict(resource_dict, distribution, [('service_api_endpoint', DCAT.accessURL, None, URIRef)])

            # Field data_services => dcat:accessService
            data_services = self._get_dataset_value(resource_dict, 'data_services')
            if data_services:
                values = toolkit.get_converter('json_or_string')(data_services)
                if values and isinstance(values, list):
                    for dataset in values:
                        g.add((distribution, DCAT.accessService, URIRef(h.url_for('dataset.read', id=dataset, _external=True))))

            # Field description => dcterms:description
            self._add_list_triples_from_dict(resource_dict, distribution, [('description', DCTERMS.description, None, Literal)])

            # Field additional_info => rdfs:comment
            self._add_list_triples_from_dict(resource_dict, distribution, [('additional_info', RDFS.comment, None, Literal)])

            # Field rights_statement => dcterms:rights
            self._add_list_triples_from_dict(resource_dict, distribution, [('rights_statement', DCTERMS.rights, None, Literal)])

    def _dataservice_graph(self, dataset_dict, dataset_ref):
        g = self.g

        # Field data_services => dcat:Dataservice
        g.remove((dataset_ref, RDF.type, DCAT.Dataset))
        g.add((dataset_ref, RDF.type, QDCAT.DataService))

        # Let's update the namespace here.
        overridden_namespace = [
            DCTERMS,  # DCT prefix need to be DCTERMS as per spec
            GEO  # DCT prefix need to be DCTERMS as per spec
        ]
        for prefix, namespace in namespaces.items():
            override = False
            if namespace in overridden_namespace:
                override = True

            g.bind(prefix, namespace, override=override)

        items = [
            ('identifiers', DCTERMS.identifier, ['id'], Literal),
            ('classification', DCTERMS.type, None, URIRef),
        ]
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, items)

        # Field additional_info => rdfs:comment.
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('additional_info', RDFS.comment, None, Literal)])

        # Field dataset_language => dcterms:language
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('dataset_language', DCTERMS.language, None, URIRef)])

        # Field topic => dcat:theme
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('topic', DCAT.theme, None, URIRef)])

        # Field notes => dcterms:description
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('notes', DCTERMS.description, None, Literal)])

        # Field language => dcterms:language
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('language', DCTERMS.language, None, URIRef)])

        # Field tags => dcat:keyword
        tags = dataset_dict.get('tags')
        if tags:
            for tag in tags:
                g.add((dataset_ref, DCAT.keyword, Literal(tag.get('display_name'))))

        # Field datasets_available => dcat:servesDataset
        datasets_available = dataset_dict.get('datasets_available')
        if datasets_available:
            values = toolkit.get_converter('json_or_string')(datasets_available)
            if values and isinstance(values, list):
                for dataset_id in values:
                    g.add((dataset_ref, DCAT.servesDataset, URIRef(h.url_for('dataset.read', id=dataset_id, _external=True))))

        # Field standards => dcterms:conformsTo
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('standards', DCTERMS.conformsTo, None, URIRef)])

        # Field endpoint_details => dcat:endpointDescription
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('endpoint_details', DCAT.endpointDescription, None, URIRef)])

        # Field api_address => dcat:endpointURL
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('api_address', DCAT.endpointURL, None, URIRef)])

        # Field service_uri => dcat:landingPage
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('service_uri', DCAT.landingPage, None, URIRef)])

        # Field service_status => adms:status
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('service_status', ADMS.status, None, URIRef)])

        # Field service_creation_date => dcterms:created
        service_creation_date = self._get_dataset_value(dataset_dict, 'service_creation_date')
        if service_creation_date:
            g.add((dataset_ref, DCTERMS.created, Literal(service_creation_date, datatype=XSD.dateTime)))

        # Field service_launch_date => dcterms:issued
        g.remove((dataset_ref, DCTERMS.issued, None))
        service_launch_date = self._get_dataset_value(dataset_dict, 'service_launch_date')
        if service_launch_date:
            g.add((dataset_ref, DCTERMS.issued, Literal(service_launch_date, datatype=XSD.dateTime)))

        # Field service_last_modified_date => dcterms:modified
        g.remove((dataset_ref, DCTERMS.modified, None))
        service_last_modified_date = self._get_dataset_value(dataset_dict, 'service_last_modified_date')
        if service_last_modified_date:
            g.add((dataset_ref, DCTERMS.modified, Literal(service_last_modified_date, datatype=XSD.dateTime)))

        # Related dataset
        self._get_related_dataset_node(dataset_dict, dataset_ref)

        # Field contact_point => dcat:contactPoint
        dataset_dict['contact_point'] = _get_point_of_contact_name(dataset_dict['contact_point'])
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('contact_point', DCAT.contactPoint, None, Literal)])

        # Field contact_publisher => dcterms:publisher
        g.remove((dataset_ref, DCTERMS.publisher, None))
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('contact_publisher', DCTERMS.publisher, None, Literal)])

        # Field contact_creator => dcterms:creator
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('contact_creator', DCTERMS.creator, None, Literal)])

        # Field contact_other_party => prov:qualifiedAttribution
        self._get_contact_other_party_node(dataset_dict, dataset_ref)

        # Field classification_and_access_restrictions => dcterms:accessRights
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('classification_and_access_restrictions', DCTERMS.accessRights, None, URIRef)])

        # Field rights_statement => dcterms:rights
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('rights_statement', DCTERMS.rights, None, Literal)])

        # Field license => dcterms:license
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('license', DCTERMS.license, None, URIRef)])

        # Field specialized_license => odrl:hasPolicy
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('specialized_license', ODRL.hasPolicy, None, URIRef)])

        self._get_catalog_record(dataset_dict, dataset_ref)

        # Field url => dcterms:source
        self._add_list_triples_from_dict(dataset_dict, dataset_ref, [('url', DCTERMS.source, None, URIRef)])

    def _get_related_dataset_node(self, dataset_dict, dataset_ref):
        g = self.g
        all_relationships = h.get_all_relationships(dataset_dict.get('id'))
        if all_relationships:
            values = toolkit.get_converter('json_or_string')(all_relationships)
            if values and isinstance(values, list):
                for value in values:
                    relation = value.get('comment') or h.url_for('dataset.read', id=value.get('pkg_id'), _external=True) if value.get(
                        'pkg_id') else None
                    relationship_type = value.get('type')
                    role = constants.RELATIONSHIP_TYPE_URIS.get(relationship_type, None)

                    # dcat:qualifiedRelation
                    if relation or role:
                        relationship_node = BNode()
                        g.add((relationship_node, RDF.type, DCAT.Relationship))

                        # dcterms:relation
                        if relation:
                            g.add((relationship_node, DCTERMS.relation, URIRef(relation)))

                        # dcat:hadRole
                        if role:
                            # Get URI query param and decode
                            parsed_url = urlparse(role)
                            parsed_query_params = parse_qs(parsed_url.query)
                            uri = parsed_query_params.get('uri', [])
                            role = unquote(uri[0] if len(uri) > 0 else '')
                            # SUPDESQ-97 fix for role
                            g.add((relationship_node, DCAT.hadRole, URIRef(role)))

                        g.add((dataset_ref, DCAT.qualifiedRelation, relationship_node))

    def _get_contact_other_party_node(self, dataset_dict, dataset_ref):
        g = self.g

        contact_other_party = self._get_dataset_value(dataset_dict, 'contact_other_party')
        if contact_other_party:
            values = toolkit.get_converter('json_or_string')(contact_other_party)
            if values and isinstance(values, list):
                for value in values:
                    attribution_node = BNode()
                    g.add((attribution_node, RDF.type, PROV.Attribution))

                    # Field contact_other_party.the-party => prov:agent
                    self._add_list_triple(attribution_node, PROV.agent, value.get('the-party'), Literal)

                    # Field contact_other_party.nature-of-their-responsibility => dcat:hadRole
                    self._add_list_triple(attribution_node, DCAT.hadRole, value.get('nature-of-their-responsibility'),
                                          URIRef)

                    # prov:qualifiedAttribution a prov:Attribution
                    g.add((dataset_ref, PROV.qualifiedAttribution, attribution_node))

    def _get_catalog_record(self, dataset_dict, dataset_ref):
        g = self.g
        # Set CatalogRecord
        catalog_record = BNode()

        # Field metadata_created => DCTERMS.issued
        if dataset_dict.get('type') == 'dataset':
            metadata_created = self._get_dataset_value(dataset_dict, 'metadata_created')
            if metadata_created:
                g.add((catalog_record, DCTERMS.issued, Literal(metadata_created, datatype=XSD.dateTime)))

            # Field metadata_modified => DCTERMS.modified
            metadata_modified = self._get_dataset_value(dataset_dict, 'metadata_modified')
            if metadata_modified:
                g.add((catalog_record, DCTERMS.modified, Literal(metadata_modified, datatype=XSD.dateTime)))
            
             # Field metadata_update_date => qdcat:modified
            metadata_update_date = self._get_dataset_value(dataset_dict, 'metadata_update_date')
            if metadata_update_date:
                g.add((catalog_record, DCTERMS.modified, Literal(metadata_update_date, datatype=XSD.dateTime)))

        # Field metadata_modified => qdcat:reviewed
        metadata_review_date = self._get_dataset_value(dataset_dict, 'metadata_review_date')
        if metadata_review_date:
            g.add((catalog_record, QDCAT.reviewed, Literal(metadata_review_date, datatype=XSD.dateTime)))
        
        # Field url => dcterms:source
        self._add_list_triples_from_dict(dataset_dict, catalog_record, [('url', DCTERMS.source, None, URIRef)])

        # Field metadata_contact_point => dcat:contactPoint
        dataset_dict['metadata_contact_point'] = _get_point_of_contact_name(dataset_dict['metadata_contact_point'])
        self._add_list_triples_from_dict(dataset_dict, catalog_record, [('metadata_contact_point', DCAT.contactPoint, None, Literal)])

        organization = self._get_dataset_value(dataset_dict, 'organization')
        organization_name = organization.get('name')
        g.add((catalog_record, DCTERMS.publisher, Literal(organization_name)))

        g.add((dataset_ref, DCAT.CatalogRecord, catalog_record ))

    def _temporal_graph(self, dataset_dict, dataset_ref):
        g = self.g
        start = self._get_dataset_value(dataset_dict, 'temporal_start')
        end = self._get_dataset_value(dataset_dict, 'temporal_end')
        temporal_extent = BNode()
        g.add((temporal_extent, RDF.type, DCAT.PeriodOfTime))
        if start:
            self._add_date_triple(temporal_extent, DCAT.startDate, start)
        if end:
            self._add_date_triple(temporal_extent, DCAT.endDate, end)
        g.add((dataset_ref, DCAT.temporal, temporal_extent))

def _get_point_of_contact_name(contact_point):
    # TODO: Need to load all secure vocabs as dict objects
    # Load vocabulary service contact_point
    context = {
        u'model': model,
        u'user': toolkit.g.user,
        u'auth_user_obj': toolkit.g.userobj
    }
    if context.get('__auth_audit', None):
        context['__auth_audit'].pop()

    vocab_value = {}
    if contact_point:
        secure_vocabulary_record = get_action('get_secure_vocabulary_record')(
            context, {'vocabulary_name': 'point-of-contact', 'query': contact_point})
        if secure_vocabulary_record:
            vocab_value = secure_vocabulary_record
            contact_point = "{} - {}".format(vocab_value.get('Name'), vocab_value.get('Functional Position'))
            return contact_point

    return contact_point


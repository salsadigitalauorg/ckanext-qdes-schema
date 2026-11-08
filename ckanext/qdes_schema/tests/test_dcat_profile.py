# encoding: utf-8
"""Integration tests for how the QDES DCAT profile exports text fields.

ckanext-dcat's list helpers split any string that isn't JSON on commas, so
prose such as a rights statement was exported as several fragments. Text is
now exported by the field's cardinality in the schema:

- scalar text fields are one Literal, verbatim, even when they look like JSON
- multi-value text fields (`additional_info`) are one Literal per item, read
  from a native or JSON-encoded list, and never split on commas
"""

import json

import pytest

import ckan.model as model

from rdflib import BNode, Graph, Literal, URIRef
from ckan.common import config
from ckan.plugins.toolkit import g
from ckanext.dcat.processors import RDFSerializer
from ckanext.dcat.profiles import CleanedURIRef
from ckanext.dcat.utils import resource_uri
from ckanext.qdes_schema.dcat.profiles import (
    DCAT, DCTERMS, DQV, OA, ODRL, PROV, QDCAT, QDCATS, RDFS, QDESDCATProfile
)

RIGHTS = '© State of Queensland (Department of the Environment, Tourism, Science and Innovation) 2026'
PROSE = 'Landsat imagery was downloaded, converted, and composited (Flood, 2013).'
CONTACT = 'Smith, Jane - Manager, Science'
ITEMS = [PROSE, 'Second note, also with a comma']
# Scalar text that json.loads would accept: it must still be exported verbatim.
JSON_LOOKING = ['["red", "green"]', '[]', '42', '"quoted"']
MISSING = [None, '']

RESOURCE_ID = 'b1a3c5d7-0000-4000-8000-000000000001'


def make_dataset(name, type='dataset'):
    dataset = model.Package(name=name, title=name, type=type, state='active')
    model.Session.add(dataset)
    model.Session.commit()
    return dataset


def dataset_dict(dataset, **fields):
    data = {
        'id': dataset.id,
        'name': dataset.name,
        'title': dataset.title,
        'type': dataset.type,
        'organization': {'id': 'science', 'name': 'science'},
        'resources': [],
    }
    data.update(fields)
    return data


def resource(**fields):
    data = {'id': RESOURCE_ID, 'url': 'https://example.com/data.csv'}
    data.update(fields)
    return data


def objects(graph, subject, predicate):
    return sorted(str(o) for o in graph.objects(subject, predicate))


def only_node(graph, subject, predicate):
    [node] = [o for o in graph.objects(subject, predicate) if isinstance(o, BNode)]
    return node


@pytest.fixture
def fake_contact_names(monkeypatch):
    """Resolve point-of-contact ids without the secure vocabulary tables."""
    monkeypatch.setattr(
        'ckanext.qdes_schema.dcat.profiles._get_point_of_contact_name',
        lambda contact: CONTACT if contact else contact,
    )


@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
class ProfileExport(object):
    """Exports one dataset or data service through the QDES profile alone."""

    dataset_type = 'dataset'

    @pytest.fixture(autouse=True)
    def setup(self, clean_db, with_request_context):
        g.user = ''
        g.userobj = None
        self.dataset = make_dataset('text-' + self.dataset_type, type=self.dataset_type)
        self.ref = URIRef('http://example.com/dataset/' + self.dataset.name)
        self.distribution = CleanedURIRef(resource_uri({'id': RESOURCE_ID}))
        self.graph = Graph()
        self.profile = QDESDCATProfile(self.graph)

    def export(self, **fields):
        self.profile.graph_from_dataset(dataset_dict(self.dataset, **fields), self.ref)


class TestDatasetScalarText(ProfileExport):
    @pytest.mark.parametrize(
        'field, predicate',
        [
            ('purpose', QDCAT.purpose),
            ('acknowledgements', QDCATS.acknowledgments),
            ('rights_statement', DCTERMS.rights),
            ('specialized_license', ODRL.hasPolicy),
        ],
    )
    @pytest.mark.parametrize('value', [RIGHTS, PROSE] + JSON_LOOKING)
    def test_is_one_verbatim_literal(self, field, predicate, value):
        self.export(**{field: value})

        assert list(self.graph.objects(self.ref, predicate)) == [Literal(value)]

    @pytest.mark.parametrize('value', MISSING)
    def test_missing_value_adds_nothing(self, value):
        self.export(rights_statement=value)

        assert objects(self.graph, self.ref, DCTERMS.rights) == []

    @pytest.mark.parametrize('value', [PROSE, '["a", "b"]'])
    def test_lineage_description_is_one_literal(self, value):
        self.export(lineage_description=value)

        activity = only_node(self.graph, self.ref, PROV.wasGeneratedBy)
        assert objects(self.graph, activity, DCTERMS.description) == [value]

    @pytest.mark.parametrize('value', [PROSE, '["a", "b"]'])
    def test_quality_values_are_one_literal(self, value):
        self.export(
            quality_measure=json.dumps([{'measurement': 'https://example.com/accuracy', 'value': value}]),
            quality_description=json.dumps([{'dimension': 'https://example.com/completeness', 'value': value}]),
        )

        measurement = only_node(self.graph, self.ref, DQV.hasQualityMeasurement)
        annotation = only_node(self.graph, self.ref, DQV.hasQualityAnnotation)
        assert objects(self.graph, measurement, OA.bodyValue) == [value]
        assert objects(self.graph, annotation, OA.bodyValue) == [value]

    def test_missing_quality_value_adds_no_body(self):
        self.export(quality_measure=json.dumps([{'measurement': 'https://example.com/accuracy', 'value': ''}]))

        measurement = only_node(self.graph, self.ref, DQV.hasQualityMeasurement)
        assert objects(self.graph, measurement, OA.bodyValue) == []

    def test_other_party_is_one_literal(self):
        self.export(contact_other_party=json.dumps([
            {'the-party': 'Smith, Jane', 'nature-of-their-responsibility': 'https://example.com/role'},
        ]))

        attribution = only_node(self.graph, self.ref, PROV.qualifiedAttribution)
        assert objects(self.graph, attribution, PROV.agent) == ['Smith, Jane']

    @pytest.mark.usefixtures('fake_contact_names')
    def test_contact_names_are_one_literal(self):
        self.export(contact_point='poc-1', contact_creator='poc-2', metadata_contact_point='poc-3')

        record = only_node(self.graph, self.ref, DCAT.CatalogRecord)
        assert objects(self.graph, self.ref, DCAT.contactPoint) == [CONTACT]
        assert objects(self.graph, self.ref, DCTERMS.creator) == [CONTACT]
        assert objects(self.graph, record, DCAT.contactPoint) == [CONTACT]


class TestResourceScalarText(ProfileExport):
    @pytest.mark.parametrize(
        'field, predicate',
        [
            ('description', DCTERMS.description),
            ('rights_statement', DCTERMS.rights),
        ],
    )
    @pytest.mark.parametrize('value', [RIGHTS, PROSE] + JSON_LOOKING)
    def test_is_one_verbatim_literal(self, field, predicate, value):
        self.export(resources=[resource(**{field: value})])

        assert list(self.graph.objects(self.distribution, predicate)) == [Literal(value)]

    @pytest.mark.parametrize('value', MISSING)
    def test_missing_value_adds_nothing(self, value):
        self.export(resources=[resource(rights_statement=value)])

        assert objects(self.graph, self.distribution, DCTERMS.rights) == []


class TestDataServiceScalarText(ProfileExport):
    dataset_type = 'dataservice'

    @pytest.mark.parametrize(
        'field, predicate',
        [
            ('notes', DCTERMS.description),
            ('rights_statement', DCTERMS.rights),
            ('specialized_license', ODRL.hasPolicy),
            ('contact_publisher', DCTERMS.publisher),
            ('contact_creator', DCTERMS.creator),
        ],
    )
    @pytest.mark.parametrize('value', [PROSE] + JSON_LOOKING)
    def test_is_one_verbatim_literal(self, field, predicate, value):
        self.export(**{field: value})

        assert list(self.graph.objects(self.ref, predicate)) == [Literal(value)]

    def test_specialized_license_url_is_a_literal_not_a_uri(self):
        self.export(specialized_license='https://example.com/licence')

        assert list(self.graph.objects(self.ref, ODRL.hasPolicy)) == [Literal('https://example.com/licence')]

    @pytest.mark.usefixtures('fake_contact_names')
    def test_contact_points_are_one_literal(self):
        self.export(contact_point='poc-1', metadata_contact_point='poc-2')

        record = only_node(self.graph, self.ref, DCAT.CatalogRecord)
        assert objects(self.graph, self.ref, DCAT.contactPoint) == [CONTACT]
        assert objects(self.graph, record, DCAT.contactPoint) == [CONTACT]

    @pytest.mark.parametrize('value', MISSING)
    def test_missing_value_adds_nothing(self, value):
        self.export(specialized_license=value)

        assert objects(self.graph, self.ref, ODRL.hasPolicy) == []


class MultiValueText(ProfileExport):
    """additional_info is multi-value text: one Literal per item."""

    def export_additional_info(self, value):
        raise NotImplementedError

    @pytest.mark.parametrize('value', [ITEMS, json.dumps(ITEMS)], ids=['native', 'json'])
    def test_list_keeps_one_literal_per_item(self, value):
        subject = self.export_additional_info(value)

        assert objects(self.graph, subject, RDFS.comment) == sorted(ITEMS)

    def test_plain_string_is_one_item(self):
        subject = self.export_additional_info(PROSE)

        assert objects(self.graph, subject, RDFS.comment) == [PROSE]

    @pytest.mark.parametrize('value', [None, '', '[]', '[""]', []])
    def test_empty_adds_nothing(self, value):
        subject = self.export_additional_info(value)

        assert objects(self.graph, subject, RDFS.comment) == []


class TestDatasetAdditionalInfo(MultiValueText):
    def export_additional_info(self, value):
        self.export(additional_info=value)
        return self.ref


class TestResourceAdditionalInfo(MultiValueText):
    def export_additional_info(self, value):
        self.export(resources=[resource(additional_info=value)])
        return self.distribution


class TestDataServiceAdditionalInfo(MultiValueText):
    dataset_type = 'dataservice'

    def export_additional_info(self, value):
        self.export(additional_info=value)
        return self.ref


@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
class TestConfiguredProfileChain(object):
    """The configured profiles run together, as the DCAT export endpoints do."""

    @pytest.fixture(autouse=True)
    def setup(self, clean_db, with_request_context):
        g.user = ''
        g.userobj = None

    def serialize(self, dataset, **fields):
        serializer = RDFSerializer(dataset_type=dataset.type)
        ref = serializer.graph_from_dataset(dataset_dict(dataset, **fields))
        return serializer.g, ref

    def test_chain_is_euro_then_qdes(self):
        assert config.get('ckanext.dcat.rdf.profiles').split() == ['euro_dcat_ap', 'qdes_dcat']

    def test_dataset_text_is_one_literal(self):
        dataset = make_dataset('chain-dataset')
        graph, ref = self.serialize(
            dataset, notes=PROSE, rights_statement=RIGHTS, resources=[resource(description=PROSE)]
        )
        [distribution] = graph.objects(ref, DCAT.distribution)

        assert objects(graph, ref, DCTERMS.description) == [PROSE]
        assert objects(graph, ref, DCTERMS.rights) == [RIGHTS]
        assert objects(graph, distribution, DCTERMS.description) == [PROSE]

    def test_dataservice_text_is_one_literal(self):
        dataservice = make_dataset('chain-dataservice', type='dataservice')
        graph, ref = self.serialize(dataservice, notes=PROSE, specialized_license=PROSE)

        assert objects(graph, ref, DCTERMS.description) == [PROSE]
        assert list(graph.objects(ref, ODRL.hasPolicy)) == [Literal(PROSE)]

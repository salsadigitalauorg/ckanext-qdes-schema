# encoding: utf-8
"""Integration tests for related dataset relationships (SUPDESQ-227).

Related datasets must be referenced by dataset id from the autocomplete through
to storage. Datasets are built directly in the model, because the QDES schema's
mandatory fields and secure vocabularies aren't needed to exercise relationships.
"""

import contextlib
import json
import signal

import pytest

import ckan.model as model
import ckan.tests.factories as factories

from ckan.plugins.toolkit import get_action
from ckanext.qdes_schema import helpers
from ckanext.relationships.helpers import get_subject_package_relationship_objects

# This distribution enforces a stricter password policy than CKAN core's test
# factories generate.
TEST_PASSWORD = 'TestPassw0rd!23'


def make_dataset(name, **fields):
    dataset = model.Package(name=name, title=name.replace('-', ' ').title(), type='dataset', state='active', **fields)
    model.Session.add(dataset)
    model.Session.commit()
    return dataset


def add_relationship(subject, object_, relationship_type):
    """Store a relationship directly, bypassing validation, as pre-existing data."""
    model.Session.add(model.PackageRelationship(subject=subject, object=object_, type=relationship_type))
    model.Session.commit()


@contextlib.contextmanager
def fails_after(seconds):
    def timed_out(signum, frame):
        raise TimeoutError('still running after {0}s'.format(seconds))

    previous = signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def relationships(dataset):
    """The dataset's relationships as the edit form lists them."""
    return sorted(
        (r['type'], r.get('object'), r.get('comment')) for r in get_subject_package_relationship_objects(dataset.id)
    )


def existing_related_resources(dataset):
    """The existing-relationships form value, as the edit form renders it."""
    return helpers.convert_relationships_to_related_resources(get_subject_package_relationship_objects(dataset.id))


def related(resource_id, relationship):
    return {'resource': {'id': resource_id}, 'relationship': relationship}


def save_dataset(test_request_context, user, dataset, existing, new=None, series_or_collection=None):
    """Save the dataset edit form: what `after_dataset_update` does for a web form save."""
    pkg_dict = {'id': dataset.id, 'type': 'dataset', 'related_resources': json.dumps(new) if new else ''}
    if series_or_collection:
        pkg_dict['series_or_collection'] = json.dumps(series_or_collection)
    context = {
        'model': model,
        'session': model.Session,
        'user': user['name'],
        'auth_user_obj': model.User.get(user['name']),
    }
    with test_request_context(method='POST', data={'existing_related_resources': existing}):
        helpers.update_related_resources(context, pkg_dict, reconcile_relationships=True)


class FakeSolrQuery(object):
    """Stands in for Solr, which the test ini shares with the development site.

    Applies CKAN's default permission labels the way Solr's filter does.
    """

    def __init__(self, results):
        self.results = results

    def run(self, data_dict, permission_labels=None):
        def label(dataset):
            return 'member-{0}'.format(dataset.owner_org) if dataset.private else 'public'

        return {
            'results': [
                {'name': d.name, 'title': d.title}
                for d in self.results
                if permission_labels is None or label(d) in permission_labels
            ]
        }


@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context', 'without_search_indexing')
class TestDatasetAutocomplete(object):
    def test_results_include_the_dataset_id(self, monkeypatch):
        from ckan.lib import search

        first = make_dataset('first-dataset')
        second = make_dataset('second-dataset')
        monkeypatch.setattr(search, 'query_for', lambda _type: FakeSolrQuery([first, second]))
        sysadmin = factories.Sysadmin(password=TEST_PASSWORD)

        results = get_action('package_autocomplete')({'user': sysadmin['name']}, {'q': 'dataset'})

        assert [(r['id'], r['name']) for r in results] == [
            (first.id, 'first-dataset'),
            (second.id, 'second-dataset'),
        ]

    def test_private_datasets_stay_hidden_from_users_outside_their_organisation(self, monkeypatch):
        from ckan.lib import search

        organisation = factories.Organization()
        public = make_dataset('public-dataset', owner_org=organisation['id'])
        private = make_dataset('private-dataset', owner_org=organisation['id'], private=True)
        monkeypatch.setattr(search, 'query_for', lambda _type: FakeSolrQuery([public, private]))
        outsider = factories.User(password=TEST_PASSWORD)

        results = get_action('package_autocomplete')({'user': outsider['name']}, {'q': 'dataset'})

        assert [r['name'] for r in results] == ['public-dataset']

    def test_results_for_datasets_missing_from_the_database_are_dropped(self, monkeypatch):
        from ckan.lib import search

        current = make_dataset('current-dataset')
        # A stale index entry: renamed or purged without a reindex.
        stale = model.Package(name='renamed-dataset', title='Renamed Dataset', private=False)
        monkeypatch.setattr(search, 'query_for', lambda _type: FakeSolrQuery([current, stale]))
        sysadmin = factories.Sysadmin(password=TEST_PASSWORD)

        results = get_action('package_autocomplete')({'user': sysadmin['name']}, {'q': 'dataset'})

        assert [r['name'] for r in results] == ['current-dataset']


@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context', 'without_search_indexing')
class TestSaveRelatedDatasets(object):
    @pytest.fixture(autouse=True)
    def setup(self, clean_db, test_request_context):
        self.request_context = test_request_context
        self.user = factories.Sysadmin(password=TEST_PASSWORD)
        self.subject = make_dataset('subject-dataset')
        self.target = make_dataset('target-dataset')

    def save(self, new=None, existing=None, series_or_collection=None):
        if existing is None:
            existing = existing_related_resources(self.subject)
        save_dataset(self.request_context, self.user, self.subject, existing, new, series_or_collection)

    def test_resaving_unchanged_keeps_one_relationship(self):
        self.save(new=[related(self.target.id, 'Is Part Of')], existing='')

        self.save()
        self.save()

        assert relationships(self.subject) == [('Is Part Of', self.target.id, None)]

    def test_removing_a_relationship_deletes_it(self):
        other = make_dataset('other-dataset')
        self.save(new=[related(self.target.id, 'Is Part Of'), related(other.id, 'References')], existing='')

        self.save(existing=json.dumps([related(other.id, 'References')]))

        assert relationships(self.subject) == [('References', other.id, None)]

    def test_removing_and_readding_in_one_save_keeps_one_relationship(self):
        self.save(new=[related(self.target.id, 'Is Part Of')], existing='')

        self.save(new=[related(self.target.id, 'Is Part Of')], existing='')

        assert relationships(self.subject) == [('Is Part Of', self.target.id, None)]

    def test_external_uri_relationship_survives_resave(self):
        uri = 'https://example.com/dataset/external'
        self.save(new=[related(uri, 'References')], existing='')

        self.save()

        assert relationships(self.subject) == [('References', None, uri)]

    def test_series_or_collection_survives_resave(self):
        series = [{'id': self.target.id, 'text': self.target.title}]
        self.save(series_or_collection=series, existing='')

        self.save(series_or_collection=series)

        assert relationships(self.subject) == [('Is Part Of', self.target.id, None)]

    def test_circular_replaces_relationship_is_not_created(self):
        save_dataset(self.request_context, self.user, self.target, '', [related(self.subject.id, 'Replaces')])

        self.save(new=[related(self.target.id, 'Replaces')], existing='')

        assert relationships(self.subject) == []

    def test_unknown_dataset_id_is_not_stored_as_an_external_uri(self):
        purged_dataset_id = 'b1a3c5d7-0000-4000-8000-000000000000'

        self.save(existing=json.dumps([related(purged_dataset_id, 'Is Part Of')]))

        assert relationships(self.subject) == []

    def test_existing_replaces_cycle_elsewhere_does_not_hang_the_save(self):
        first = make_dataset('first-dataset')
        second = make_dataset('second-dataset')
        add_relationship(first, second, 'Replaces')
        add_relationship(second, first, 'Replaces')

        with fails_after(30):
            self.save(new=[related(first.id, 'Replaces')], existing='')

        assert relationships(self.subject) == [('Replaces', first.id, None)]

    def test_circular_replaces_behind_a_second_branch_is_not_created(self):
        model.Session.add(
            model.PackageRelationship(
                subject=self.target, object=None, type='Replaces', comment='https://example.com/dataset/older'
            )
        )
        model.Session.commit()
        add_relationship(self.target, self.subject, 'Replaces')

        self.save(new=[related(self.target.id, 'Replaces')], existing='')

        assert relationships(self.subject) == []

# encoding: utf-8
import pytest
import redis


@pytest.fixture(autouse=True, scope='session')
def _copyable_redis_client():
    """Allow CKAN's `ckan_config` fixture to copy the application config.

    CKAN stores a live Redis client in `SESSION_REDIS`, and the `ckan_config`
    fixture that `with_plugins` depends on deepcopies the config. A Redis
    client holds a thread lock and cannot be deepcopied, so copying yields the
    same client.
    """
    if not hasattr(redis.Redis, '__deepcopy__'):
        redis.Redis.__deepcopy__ = lambda self, memo: self
    yield


@pytest.fixture
def clean_db(reset_db, migrate_db_for, with_plugins):
    """Reset the database, refusing to run against a non-test database.

    CKAN's own `clean_db` drops and recreates every table in whatever database
    `sqlalchemy.url` names, so a run with the development ini would destroy
    local data.
    """
    # Imported lazily: importing ckan.common at module scope triggers CKAN's
    # environment bootstrap, which fails when the unit suite runs with
    # `-p no:ckan`.
    from ckan.common import config

    url = config.get('sqlalchemy.url') or ''
    database = url.rsplit('/', 1)[-1].split('?')[0]
    if 'test' not in database:
        pytest.fail(
            'Refusing to reset database "{0}": it is not a test database and '
            'resetting it would destroy local development data. Run with a '
            'ckan ini whose sqlalchemy.url names a test database.'.format(database)
        )
    reset_db()
    # `reset_db` only creates CKAN core's tables; any action that writes an
    # activity record needs the activity plugin's migrations too.
    migrate_db_for('activity')


@pytest.fixture
def without_search_indexing(monkeypatch):
    """Stop dataset commits from being indexed.

    `ckan.pytest.ini` shares the development Solr core, so indexing test
    datasets would pollute the local site's search results.
    """
    from ckan.lib import search

    monkeypatch.setattr(search.SynchronousSearchPlugin, 'notify', lambda self, entity, operation: None)

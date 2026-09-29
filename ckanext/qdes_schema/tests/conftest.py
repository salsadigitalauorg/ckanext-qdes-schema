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
def clean_index(reset_index):
    """Clear the search index, refusing to touch the development site's documents.

    Tests share the development Solr core. CKAN's `clean_index` deletes every
    document for the configured `ckan.site_id`, which `ahoy test-setup` sets
    to `ckan_test`.
    """
    from ckan.common import config

    site_id = config.get('ckan.site_id') or ''
    if 'test' not in site_id:
        pytest.fail(
            'Refusing to clear the search index for site_id "{0}": it is not a '
            'test site and would delete the development index. Run with a ckan '
            'ini whose ckan.site_id names a test site.'.format(site_id)
        )
    reset_index()


@pytest.fixture
def clean_redis(reset_redis):
    """Empty Redis, refusing to touch the database the development site uses.

    CKAN's `clean_redis` deletes every key in the configured Redis database.
    Locally that is database 0, shared with the development site's sessions and
    job queues, and the Lagoon image only provides one database. To clear test
    jobs, call `reset_redis('ckan:ckan_test:*')` instead.
    """
    from urllib.parse import urlparse

    from ckan.common import config

    database = urlparse(config.get('ckan.redis.url') or '').path.strip('/') or '0'
    if database == '0':
        pytest.fail(
            "Refusing to empty Redis database 0: the development site uses it. "
            "Use reset_redis('ckan:ckan_test:*') to clear only test job queues."
        )
    reset_redis()

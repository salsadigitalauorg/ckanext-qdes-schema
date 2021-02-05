import ckan.plugins.toolkit as toolkit
import click
import logging

from ckanext.qdes_schema import model
from pprint import pformat

log = logging.getLogger(__name__)


@click.command(u"publish-log-init-db")
def init_db_cmd():
    u"""
    Initialise the database tables required for publish_log
    """
    click.secho(u"Initializing publish_log table", fg=u"green")

    try:
        model.publish_log_table.create()
        click.secho(u"Table publish_log is setup", fg=u"green")
    except Exception as e:
        log.error(str(e))


def get_commands():
    return [init_db_cmd]

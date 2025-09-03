import click

from workflow.commands.assets import dlassets
from workflow.commands.celery import celery
from workflow.commands.db import db
from workflow.commands.webserver import webserver
from workflow.commands.workflows import workflow


@click.group()
def cli():
    """Celery workflow - Command Line Interface"""
    pass


cli.add_command(webserver)
cli.add_command(celery)
cli.add_command(workflow)
cli.add_command(db)
cli.add_command(dlassets)

from __future__ import absolute_import, unicode_literals

import logging

from celery import Celery
from celery.signals import task_postrun, task_prerun
from django.conf import settings
from django.db import connection


_l = logging.getLogger('workflow')

app = Celery('workflow')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


# app.autodiscover_tasks()


def schema_exists(schema_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = %s;
        """, [schema_name])
        return cursor.fetchone() is not None


# EXTREMELY IMPORTANT CODE
# DO NOT MODIFY IT
# IT SETS CONTEXT FOR SHARED WORKERS TO WORK WITH DIFFERENT SCHEMAS
# 2024-03-24 szhitenev
# ALL TASKS MUST BE PROVIDED WITH CONTEXT WITH space_code
@task_prerun.connect
def set_task_context(task_id, task, kwargs=None, **unused):
    _l.info(f"task_prerun.task {task}")

    context = kwargs.get('context')
    if context:
        if context.get('space_code'):

            if schema_exists(context.get('space_code')):

                space_code = context.get('space_code')
                with connection.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {space_code};")
                    _l.info(f"task_prerun.context {space_code}")
            else:  # REMOVE IN 1.9.0, PROBABLY SECURITY ISSUE
                with connection.cursor() as cursor:
                    cursor.execute(f"SET search_path TO public;")
        else:
            raise Exception('No space_code in context')
    else:
        raise Exception('No context in kwargs')


@task_postrun.connect
def cleanup(task_id, **kwargs):
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO public;")

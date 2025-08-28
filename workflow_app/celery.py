# from __future__ import absolute_import, unicode_literals

import logging

from celery import Celery
from celery.signals import setup_logging  # noqa
from django.conf import settings

_l = logging.getLogger("workflow")

print("Creating Celery app Instance...")

app = Celery("workflow")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")


@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig  # noqa
    from django.conf import settings  # noqa

    dictConfig(settings.LOGGING)


app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

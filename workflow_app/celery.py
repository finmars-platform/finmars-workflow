from __future__ import absolute_import, unicode_literals

import logging
import sys
from celery.signals import worker_init, beat_init
from celery import Celery
from django.conf import settings



_l = logging.getLogger('workflow')

print("Creating Celery app Instance...")

app = Celery('workflow')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@beat_init.connect
def configure_beat(**kwargs):
    from workflow.system import get_system_workflow_manager
    system_workflow_manager = get_system_workflow_manager()

    system_workflow_manager.init_periodic_tasks()
    kwargs['sender'].scheduler.setup_schedule()

# app.autodiscover_tasks()

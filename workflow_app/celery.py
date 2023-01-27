from __future__ import absolute_import, unicode_literals

from celery import Celery
from django.conf import settings

app = Celery('workflow')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)



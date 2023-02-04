import json
import logging

import requests
from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate

from workflow_app import settings

_l = logging.getLogger('workflow')


class WorkflowConfig(AppConfig):
    name = 'workflow'

    def ready(self):
        post_migrate.connect(self.bootstrap, sender=self)

    def bootstrap(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):

        _l.info("Bootstrapping Worflow Application")

        self.create_finmars_bot()

    def create_finmars_bot(self):

        from workflow.models import User

        try:

            user = User.objects.get(username='finmars_bot')

        except Exception as e:

            user = User.objects.create(username='finmars_bot', is_bot=True)

            _l.info("Finmars bot created")
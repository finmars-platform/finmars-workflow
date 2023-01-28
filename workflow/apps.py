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
        self.sync_users_at_authorizer_service()

    def create_finmars_bot(self):

        from workflow.models import User

        try:

            user = User.objects.get(username='finmars_bot')

        except Exception as e:

            user = User.objects.create(username='finmars_bot', is_bot=True)

            _l.info("Finmars bot created")

    def sync_users_at_authorizer_service(self):

        from workflow.models import User

        try:
            _l.info("sync_users_at_authorizer_service processing")

            headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

            data = {
                "base_api_url": settings.BASE_API_URL,
            }

            try:

                url = settings.AUTHORIZER_URL + '/backend-sync-users/'

                response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)
                _l.info(
                    "sync_users_at_authorizer_service backend-sync-users response.status_code %s" % response.status_code)
                # _l.info("sync_users_at_authorizer_service backend-sync-users response.text %s" % response.text)

                response_data = response.json()

                members = response_data['members']

                for member in members:

                    user = None
                    _member = None

                    try:

                        user = User.objects.get(username=member['username'])

                    except Exception as e:

                        user = User.objects.create(username=member['username'])

                        _l.info("User %s created " % member['username'])

            except Exception as e:
                _l.error("Could not sync users %s" % e)


        except Exception as e:
            _l.info("sync_users_at_authorizer_service error %s" % e)

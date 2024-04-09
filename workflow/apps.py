import logging

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db import connection
from django.db.models.signals import post_migrate

from workflow_app import settings

_l = logging.getLogger('workflow')


def get_current_search_path():
    with connection.cursor() as cursor:
        cursor.execute("SHOW search_path;")
        search_path = cursor.fetchone()
        return search_path[0] if search_path else None


class WorkflowConfig(AppConfig):
    name = 'workflow'

    def ready(self):
        post_migrate.connect(self.bootstrap, sender=self)

    def bootstrap(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):

        _l.info("Bootstrapping Workflow Application")

        self.create_space_if_not_exist()
        self.create_finmars_bot()

    def create_space_if_not_exist(self):

        from workflow.models import Space

        space_code = get_current_search_path()

        if space_code == 'public':
            space_code = 'space00000'

        try:
            space = Space.objects.get(space_code=space_code, name=space_code, realm_code=settings.REALM_CODE)
            _l.info("bootstrap.space_exists: %s " % space_code)
        except Space.DoesNotExist:
            space = Space.objects.create(space_code=space_code, name=space_code, realm_code=settings.REALM_CODE)
            _l.info("bootstrap.creating_new_space: %s " % space_code)

    def create_finmars_bot(self):

        from workflow.models import User

        try:

            user = User.objects.get(username='finmars_bot')

        except Exception as e:

            user = User.objects.create(username='finmars_bot', is_bot=True)

            _l.info("Finmars bot created")

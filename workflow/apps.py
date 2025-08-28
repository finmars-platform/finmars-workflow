import logging

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS, connection
from django.db.models.signals import post_migrate

from workflow_app import settings

_l = logging.getLogger("workflow")


def get_current_search_path():
    with connection.cursor() as cursor:
        cursor.execute("SHOW search_path;")
        search_path = cursor.fetchone()
        return search_path[0].replace('"$user", ', "") if search_path else None


class WorkflowConfig(AppConfig):
    name = "workflow"

    def ready(self):
        import sys  # noqa: PLC0415

        sys.stdout.close = lambda: (_ for _ in ()).throw(Exception("stdout close attempt detected"))

        if not ("makemigrations" in sys.argv or "migrate" in sys.argv or "migrate_all_schemes" in sys.argv):
            from workflow.system import get_system_workflow_manager  # noqa: PLC0415

            system_workflow_manager = get_system_workflow_manager()
            system_workflow_manager.register_workflows()
        else:
            _l.info("system_workflow_manager ignored - TEST MODE")

        post_migrate.connect(self.bootstrap, sender=self)

    def bootstrap(self, app_config, verbosity=2, using=DEFAULT_DB_ALIAS, **kwargs):
        try:
            _l.info("Bootstrapping Workflow Application")

            current_space_code = get_current_search_path()

            _l.info("bootstrap: Current search path: %s", current_space_code)

            self.create_space_if_not_exist()
            self.create_finmars_bot()

        except Exception as e:
            _l.info("bootstrap: failed: %e", e)

    def create_space_if_not_exist(self):
        from workflow.models import Space  # noqa: PLC0415

        space_code = get_current_search_path()

        if space_code == "public":
            space_code = "space00000"

        try:
            space = Space.objects.first()
            if not space:
                raise Space.DoesNotExist()
            space.space_code = space_code
            space.name = space_code
            space.realm_code = settings.REALM_CODE
            space.save()
            _l.info("bootstrap.space_exists: %s ", space_code)
        except Space.DoesNotExist:
            space = Space.objects.create(space_code=space_code, name=space_code, realm_code=settings.REALM_CODE)
            _l.info("bootstrap.creating_new_space: %s ", space_code)

    def create_finmars_bot(self):
        from workflow.models import User  # noqa: PLC0415

        try:
            user = User.objects.get(username="finmars_bot")

        except Exception as e:
            user = User.objects.create(username="finmars_bot", is_bot=True)  # noqa: F841

            _l.info("Finmars bot created %s", e)

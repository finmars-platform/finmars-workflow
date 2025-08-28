import os

from celery.utils.nodenames import default_nodename
from django.core.management import BaseCommand
from django.db import connection

__author__ = "szhitenev"

from workflow.system import get_system_workflow_manager
from workflow.utils import get_all_tenant_schemas

system_workflow_manager = get_system_workflow_manager()


class Command(BaseCommand):
    help = "Cancel Existing tasks"

    def handle(self, *args, **options):
        try:
            for schema in get_all_tenant_schemas():
                # Set the search path to the tenant's schema
                with connection.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {schema};")

                worker_name = default_nodename(os.getenv("WORKFLOW_WORKER_NAME"))

                self.stdout.write(f"Going to cancel tasks in {schema}")
                system_workflow_manager.cancel_all_existing_tasks(worker_name)

            # Optionally, reset the search path to default after migrating
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO public;")

        except Exception as e:
            print("cancel_existing_tasks error e %s ", e)

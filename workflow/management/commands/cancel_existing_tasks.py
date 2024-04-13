from django.core.management import BaseCommand
from django.db import connection

__author__ = 'szhitenev'

from workflow.utils import get_all_tenant_schemas


from workflow.system import get_system_workflow_manager
system_workflow_manager = get_system_workflow_manager()

class Command(BaseCommand):
    help = 'Cancel Existing tasks'

    def handle(self, *args, **options):
        try:

            for schema in get_all_tenant_schemas():
                self.stdout.write(self.style.SUCCESS(f"Applying migrations to {schema}..."))

            # Set the search path to the tenant's schema
            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema};")

                system_workflow_manager.register_workflows_all_schemas()

                self.stdout.write("Going to cancel tasks")
                system_workflow_manager.cancel_all_existing_tasks()

            # Optionally, reset the search path to default after migrating
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO public;")

        except Exception as e:
            print('cancel_existing_tasks error e %s ' % e)

from django.core.management import BaseCommand
from django.db import connection

__author__ = 'szhitenev'

def get_all_tenant_schemas():
    # List to hold tenant schemas
    tenant_schemas = []

    # SQL to fetch all non-system schema names
    # ('pg_catalog', 'information_schema', 'public') # do later in 1.9.0. where is not public schemes left
    sql = """
    SELECT schema_name
    FROM information_schema.schemata
    WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
    AND schema_name NOT LIKE 'pg_toast%'
    AND schema_name NOT LIKE 'pg_temp_%'
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        tenant_schemas = [row[0] for row in cursor.fetchall()]

    return tenant_schemas


class Command(BaseCommand):
    help = 'Cancel Existing tasks'

    def handle(self, *args, **options):
        try:
            from workflow.celery_workflow import CeleryWorkflow
            from workflow.celery_workflow import cancel_existing_tasks

            for schema in get_all_tenant_schemas():
                self.stdout.write(self.style.SUCCESS(f"Applying migrations to {schema}..."))

            # Set the search path to the tenant's schema
            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema};")

                celery_workflow = CeleryWorkflow()

                celery_workflow.load_all_workflows()

                self.stdout.write("Going to cancel tasks")
                celery_workflow.cancel_all_existing_tasks()

            # Optionally, reset the search path to default after migrating
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO public;")

        except Exception as e:
            print('cancel_existing_tasks error e %s ' % e)

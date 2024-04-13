from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

from workflow.system import get_system_workflow_manager
system_workflow_manager = get_system_workflow_manager()


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
    help = "Sync all workflows from all Spaces in realm to local file storage."

    def handle(self, *args, **options):

        system_workflow_manager.sync_remote_storage_to_local_storage_all_schemas()

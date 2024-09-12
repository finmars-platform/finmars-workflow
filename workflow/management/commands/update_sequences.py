from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import AutoField

from workflow.utils import get_all_tenant_schemas


class Command(BaseCommand):
    help = "Repair autoincrement primary keys sequence to be greater than max id"

    def handle(self, *args, **options):
        models = apps.get_models()

        for schema in get_all_tenant_schemas():
            # Set the search path to the tenant's schema
            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema};")

                for model in models:
                    if not model._meta.managed:
                        continue

                    table_name = model._meta.db_table
                    primary_key_field = model._meta.pk
                    if not isinstance(primary_key_field, AutoField):
                        continue

                    primary_key_column = primary_key_field.column
                    cursor.execute(
                        f"SELECT MAX({primary_key_column}) FROM {table_name}"
                    )
                    max_id = cursor.fetchone()[0] or 0

                    cursor.execute(
                        f"""SELECT distinct seq.relname AS sequence_name
                                        FROM pg_class AS seq
                                        JOIN pg_depend AS dep ON seq.oid = dep.objid
                                        JOIN pg_class AS tab ON dep.refobjid = tab.oid
                                        JOIN pg_attribute AS attr ON attr.attnum = dep.refobjsubid
                                        JOIN pg_namespace AS ns ON tab.relnamespace = ns.oid
                                        WHERE seq.relkind = 'S'
                                          AND tab.relname = '{table_name}' and ns.nspname = '{schema}'"""
                    )
                    sequence_name = cursor.fetchone()[0]
                    cursor.execute(
                        f"""SELECT COUNT(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                                        WHERE c.relkind = 'S' AND c.relname = %s AND n.nspname = %s""",
                        [sequence_name, schema],
                    )
                    sequence_exists = cursor.fetchone()[0]
                    if not sequence_exists:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Sequence {sequence_name} does not exist for {schema}.{table_name}"
                            )
                        )
                        continue

                    cursor.execute(f"SELECT last_value FROM {sequence_name}")
                    last_id = cursor.fetchone()[0]

                    if max_id >= last_id:
                        cursor.execute(
                            f"SELECT setval('{sequence_name}', {max_id+1}, false)"
                        )
                        self.stdout.write(
                            f"Updated sequence {schema}.{sequence_name} to {max_id+1}"
                        )

        self.stdout.write(
            self.style.SUCCESS("Successfully updated sequences where necessary")
        )

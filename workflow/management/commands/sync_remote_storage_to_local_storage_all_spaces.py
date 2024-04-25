from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

from workflow.system import get_system_workflow_manager
system_workflow_manager = get_system_workflow_manager()


class Command(BaseCommand):
    help = "Sync all workflows from all Spaces in realm to local file storage."

    def handle(self, *args, **options):
        system_workflow_manager.sync_remote_storage_to_local_storage()

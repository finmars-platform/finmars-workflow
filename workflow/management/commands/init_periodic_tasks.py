from django.core.management import BaseCommand

__author__ = 'szhitenev'


from workflow.system import get_system_workflow_manager
system_workflow_manager = get_system_workflow_manager()


class Command(BaseCommand):
    help = 'Init Periodic tasks'

    def handle(self, *args, **options):
        try:
            system_workflow_manager.register_workflows()
            system_workflow_manager.init_periodic_tasks()
        except Exception as e:
            print('init_periodic_tasks error e %s ' % e)

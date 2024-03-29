from django.core.management import BaseCommand

__author__ = 'szhitenev'


class Command(BaseCommand):
    help = 'Cancel Existing tasks'

    def handle(self, *args, **options):
        try:
            from workflow.celery_workflow import CeleryWorkflow
            from workflow.celery_workflow import cancel_existing_tasks
            celery_workflow = CeleryWorkflow()

            celery_workflow.load_all_workflows()

            self.stdout.write("Going to cancel tasks")
            celery_workflow.cancel_all_existing_tasks()
        except Exception as e:
            print('cancel_existing_tasks error e %s ' % e)

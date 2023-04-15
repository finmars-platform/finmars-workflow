from django.core.management import BaseCommand

__author__ = 'szhitenev'


class Command(BaseCommand):
    help = 'Cancel Existing tasks'

    def handle(self, *args, **options):
        try:
            from workflow.celery_workflow import CeleryWorkflow
            from workflow.celery_workflow import cancel_existing_tasks
            celery_workflow = CeleryWorkflow()

            celery_workflow.init_app()

            self.stdout.write("Going to cancel tasks")
            cancel_existing_tasks()
        except Exception as e:
            print('cancel_existing_tasks error e %s ' % e)

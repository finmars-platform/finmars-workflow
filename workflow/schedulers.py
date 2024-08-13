from django_celery_beat.schedulers import ModelEntry, DatabaseScheduler as DCBScheduler
from workflow.models import Schedule


class DatabaseScheduler(DCBScheduler):
    Model = Schedule

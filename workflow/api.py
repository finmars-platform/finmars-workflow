
from workflow.tasks.base import BaseTask
from functools import partial

from workflow_app import celery_app

task = partial(celery_app.task, base=BaseTask)
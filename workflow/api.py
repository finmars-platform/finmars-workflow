
from workflow.tasks.base import BaseTask
from functools import partial

from workflow_app import celery_app
from functools import wraps

def task(*task_args, **task_kwargs):
    def decorator(func):

        from workflow.models import Space
        space = Space.objects.all().first()

        # Prepend the prefix to the original task name
        original_name = task_kwargs.get('name', func.__name__)
        prefixed_name = f"{space.space_code}.{original_name}"
        task_kwargs['name'] = prefixed_name
        task_kwargs['base'] = BaseTask # Extremely important, never forget to replace BaseTask

        # Register the function as a Celery task with the updated name
        task = celery_app.task(*task_args, **task_kwargs)(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return task(*args, **kwargs)

        return wrapper


    return decorator

# task = partial(celery_app.task, base=BaseTask)
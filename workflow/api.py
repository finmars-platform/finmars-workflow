from functools import partial, wraps
from threading import local

from workflow.tasks.base import BaseTask

_registered_task = local()


def get_registered_task():
    return getattr(_registered_task, "func", None)


def clear_registered_task():
    if hasattr(_registered_task, "func"):
        del _registered_task.func


def task(*task_args, **task_kwargs):
    def decorator(func):
        from workflow.models import Space

        space = Space.objects.all().first()

        # Prepend the prefix to the original task name
        original_name = task_kwargs.get("name", func.__name__)
        prefixed_name = f"{space.space_code}.{original_name}"

        _registered_task.func = partial(func, **task_kwargs)
        _registered_task.func.__name__ = func.__name__

        task_kwargs["name"] = prefixed_name
        task_kwargs["base"] = (
            BaseTask  # Extremely important, never forget to replace BaseTask
        )

        # Register the function as a Celery task with the updated name
        # task = celery_app.task(*task_args, **task_kwargs)(execute_workflow_step)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


# task = partial(celery_app.task, base=BaseTask)

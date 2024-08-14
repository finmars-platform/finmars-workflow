import time
import traceback

from celery import chain
from celery.utils import uuid
from celery.utils.log import get_task_logger
from django.db import connection

from workflow.models import Task, Workflow, User, Space
from workflow.tasks.base import BaseTask
from workflow.utils import schema_exists, set_schema_from_context
from workflow_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(bind=True)
def ping(self):
    # type: () -> str
    """Simple task that just returns 'pong'."""
    return "pong"


@celery_app.task(bind=True)
def start(self, workflow_id, *args, **kwargs):

    context = kwargs.get('context')
    set_schema_from_context(context)

    logger.info(f"Opening the workflow {workflow_id}")
    workflow = Workflow.objects.get(id=workflow_id)

    workflow.status = Workflow.STATUS_PROGRESS
    workflow.save()


@celery_app.task(bind=True)
def end(self, workflow_id, *args, **kwargs):
    # Waiting for the workflow status to be marked in error if a task failed
    time.sleep(0.5)

    context = kwargs.get('context')
    set_schema_from_context(context)

    logger.info(f"Closing the workflow {workflow_id}")
    workflow = Workflow.objects.get(id=workflow_id)

    if workflow.status != Workflow.STATUS_ERROR:
        workflow.status = Workflow.STATUS_SUCCESS
        workflow.save()


@celery_app.task(bind=True)
def mark_as_canceled_init_tasks(self, workflow_id, *args, **kwargs):
    logger.info(f"Mark as cancelled pending tasks of the workflow {workflow_id}")

    context = kwargs.get('context')
    set_schema_from_context(context)

    tasks = Task.objects.filter(workflow_id=workflow_id, status=Task.STATUS_INIT)
    for task in tasks:
        task.status = Task.STATUS_CANCELED
        task.mark_task_as_finished()
        task.save()


@celery_app.task(bind=True)
def failure_hooks_launcher(self, workflow_id, queue, tasks_names, payload, *args, **kwargs):
    logger.info('failure_hooks_launcher %s' % workflow_id)

    context = kwargs.get('context')
    set_schema_from_context(context)

    canvas = []

    for task_name in tasks_names:
        task_id = uuid()

        # We create the Celery task specifying its UID
        signature = celery_app.tasks.get(task_name).subtask(
            kwargs={"workflow_id": workflow_id, "payload": payload, "context": context},
            queue='workflow',
            task_id=task_id,
        )

        # workflow task has the same UID
        task = Task(
            celery_task_id=task_id,
            name=task_name,
            workflow_id=workflow_id,
            status=Task.STATUS_INIT,
            is_hook=True,
        )
        task.save()

        logger.info('failure_hooks_launcher.task %s' % task)

        canvas.append(signature)

    canvas = chain(*canvas, task_id=uuid())

    result = canvas.apply_async()

    if result.ready():
        try:
            result.get()
        except Exception as e:
            logger.error("failure_hooks_launcher.result.get e %s" % e)
            pass

    logger.info("Going to cancel init tasks")

    task_id = uuid()
    signature_mark_as_canceled = celery_app.tasks.get(
        "workflow.tasks.workflows.mark_as_canceled_init_tasks"
    ).subtask(
        kwargs={"workflow_id": workflow_id},
        queue='workflow',
        task_id=task_id,
    )

    logger.info('signature_mark_as_canceled %s' % signature_mark_as_canceled)

    signature_mark_as_canceled.apply_async()


@celery_app.task(bind=True)
def execute(self, user_code, payload, is_manager, *args, **kwargs):
    from workflow.system import get_system_workflow_manager
    manager = get_system_workflow_manager()

    try:

        logger.info("periodic.execute %s" % user_code)

        context = kwargs.get('context')

        set_schema_from_context(context)

        finmars_bot = User.objects.get(username='finmars_bot')
        space = Space.objects.get(space_code=context.get('space_code'))

        c_obj = Workflow(owner=finmars_bot, space=space, user_code=user_code, payload=payload, periodic=True,
                         is_manager=is_manager)
        c_obj.save()

        manager.get_by_user_code(user_code, sync_remote=True)

        # Build the workflow and execute it
        from workflow.builder import WorkflowBuilder
        workflow = WorkflowBuilder(c_obj.id)
        workflow.run()

        c_obj_dict = c_obj.to_dict()
        #
        # # Force commit before ending the function to ensure the ongoing transaction
        # # does not end up in a "idle in transaction" state on PostgreSQL
        # c_obj.commit()

        return c_obj_dict

    except Exception as e:
        logger.error('periodic task error: %s' % e, exc_info=True)


@celery_app.task(bind=True, base=BaseTask)
def execute_workflow_step(self, *args, **kwargs):
    from workflow.api import get_registered_task, clear_registered_task
    from workflow.system import get_system_workflow_manager

    clear_registered_task()
    manager = get_system_workflow_manager()

    context = kwargs.get('context')
    set_schema_from_context(context)

    workflow = Workflow.objects.get(id=kwargs['workflow_id'])
    path = workflow.user_code[len(context['space_code'])+1:].replace('.', '/').replace(':', '/')
    module_path, _ = path.rsplit('/', maxsplit=1)
    manager.sync_remote_storage_to_local_storage_for_schema(module_path)
    manager.import_user_tasks(path, raise_exception=True)

    func = get_registered_task()
    if func:
        logger.info('executing %s', func.__name__)
        result = func(self, *args, **kwargs)
        return result
    else:
        raise Exception(f'no function to execute for {workflow.user_code}')

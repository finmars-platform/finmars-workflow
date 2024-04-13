import time
import traceback

from celery import chain
from celery.utils import uuid
from celery.utils.log import get_task_logger

from workflow.models import Task
from workflow.models import Workflow, User
from workflow_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(bind=True)
def ping(self):
    # type: () -> str
    """Simple task that just returns 'pong'."""
    return "pong"


@celery_app.task(bind=True)
def start(self, workflow_id, *args, **kwargs):
    logger.info(f"Opening the workflow {workflow_id}")
    workflow = Workflow.objects.get(id=workflow_id)

    workflow.status = Workflow.STATUS_PROGRESS
    workflow.save()


@celery_app.task(bind=True)
def end(self, workflow_id, *args, **kwargs):
    # Waiting for the workflow status to be marked in error if a task failed
    time.sleep(0.5)

    logger.info(f"Closing the workflow {workflow_id}")
    workflow = Workflow.objects.get(id=workflow_id)

    if workflow.status != Workflow.STATUS_ERROR:
        workflow.status = Workflow.STATUS_SUCCESS
        workflow.save()


@celery_app.task(bind=True)
def mark_as_canceled_init_tasks(self, workflow_id, *args, **kwargs):
    logger.info(f"Mark as cancelled pending tasks of the workflow {workflow_id}")
    tasks = Task.objects.filter(workflow_id=workflow_id, status=Task.STATUS_INIT)
    for task in tasks:
        task.status = Task.STATUS_CANCELED
        task.mark_task_as_finished()
        task.save()


@celery_app.task(bind=True)
def failure_hooks_launcher(self, workflow_id, queue, tasks_names, payload, *args, **kwargs):
    logger.info('failure_hooks_launcher %s' % workflow_id)

    canvas = []

    for task_name in tasks_names:
        task_id = uuid()

        # We create the Celery task specifying its UID
        signature = celery_app.tasks.get(task_name).subtask(
            kwargs={"workflow_id": workflow_id, "payload": payload},
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
    try:

        logger.info("periodic.execute %s" % user_code)

        finmars_bot = User.objects.get(username='finmars_bot')

        c_obj = Workflow(owner=finmars_bot, user_code=user_code, payload=payload, periodic=True, is_manager=is_manager)
        c_obj.save()

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
        logger.error('execute e %s' % e)
        logger.error('execute traceback %s' % traceback.format_exc())

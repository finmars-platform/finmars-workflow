from celery import Task as _Task
from celery.signals import task_prerun, task_postrun, task_failure, task_internal_error
from celery.exceptions import TimeLimitExceeded, SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from django.db import connection
from django.utils.timezone import now

from workflow.models import Task, Workflow
from workflow.utils import (
    send_alert,
    schema_exists,
    set_schema_from_context,
    get_next_node_by_condition,
)
from workflow_app import celery_app

logger = get_task_logger(__name__)


# EXTREMELY IMPORTANT CODE
# DO NOT MODIFY IT
# IT SETS CONTEXT FOR SHARED WORKERS TO WORK WITH DIFFERENT SCHEMAS
# 2024-03-24 szhitenev
# ALL TASKS MUST BE PROVIDED WITH CONTEXT WITH space_code
@task_prerun.connect
def workflow_prerun(task_id, task, sender, *args, **kwargs):
    ignored_tasks = ("workflow.tasks", "celery.")

    if task.name.startswith(ignored_tasks):
        return

    logger.info(f"task_prerun.task {task}")

    context = kwargs.get("context")
    if context:
        if context.get("space_code"):
            if schema_exists(context.get("space_code")):
                space_code = context.get("space_code")
                with connection.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {space_code};")
                    logger.info(f"task_prerun.context {space_code}")
            else:  # REMOVE IN 1.9.0, PROBABLY SECURITY ISSUE
                with connection.cursor() as cursor:
                    cursor.execute(f"SET search_path TO public;")
        else:
            raise Exception("No space_code in context")
    else:
        raise Exception("No context in kwargs")

    with celery_app.app.app_context():
        print("task_id %s" % task_id)

        task = Task.objects.get(celery_task_id=task_id)
        task.status = Task.STATUS_PROGRESS
        task.worker_name = sender.request.hostname
        task.save()
        logger.info(f"Task {task_id} is now in progress")


@task_postrun.connect
def cleanup(task_id, **kwargs):
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO public;")


@task_failure.connect
@task_internal_error.connect
def on_failure(task_id, exception, args, einfo, **kwargs):
    logger.info("task_failure.task_id: %s" % task_id)
    logger.info("task_failure.kwargs: %s" % kwargs["kwargs"])
    logger.info("task_failure.exception: %s" % exception)

    context = kwargs["kwargs"].get("context")
    set_schema_from_context(context)

    task = Task.objects.get(celery_task_id=task_id)
    workflow = Workflow.objects.get(id=task.workflow_id)

    if isinstance(exception, (TimeLimitExceeded, SoftTimeLimitExceeded)):
        workflow.status = Workflow.STATUS_TIMEOUT
        task.status = Task.STATUS_TIMEOUT
    else:
        workflow.status = Workflow.STATUS_ERROR
        task.status = Task.STATUS_ERROR

    task.result = {"exception": str(exception), "traceback": einfo.traceback}
    task.error_message = str(exception)
    task.mark_task_as_finished()

    task.save()
    workflow.save()

    if task.workflow.parent:
        logger.info(
            f"task_failureWorkflow has a parent with ID {task.workflow.parent.id}. Triggering next task."
        )
        parent_workflow = task.workflow.parent

        parent_task = Task.objects.get(
            workflow=parent_workflow,
            node_id=task.workflow.node_id,
            space=task.workflow.space,
        )

        parent_task.status = Task.STATUS_ERROR
        on_failure(parent_task.celery_task_id, exception, args, einfo, **kwargs)

    send_alert(workflow)
    logger.info(f"Task {task_id} is now in error")


# @task_postrun.connect
# def close_session(*args, **kwargs):
#     # Flask SQLAlchemy will automatically create new sessions for you from
#     # a scoped session factory, given that we are maintaining the same app
#     # context, this ensures tasks have a fresh session (e.g. session errors
#     # won't propagate across tasks)
#     db.session.remove()


class BaseTask(_Task):
    def update_progress(self, progress):
        task = Task.objects.get(id=self.task.id)

        task.progress = progress

        task.save()

    """
    We need this method to prevent periodic worfklow overlap
    e.g. workflow execution time is about 2 hours
    but periodic runs it every hour
    
    00:00 - Run workflow (1)
    01:00 - Run workflow (2) - it will be exited, because workflow (1) is still running
    01:30 - Finished Workflow (1)
    02:00 - Run Workflow (3) It will run, because no active workflow at the moment
    02:40 - Finish Workflow (3) - Workflow was super fast and ended before next one
    03:00 - Run Workflow (4) - It will run, because previous one finished quicker before schedule
    
    """

    def log(self, message):
        # Append the message to the task's log

        if not self.task.log:
            self.task.log = ""

        self.task.log = self.task.log + str(message) + "\n"
        self.task.save()

    def is_workflow_already_running(self, workflow_user_code):
        # Works great for everything except first task inside actual running workflow
        is_running = False

        # Workflow (1) started - worfklow_id generated - it has status progress
        # Workflow (1) has first task in it with is_workflow_already_running check
        # It return true, because Workflow (1) is in progress indeed, and stop working
        # But it should work, because this is a task inside Running Workflow
        # is_workflow_already_running should prevent from executuon in Workflow (2) and so on
        # thats why we have exclude clause

        running_workflows_count = (
            Workflow.objects.exclude(id__in=[self.task.workflow_id])
            .filter(user_code=workflow_user_code, status=Workflow.STATUS_PROGRESS)
            .count()
        )

        if running_workflows_count > 0:
            is_running = True

        return is_running

    def before_start(self, task_id, args, kwargs):
        logger.info("BaseTask.before_start.task_id %s" % task_id)
        logger.info("BaseTask.before_start.kwargs: %s" % kwargs)

        context = kwargs.get("context")
        set_schema_from_context(context)

        task = Task.objects.get(celery_task_id=task_id)
        task.status = Task.STATUS_PROGRESS
        task.worker_name = self.request.hostname
        task.save()

        workflow = Workflow.objects.get(id=task.workflow_id)

        self.task = task
        self.workflow = workflow

        logger.info(f"Task {task_id} is now in progress")
        super(BaseTask, self).before_start(task_id, args, kwargs)

    def on_success(self, retval, task_id, args, kwargs):
        super(BaseTask, self).on_success(retval, task_id, args, kwargs)

        logger.info("BaseTask.on_success.task_id %s" % task_id)
        logger.info("BaseTask.on_success.kwargs: %s" % kwargs)

        context = kwargs.get("context")
        set_schema_from_context(context)

        task = Task.objects.get(celery_task_id=task_id)

        task.handle_task_success(retval)

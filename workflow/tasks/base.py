from celery import Task as _Task
from celery.signals import task_prerun
from celery.utils.log import get_task_logger

from workflow.models import Task, Workflow
from workflow.utils import send_alert
from workflow_app import celery_app

logger = get_task_logger(__name__)


@task_prerun.connect
def workflow_prerun(task_id, task, *args, **kwargs):
    ignored_tasks = ("workflow.tasks", "celery.")

    if task.name.startswith(ignored_tasks):
        return

    with celery_app.app.app_context():
        print('task_id %s' % task_id)

        task = Task.objects.get(celery_task_id=task_id)
        task.status = Task.STATUS_PROGRESS
        task.save()
        logger.info(f"Task {task_id} is now in progress")


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

    def is_workflow_already_running(self, workflow_user_code):
        is_running = False

        running_workflows_count = Workflow.objects.filter(user_code=workflow_user_code,
                                                          status=Workflow.STATUS_PROGRESS).count()

        if running_workflows_count > 0:
            is_running = True

        return is_running

    def before_start(self, task_id, args, kwargs):
        task = Task.objects.get(celery_task_id=task_id)
        task.status = Task.STATUS_PROGRESS
        task.save()

        workflow = Workflow.objects.get(id=task.workflow_id)

        self.task = task
        self.workflow = workflow

        logger.info(f"Task {task_id} is now in progress")
        super(BaseTask, self).before_start(task_id, args, kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        task = Task.objects.get(celery_task_id=task_id)
        task.status = Task.STATUS_ERROR
        task.result = {"exception": str(exc), "traceback": einfo.traceback}
        task.error_message = str(exc)
        task.save()

        workflow = Workflow.objects.get(id=task.workflow_id)
        workflow.status = Workflow.STATUS_ERROR
        workflow.save()

        send_alert(workflow)

        logger.info(f"Task {task_id} is now in error")
        super(BaseTask, self).on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        task = Task.objects.get(celery_task_id=task_id)
        task.status = Task.STATUS_SUCCESS
        task.result = retval
        task.save()

        logger.info(f"Task {task_id} is now in success. Retval {retval}")
        super(BaseTask, self).on_success(retval, task_id, args, kwargs)

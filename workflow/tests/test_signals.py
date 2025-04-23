import time
from django.test import TransactionTestCase, override_settings
from celery.contrib.testing.worker import start_worker
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils import uuid
from workflow.models import Space, Workflow, Task, User
from workflow_app import celery_app
from workflow.tasks.base import BaseTask


@override_settings(
    CELERY_BROKER_URL="memory://", CELERY_RESULT_BACKEND="cache+memory://"
)
class SignalsTest(TransactionTestCase):
    def setUp(self):
        space = Space.objects.first()
        task_id = uuid()
        self.workflow = Workflow.objects.create(
            space=space, owner=User.objects.first(), status=Workflow.STATUS_INIT
        )
        self.task = Task.objects.create(
            workflow=self.workflow,
            space=space,
            celery_task_id=task_id,
            status=Task.STATUS_INIT,
        )
        self.task_params = (), dict(context={"space_code": "public"}), task_id

    def test_task_success(self):
        @celery_app.task(bind=True, base=BaseTask)
        def task_success(self, *args, **kwargs):
            return "ok"

        with start_worker(celery_app, perform_ping_check=False):
            result = task_success.apply_async(*self.task_params)
            result.get()

        self.task.refresh_from_db()

        self.assertEqual(Task.STATUS_SUCCESS, self.task.status)

    def test_task_terminated(self):
        @celery_app.task(bind=True, base=BaseTask)
        def task_oom(self, *args, **kwargs):
            raise MemoryError()

        with start_worker(celery_app, perform_ping_check=False):
            result = task_oom.apply_async(*self.task_params)
            time.sleep(1)
            result.revoke()

        self.task.refresh_from_db()
        self.workflow.refresh_from_db()

        self.assertEqual(Task.STATUS_ERROR, self.task.status)
        self.assertEqual(Workflow.STATUS_ERROR, self.workflow.status)

    def test_task_timeout(self):
        @celery_app.task(bind=True, base=BaseTask)
        def task_timeout(self, *args, **kwargs):
            raise SoftTimeLimitExceeded()

        with start_worker(celery_app, perform_ping_check=False):
            result = task_timeout.apply_async(*self.task_params)
            time.sleep(1)
            result.revoke()

        self.task.refresh_from_db()
        self.workflow.refresh_from_db()

        self.assertEqual(Task.STATUS_TIMEOUT, self.task.status)
        self.assertEqual(Workflow.STATUS_TIMEOUT, self.workflow.status)

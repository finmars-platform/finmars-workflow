import logging

from celery import chain, group
from celery.utils import uuid

from workflow.exceptions import WorkflowSyntaxError
from workflow.models import Task, Workflow
from workflow.system import get_system_workflow_manager
from workflow.tasks.workflows import (
    end,
    execute_workflow_step,
    failure_hooks_launcher,
    start,
)
from workflow_app import celery_app

_l = logging.getLogger("workflow")


system_workflow_manager = get_system_workflow_manager()


class WorkflowBuilder(object):
    def __init__(self, workflow_id):
        self.workflow_id = workflow_id
        self._workflow = None

        self.queue = system_workflow_manager.get_queue(str(self.workflow))
        self.custom_queues = {}

        self.tasks = system_workflow_manager.get_tasks(str(self.workflow))

        self.imports = system_workflow_manager.get_imports(str(self.workflow))

        self.canvas = []

        self.failure_hook = system_workflow_manager.get_failure_hook_task(
            str(self.workflow)
        )
        self.failure_hook_canvas = []

        self.success_hook = system_workflow_manager.get_success_hook_task(
            str(self.workflow)
        )

        self.before_start_hook = system_workflow_manager.get_before_start_hook_task(
            str(self.workflow)
        )

        _l.info("self.success_hook %s" % self.success_hook)
        _l.info("self.before_start_hook %s" % self.before_start_hook)

        self.success_hook_canvas = []

        # Pointer to the previous task(s)
        self.previous = []

    @property
    def workflow(self):
        if not self._workflow:
            self._workflow = Workflow.objects.get(id=self.workflow_id)
        return self._workflow

    def new_task(self, task_name, is_hook, single=True):
        task_id = uuid()

        prefixed_name = self.workflow.space.space_code + "." + task_name

        queue = self.custom_queues.get(prefixed_name, self.queue)

        # We create the Celery task specifying its UID

        _l.info("WorkflowBuilder.celery_app.task_name %s" % prefixed_name)
        # _l.info('celery_app.tasks %s' % celery_app.tasks)
        _l.info("WorkflowBuilder.celery_app.backend %s" % celery_app.backend)

        signature = execute_workflow_step.subtask(
            kwargs={
                "workflow_id": self.workflow_id,
                "payload": self.workflow.payload,
                "context": {
                    "realm_code": self.workflow.space.realm_code,
                    "space_code": self.workflow.space.space_code,
                },
                "imports": self.imports,
            },
            queue=queue,
            task_id=task_id,
        )

        _l.info("self.previous %s" % self.previous)

        # workflow task has the same UID
        task = Task(
            celery_task_id=task_id,
            name=task_name,
            previous=self.previous,
            workflow_id=self.workflow.id,
            status=Task.STATUS_INIT,
            space=self._workflow.space,
            is_hook=is_hook,
        )
        task.save()

        _l.info("signature %s" % signature.id)

        if single:
            self.previous = [signature.id]

        return signature

    def parse_queues(self):
        if type(self.queue) is dict:
            self.custom_queues = self.queue.get("customs", {})
            self.queue = self.queue.get("default", "celery")
        if type(self.queue) is not str or type(self.custom_queues) is not dict:
            raise WorkflowSyntaxError()

    def parse(self, tasks, is_hook=False):
        canvas = []

        for task in tasks:

            if type(task) is str:
                signature = self.new_task(task, is_hook)
                canvas.append(signature)
            elif type(task) is dict:
                name = list(task)[0]
                if "type" not in task[name] and task[name]["type"] != "group":
                    raise WorkflowSyntaxError()

                sub_canvas_tasks = [
                    self.new_task(t, is_hook, single=False) for t in task[name]["tasks"]
                ]

                sub_canvas = group(*sub_canvas_tasks, task_id=uuid())
                canvas.append(sub_canvas)
                self.previous = [s.id for s in sub_canvas_tasks]
            else:
                raise WorkflowSyntaxError()

        return canvas

    def build(self):
        self.parse_queues()
        self.canvas = self.parse(self.tasks)
        if self.before_start_hook:
            initial_previous = self.previous
            self.previous = None
            self.before_start_hook_canvas = self.parse([self.before_start_hook], True)[
                0
            ]

            _l.info("self.before_start_hook_canvas %s" % self.before_start_hook_canvas)

            self.canvas.insert(
                0, self.before_start_hook_canvas.set(queue=self.queue)
            )  # insert before_start hook if exists

            self.previous = initial_previous

        self.canvas.insert(
            0,
            start.si(
                self.workflow.id,
                context={
                    "realm_code": self.workflow.space.realm_code,
                    "space_code": self.workflow.space.space_code,
                },
            ).set(queue=self.queue),
        )  # Workflow Start would be always first

        self.canvas.append(
            end.si(
                self.workflow.id,
                context={
                    "realm_code": self.workflow.space.realm_code,
                    "space_code": self.workflow.space.space_code,
                },
            ).set(queue=self.queue)
        )

    def build_hooks(self):
        initial_previous = self.previous

        if self.failure_hook and not self.failure_hook_canvas:
            self.previous = None
            self.failure_hook_canvas = [
                failure_hooks_launcher.si(
                    self.workflow.id,
                    self.queue,
                    [self.failure_hook],
                    self.workflow.payload,
                    context={
                        "realm_code": self.workflow.space.realm_code,
                        "space_code": self.workflow.space.space_code,
                    },
                ).set(queue=self.queue),
            ]

        if self.success_hook and not self.success_hook_canvas:
            # self.previous = None
            self.success_hook_canvas = [self.parse([self.success_hook], True)[0]]

        self.previous = initial_previous

    def run(self):

        _l.info("celery_app %s" % celery_app.backend)

        if not self.canvas:
            self.build()

        canvas = chain(*self.canvas, task_id=uuid())

        self.build_hooks()

        try:
            return canvas.apply_async(
                link=self.success_hook_canvas,
                link_error=self.failure_hook_canvas,
            )

        except Exception as e:
            _l.error("run.e %s" % e)
            self.workflow.status = Workflow.STATUS_ERROR
            self.workflow.save()
            raise e

    def cancel(self):
        status_to_cancel = set([Task.STATUS_PROGRESS])
        for task in self.workflow.tasks:
            if task.status in status_to_cancel:
                celery_app.control.revoke(task.celery_task_id, terminate=True)
                task.mark_task_as_finished()
                task.status = Task.STATUS_CANCELED
                task.save()
        self.workflow.status = Workflow.STATUS_CANCELED
        self.workflow.save()

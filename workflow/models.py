from __future__ import unicode_literals
from celery import schedules
import json

import pytz
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, connection
from django.utils.translation import gettext_lazy
from django_celery_beat.models import PeriodicTask, CrontabSchedule

from workflow.storage import get_storage
from workflow.utils import get_all_tenant_schemas, get_next_node_by_condition

LANGUAGE_MAX_LENGTH = 5
TIMEZONE_MAX_LENGTH = 20
TIMEZONE_CHOICES = sorted(list((k, k) for k in pytz.all_timezones))
TIMEZONE_COMMON_CHOICES = sorted(list((k, k) for k in pytz.common_timezones))

from django.utils.translation import gettext_lazy as _
from workflow_app import celery_app
from django.utils.timezone import now
from croniter import croniter
from datetime import datetime
import pytz

import logging

_l = logging.getLogger('workflow')

storage = get_storage()



class User(AbstractUser):
    language = models.CharField(max_length=LANGUAGE_MAX_LENGTH, default=settings.LANGUAGE_CODE,
                                verbose_name=gettext_lazy('language'))
    timezone = models.CharField(max_length=TIMEZONE_MAX_LENGTH, default=settings.TIME_ZONE,
                                verbose_name=gettext_lazy('timezone'))

    two_factor_verification = models.BooleanField(default=False, verbose_name=gettext_lazy('two factor verification'))

    json_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('json data'))

    is_verified = models.BooleanField(default=False, verbose_name=gettext_lazy('is verified'))

    password = models.CharField(_("password"), max_length=256)

    is_bot = models.BooleanField(default=False, verbose_name=gettext_lazy('is bot'))

    @property
    def data(self):
        if self.json_data:
            try:
                return json.loads(self.json_data)
            except (ValueError, TypeError):
                return None
        else:
            return None

    @data.setter
    def data(self, val):
        if val:
            self.json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.json_data = None


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False, db_index=True,
                                   verbose_name=gettext_lazy('created'))
    modified_at = models.DateTimeField(auto_now=True, editable=False, db_index=True,
                                    verbose_name=gettext_lazy('modified'))

    class Meta:
        abstract = True
        get_latest_by = 'modified_at'
        ordering = ['created_at', ]


class Space(TimeStampedModel):
    name = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=gettext_lazy('name'))

    realm_code = models.CharField(max_length=255, null=True, blank=True,
                                  verbose_name=gettext_lazy('realm_code'))

    space_code = models.CharField(max_length=255,
                                  verbose_name=gettext_lazy('space_code'))


class WorkflowTemplate(TimeStampedModel):

    name = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=gettext_lazy('name'))

    user_code = models.CharField(max_length=1024, null=True, blank=True,
                                 verbose_name=gettext_lazy('user_code'))

    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))

    data = models.JSONField(null=True, blank=True, verbose_name=gettext_lazy('data'))

    space = models.ForeignKey(Space, verbose_name=gettext_lazy('space'),
                              on_delete=models.CASCADE, related_name="workflow_templates")

    owner = models.ForeignKey(User, verbose_name=gettext_lazy('owner'),
                              on_delete=models.CASCADE, related_name="workflow_templates")



class Workflow(TimeStampedModel):
    STATUS_INIT = 'init'
    STATUS_PROGRESS = 'progress'
    STATUS_WAIT = 'wait'
    STATUS_SUCCESS = 'success'
    STATUS_ERROR = 'error'
    STATUS_TIMEOUT = 'timeout'
    STATUS_CANCELED = 'canceled'

    STATUS_CHOICES = (
        (STATUS_INIT, 'init'),
        (STATUS_PROGRESS, 'progress'),
        (STATUS_WAIT, 'wait'),
        (STATUS_SUCCESS, 'success'),
        (STATUS_ERROR, 'error'),
        (STATUS_TIMEOUT, 'timeout'),
        (STATUS_CANCELED, 'canceled')
    )

    name = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=gettext_lazy('name'))

    workflow_template = models.ForeignKey(WorkflowTemplate, null=True, verbose_name=gettext_lazy('template'),
                                 on_delete=models.CASCADE, related_name="workflows")

    current_node_id = models.CharField(max_length=255, null=True, blank=True)  # Store the current node ID
    last_task_output = models.JSONField(null=True, blank=True)  # New field for storing last output
    node_id = models.CharField(max_length=255, blank=True, null=True, help_text="Node ID from the workflow JSON structure")

    user_code = models.CharField(max_length=1024, null=True, blank=True,
                                 verbose_name=gettext_lazy('user_code'))

    status = models.CharField(null=True, max_length=255, default=STATUS_INIT, choices=STATUS_CHOICES,
                              verbose_name='status')
    payload_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('payload data'))
    periodic = models.BooleanField(default=False, verbose_name=gettext_lazy('periodic'))

    is_manager = models.BooleanField(default=False, verbose_name=gettext_lazy('is manager'))
    platform_task_id = models.IntegerField(null=True,
                                           help_text="Platform Task ID in case if Platform initiated some pipeline")

    space = models.ForeignKey(Space, verbose_name=gettext_lazy('space'),
                              on_delete=models.CASCADE, related_name="workflows")

    owner = models.ForeignKey(User, verbose_name=gettext_lazy('owner'),
                              on_delete=models.CASCADE, related_name="workflows")

    crontab = models.ForeignKey(CrontabSchedule, verbose_name=gettext_lazy('crontab'),
                                null=True, on_delete=models.SET_NULL, related_name="workflows")

    finished_at = models.DateTimeField(null=True, db_index=True,
                                       verbose_name=gettext_lazy('finished at'))

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        verbose_name=gettext_lazy("parent"),
        on_delete=models.SET_NULL,
    )

    class Meta:
        get_latest_by = 'modified'
        ordering = ['-created_at', 'id']

    @property
    def payload(self):
        if self.payload_data:
            try:
                return json.loads(self.payload_data)
            except (ValueError, TypeError):
                return {}
        else:
            return {}

    @payload.setter
    def payload(self, val):
        if val:
            self.payload_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.payload_data = None

    def __str__(self):
        return f"{self.user_code}"

    def __repr__(self):
        return f"<Workflow {self.user_code}>"

    def to_dict(self, with_payload=True):
        d = {}
        d.update(
            {
                "id": self.id,
                "name": self.name,
                "user_code": self.user_code,
                "status": self.status,
                "periodic": self.periodic,
            }
        )
        if with_payload:
            d["payload"] = self.payload
        return d

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.platform_task_id and \
           self.status in (self.STATUS_SUCCESS, self.STATUS_ERROR, self.STATUS_TIMEOUT, self.STATUS_CANCELED):

            from workflow.finmars import update_task_status
            try:
                error_task = self.tasks.filter(status=Task.STATUS_ERROR).first()
                if error_task:
                    update_task_status(self.platform_task_id, self.status, error=error_task.error_message)
                    return

                last_task = self.tasks.last()
                if last_task:
                    update_task_status(self.platform_task_id, self.status, result=last_task.result)
            except Exception as ex:
                _l.warning('update_task_status %s' % ex)

    def cancel(self):
        status_to_cancel = [Task.STATUS_PROGRESS]
        for task in self.tasks.all():
            if task.status in status_to_cancel:
                celery_app.control.revoke(task.celery_task_id, terminate=True)
                task.status = Task.STATUS_CANCELED
                task.mark_task_as_finished()
                task.save()
        self.status = Workflow.STATUS_CANCELED
        self.save()

    def run_new_workflow(self, user_code, payload={}):

        if not user_code:
            raise Exception("User code is required.")

        if not self.is_manager:
            raise Exception("Workflow is not manager. Can't run new workflow.")

        from workflow.system import get_system_workflow_manager
        from workflow.workflows import execute_workflow
        system_workflow_manager = get_system_workflow_manager()

        user_code = f'{self.space.space_code}.{user_code}'

        new_workflow = system_workflow_manager.get_by_user_code(user_code, sync_remote=True)

        is_manager = new_workflow['workflow'].get('is_manager', False)

        if is_manager:
            raise Exception("New Workflow is manager. Manager can't execute another manager")

        _l.info('run_new_workflow. Going to execute: %s', user_code)

        data = execute_workflow(self.owner.username, user_code, payload, self.space.realm_code, self.space.space_code)

        return data


class Task(TimeStampedModel):
    STATUS_INIT = 'init'
    STATUS_PROGRESS = 'progress'
    STATUS_NESTED_PROGRESS = 'nested-progress' # needed for nested progress
    STATUS_SUCCESS = 'success'
    STATUS_ERROR = 'error'
    STATUS_TIMEOUT = 'timeout'
    STATUS_CANCELED = 'canceled'

    STATUS_CHOICES = (
        (STATUS_INIT, 'INIT'),
        (STATUS_PROGRESS, 'PROGRESS'),
        (STATUS_NESTED_PROGRESS, 'nested-progress'),
        (STATUS_SUCCESS, 'SUCCESS'),
        (STATUS_ERROR, 'ERROR'),
        (STATUS_TIMEOUT, 'TIMEOUT'),
        (STATUS_CANCELED, 'CANCELED'),
    )

    workflow = models.ForeignKey(Workflow, verbose_name=gettext_lazy('workflow'),
                                 on_delete=models.CASCADE, related_name="tasks")

    node_id = models.CharField(max_length=255, blank=True, null=True, help_text="Node ID from the workflow JSON structure")

    celery_task_id = models.CharField(null=True, max_length=255)
    name = models.CharField(null=True, max_length=255)
    source_code = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('source code'))
    status = models.CharField(null=True, max_length=255, default=STATUS_INIT, choices=STATUS_CHOICES,
                              verbose_name='status')
    worker_name = models.CharField(null=True, max_length=255, verbose_name="worker name")
    type = models.CharField(max_length=50, blank=True, null=True)

    payload_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('payload data'))
    result_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('result data'))

    progress_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('progress data'))

    log = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('log'))

    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))
    error_message = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('error message'))

    verbose_name = models.CharField(null=True, max_length=255)
    verbose_result = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('verbose result'))

    previous_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('previous data'))

    is_hook = models.BooleanField(default=False, verbose_name=gettext_lazy('is hook'))

    finished_at = models.DateTimeField(null=True, db_index=True,
                                       verbose_name=gettext_lazy('finished at'))

    space = models.ForeignKey(Space, verbose_name=gettext_lazy('space'),
                              on_delete=models.CASCADE, related_name="tasks")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return '<Task: {0.pk} ({0.status})>'.format(self)

    @property
    def payload(self):
        if self.payload_data is None:
            return None
        return json.loads(self.payload_data)

    @payload.setter
    def payload(self, value):
        if value is None:
            self.payload_data = None
        else:
            self.payload_data = json.dumps(value, sort_keys=True, indent=1)

    @property
    def result(self):
        if self.result_data is None:
            return None
        return json.loads(self.result_data)

    @result.setter
    def result(self, value):
        if value is None:
            self.result_data = None
        else:
            self.result_data = json.dumps(value, sort_keys=True, indent=1)

    @property
    def progress(self):
        if self.progress_data is None:
            return None
        return json.loads(self.progress_data)

    @progress.setter
    def progress(self, value):
        if value is None:
            self.progress_data = None
        else:
            self.progress_data = json.dumps(value, sort_keys=True, indent=1)

    @property
    def previous(self):
        if self.previous_data is None:
            return None
        return json.loads(self.previous_data)

    @previous.setter
    def previous(self, value):
        if value is None:
            self.previous_data = None
        else:
            self.previous_data = json.dumps(value, sort_keys=True, indent=1)

    # def add_attachment(self, file_report_id):
    #
    #     CeleryTaskAttachment.objects.create(celery_task=self,
    #                                         file_report_id=file_report_id)

    def mark_task_as_finished(self):

        self.finished_at = now()

    def update_progress(self, progress):

        # {
        #   current: 20,
        #   total: 100,
        #   percent: 20
        #   description
        # }

        _l.info('update_progress %s' % progress)

        self.progress = progress

        self.save()


    def handle_task_success(self, retval):

        if self.status == Task.STATUS_NESTED_PROGRESS:
            _l.info(f"Task {self.id} is in STATUS_NESTED_PROGRESS status; waiting for nested workflow to complete.")
            # If the task status is STATUS_NESTED_PROGRESS, we should exit without marking it complete
            # It will be resumed by the nested workflow completion logic
            return

        self.status = Task.STATUS_SUCCESS
        if retval:
            self.result = retval
        else:
            self.result = {"message": "Task finished successfully. No results returned"}
        self.mark_task_as_finished()
        self.save()

        # if workflow version v2
        if self.workflow.workflow_template:
            from workflow.tasks.workflows import process_next_node

            workflow_data = self.workflow.workflow_template.data
            nodes = {node['id']: node for node in workflow_data['workflow']['nodes']}
            connections = workflow_data['workflow']['connections']

            adjacency_list = {node_id: [] for node_id in nodes}
            for connection in connections:
                adjacency_list[connection['source']].append(connection['target'])

            current_node_id = self.node_id
            current_node = nodes[current_node_id]

            self.workflow.last_task_output = retval
            self.workflow.current_node_id = current_node_id

            _l.info(f"Task {self.name} executed successfully, result: {retval}")

            next_node_ids = []
            if current_node['data']['node']['type'] == "condition":
                # Use the condition result to determine the next path
                _l.info(f"BaseTask.on_success.Processing conditional node {current_node_id}, result: {retval}")
                next_node_id = get_next_node_by_condition(current_node_id, retval, connections)
                if next_node_id:
                    next_node_ids.append(next_node_id)
            else:
                # Normal node, just proceed to the next nodes from adjacency list
                next_node_ids = adjacency_list.get(current_node_id, [])

            if not next_node_ids:
                _l.info(f"BaseTask.on_success.No next nodes found for current node ID: {current_node_id}. Marking workflow as complete.")

                _l.info(f'BaseTask.on_success.workflow owner {self.workflow.owner}')
                # If there are no next nodes, update the workflow status to SUCCESS
                self.workflow.status = Workflow.STATUS_SUCCESS
                self.workflow.finished_at =  now()
                self.workflow.save()
                _l.info(f"BaseTask.on_success.Workflow ID {self.workflow.id} status updated to SUCCESS.")

                if self.workflow.parent:

                    _l.info(f"BaseTask.on_success.Workflow has a parent with ID {self.workflow.parent.id}. Triggering next task.")
                    parent_workflow = self.workflow.parent

                    parent_task = Task.objects.get(workflow=parent_workflow, node_id=self.workflow.node_id, space=self.workflow.space)

                    parent_task.status = Task.STATUS_PROGRESS
                    parent_task.handle_task_success(retval)

                else:
                    return


            # Decide what the next step will be, based on the current task's output
            for next_node_id in next_node_ids:
                next_node = nodes.get(next_node_id)
                if not next_node:
                    _l.error(f"BaseTask.on_success.Next node with ID {next_node_id} does not exist in the workflow nodes.")
                    continue

                _l.info(f"BaseTask.on_success.Processing next node: {next_node_id}, Name: {next_node['name']}")

                # Check if the workflow is in WAIT state

                # Execute the next task recursively by calling `process_next_node` again
                process_next_node.apply_async(kwargs={
                    "current_node_id": next_node_id,
                    "workflow_id": self.workflow.id,
                    "nodes": nodes,
                    "adjacency_list": adjacency_list,
                    "context": {
                        "realm_code": self.workflow.space.realm_code,
                        "space_code": self.workflow.space.space_code,
                    },
                    "connections": connections
                }, queue="workflow")



class ScheduleManager(models.Manager):
    def enabled(self):
        result = []
        schemas = get_all_tenant_schemas()

        for schema in schemas:
            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema};")

            schema_schedules = list(self.filter(enabled=True).prefetch_related("crontab"))
            result.extend(schema_schedules)
        return result


class Schedule(PeriodicTask, TimeStampedModel):
    objects = ScheduleManager()

    user_code = models.TextField(verbose_name=gettext_lazy('user_code'))

    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))

    payload = models.JSONField(null=True, blank=True, verbose_name=gettext_lazy('payload'))

    is_manager = models.BooleanField(default=False, verbose_name=gettext_lazy('is manager'))

    space = models.ForeignKey(Space, verbose_name=gettext_lazy('space'),
                              on_delete=models.CASCADE, related_name="schedules")

    owner = models.ForeignKey(User, verbose_name=gettext_lazy('owner'),
                              on_delete=models.CASCADE, related_name="schedules")

    workflow_user_code = models.TextField(verbose_name=gettext_lazy('workflow_user_code'))

    @property
    def crontab_line(self) -> str | None:
        if self.crontab:
            return '{} {} {} {} {}'.format(
                self.crontab.minute, self.crontab.hour,
                self.crontab.day_of_month, self.crontab.month_of_year,
                self.crontab.day_of_week
            )

    @crontab_line.setter
    def crontab_line(self, value: str):
        minute, hour, day, month, weekday = value.split(' ')
        schedule = schedules.crontab(
            minute=minute,
            hour=hour,
            day_of_month=day,
            month_of_year=month,
            day_of_week=weekday
        )
        self.crontab = CrontabSchedule.from_schedule(schedule)

    def save(self, *args, **kwargs):
        self.queue = "workflow"
        self.task = "workflow.tasks.workflows.execute"
        space_user_code = f"{self.space.space_code}.{self.workflow_user_code}"
        if not self.name:
            self.name = f"periodic-{space_user_code}-{self.crontab_line}"
        self.args = json.dumps([space_user_code, self.payload, self.is_manager])
        self.crontab, _ = CrontabSchedule.objects.get_or_create(
            minute=self.crontab.minute,
            hour=self.crontab.hour,
            day_of_month=self.crontab.day_of_month,
            month_of_year=self.crontab.month_of_year,
            day_of_week=self.crontab.day_of_week
        )
        self.kwargs = json.dumps({
            "context": {"realm_code": self.space.realm_code, "space_code": self.space.space_code},
            "crontab_id": self.crontab.id,
            "schedule_id": self.id
        })
        _l.info("Schedule save: %s" % self.kwargs)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    # restore the property overwritten by 1:1 relationship
    @property
    def schedule(self):
        return self.crontab.schedule


    def get_next_run_at(self):
        try:
            # Assuming `crontab_line` is in standard cron format (minute, hour, day, month, weekday)
            cron_expression = self.crontab_line
            now = datetime.now(pytz.UTC)  # Ensure the current time is in UTC
            cron_iter = croniter(cron_expression, now)
            next_run_time = cron_iter.get_next(datetime)
            return next_run_time
        except Exception as e:
            # Handle errors, for example, invalid cron expression
            print(f"Error calculating next run time: {e}")
            return None

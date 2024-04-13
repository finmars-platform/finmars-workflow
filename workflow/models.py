from __future__ import unicode_literals

import json

import pytz
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy

from workflow.storage import get_storage


LANGUAGE_MAX_LENGTH = 5
TIMEZONE_MAX_LENGTH = 20
TIMEZONE_CHOICES = sorted(list((k, k) for k in pytz.all_timezones))
TIMEZONE_COMMON_CHOICES = sorted(list((k, k) for k in pytz.common_timezones))

from django.utils.translation import gettext_lazy as _
from workflow_app import celery_app
from django.utils.timezone import now

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
    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True,
                                   verbose_name=gettext_lazy('created'))
    modified = models.DateTimeField(auto_now=True, editable=False, db_index=True,
                                    verbose_name=gettext_lazy('modified'))

    class Meta:
        abstract = True
        get_latest_by = 'modified'
        ordering = ['created', ]


class Space(TimeStampedModel):
    name = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=gettext_lazy('name'))

    realm_code = models.CharField(max_length=255, null=True, blank=True,
                                  verbose_name=gettext_lazy('realm_code'))

    space_code = models.CharField(max_length=255,
                                  verbose_name=gettext_lazy('space_code'))


class Workflow(TimeStampedModel):
    STATUS_INIT = 'init'
    STATUS_PENDING = 'pending'
    STATUS_PROGRESS = 'progress'
    STATUS_SUCCESS = 'success'
    STATUS_ERROR = 'error'
    STATUS_TIMEOUT = 'timeout'
    STATUS_CANCELED = 'canceled'

    STATUS_CHOICES = (
        (STATUS_INIT, 'INIT'),
        (STATUS_PENDING, 'PENDING'),
        (STATUS_PROGRESS, 'PROGRESS'),
        (STATUS_SUCCESS, 'SUCCESS'),
        (STATUS_ERROR, 'ERROR'),
        (STATUS_TIMEOUT, 'TIMEOUT'),
        (STATUS_CANCELED, 'CANCELED')
    )

    name = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=gettext_lazy('name'))

    user_code = models.CharField(max_length=1024, null=True, blank=True,
                                 verbose_name=gettext_lazy('user_code'))

    status = models.CharField(null=True, max_length=255, default=STATUS_INIT, choices=STATUS_CHOICES,
                              verbose_name='status')
    payload_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('payload data'))
    periodic = models.BooleanField(default=False, verbose_name=gettext_lazy('periodic'))

    is_manager = models.BooleanField(default=False, verbose_name=gettext_lazy('is manager'))

    space = models.ForeignKey(Space, verbose_name=gettext_lazy('space'),
                              on_delete=models.CASCADE, related_name="workflows")

    owner = models.ForeignKey(User, verbose_name=gettext_lazy('owner'),
                              on_delete=models.CASCADE, related_name="workflows")

    class Meta:
        get_latest_by = 'modified'
        ordering = ['-created', 'id']

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

    def cancel(self):
        status_to_cancel = [Task.STATUS_PROGRESS, Task.STATUS_PENDING]
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

        new_workflow = system_workflow_manager.get_by_user_code(user_code)

        is_manager = new_workflow.get('is_manager', False)

        if is_manager:
            raise Exception("New Workflow is manager. Manager can't execute another manager")

        _l.info('run_new_workflow. Going to execute: %s', user_code)

        data, _ = execute_workflow(self.owner.username, user_code, payload, self.space.realm_code, self.space.space_code)

        return data


class Task(TimeStampedModel):
    STATUS_INIT = 'init'
    STATUS_PENDING = 'pending'
    STATUS_PROGRESS = 'progress'
    STATUS_SUCCESS = 'success'
    STATUS_ERROR = 'error'
    STATUS_TIMEOUT = 'timeout'
    STATUS_CANCELED = 'canceled'

    STATUS_CHOICES = (
        (STATUS_INIT, 'INIT'),
        (STATUS_PENDING, 'PENDING'),
        (STATUS_PROGRESS, 'PROGRESS'),
        (STATUS_SUCCESS, 'SUCCESS'),
        (STATUS_ERROR, 'ERROR'),
        (STATUS_TIMEOUT, 'TIMEOUT'),
        (STATUS_CANCELED, 'CANCELED'),
    )

    workflow = models.ForeignKey(Workflow, verbose_name=gettext_lazy('workflow'),
                                 on_delete=models.CASCADE, related_name="tasks")

    celery_task_id = models.CharField(null=True, max_length=255)
    name = models.CharField(null=True, max_length=255)
    source_code = models.CharField(null=True, max_length=255)
    status = models.CharField(null=True, max_length=255, default=STATUS_INIT, choices=STATUS_CHOICES,
                              verbose_name='status')
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
        ordering = ['-created']

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

from __future__ import unicode_literals

import json

import pytz
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.sessions.base_session import AbstractBaseSession
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy

from workflow.storage import get_storage

LANGUAGE_MAX_LENGTH = 5
TIMEZONE_MAX_LENGTH = 20
TIMEZONE_CHOICES = sorted(list((k, k) for k in pytz.all_timezones))
TIMEZONE_COMMON_CHOICES = sorted(list((k, k) for k in pytz.common_timezones))

from django.utils.translation import gettext_lazy as _

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

    user_code = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=gettext_lazy('user_code'))

    project = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=gettext_lazy('name'))

    status = models.CharField(null=True, max_length=255, default=STATUS_INIT, choices=STATUS_CHOICES,
                              verbose_name='status')
    payload_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('payload data'))
    periodic = models.BooleanField(default=False, verbose_name=gettext_lazy('periodic'))

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
        return f"{self.project}.{self.name}"

    def __repr__(self):
        return f"<Workflow {self.project}.{self.name}>"

    def to_dict(self, with_payload=True):
        d = {}
        d.update(
            {
                "id": self.id,
                "name": self.name,
                "project": self.project,
                "fullname": f"{self.project}.{self.name}",
                "status": self.status,
                "periodic": self.periodic,
            }
        )
        if with_payload:
            d["payload"] = self.payload
        return d


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

    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))
    error_message = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('error message'))

    verbose_name = models.CharField(null=True, max_length=255)
    verbose_result = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('verbose result'))

    previous_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('previous data'))

    is_hook = models.BooleanField(default=False, verbose_name=gettext_lazy('is hook'))

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
            self.progress_data = json.dumps(value,  sort_keys=True, indent=1)

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
            self.previous_data = json.dumps(value,  sort_keys=True, indent=1)

    # def add_attachment(self, file_report_id):
    #
    #     CeleryTaskAttachment.objects.create(celery_task=self,
    #                                         file_report_id=file_report_id)

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

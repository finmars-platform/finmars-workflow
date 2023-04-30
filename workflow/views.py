import logging
import os

import django_filters
import pexpect
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.authentication import get_authorization_header
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from workflow.celery_workflow import celery_workflow
from workflow.filters import WorkflowQueryFilter
from workflow.models import Workflow, Task
from workflow.serializers import WorkflowSerializer, TaskSerializer, PingSerializer
from workflow.workflows import execute_workflow

_l = logging.getLogger('workflow')


class WorkflowFilterSet(FilterSet):
    name = django_filters.CharFilter()
    user_code = django_filters.CharFilter()
    status = django_filters.CharFilter()
    created = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Workflow
        fields = []


class WorkflowViewSet(ModelViewSet):
    queryset = Workflow.objects.select_related(
        'owner'
    )
    serializer_class = WorkflowSerializer
    permission_classes = ModelViewSet.permission_classes + [

    ]
    filter_class = WorkflowFilterSet
    filter_backends = ModelViewSet.filter_backends + [
        OrderingFilter,
        WorkflowQueryFilter
    ]


    ordering_fields = [
        'name', 'user_code', 'created', 'modified', 'status', 'owner'
    ]

    @action(detail=False, methods=('POST',), url_path='run-workflow')
    def run_workflow(self, request, pk=None):
        user_code, payload = (
            request.data["user_code"],
            request.data["payload"],
        )
        data, _ = execute_workflow(request.user.username, user_code, payload)

        _l.info('data %s' % data)

        return Response(data)

    @action(detail=True, methods=('POST',), url_path='relaunch')
    def relaunch(self, request, pk=None):
        obj = Workflow.objects.get(id=pk)
        data, _ = execute_workflow(request.user.username, obj.user_code, obj.payload)

        return Response(data)

    @action(detail=True, methods=('POST',), url_path='cancel')
    def cancel(self, request, pk=None):
        workflow = Workflow.objects.get(id=pk)
        workflow.cancel()

        return Response(workflow.to_dict())


class TaskViewSet(ModelViewSet):
    queryset = Task.objects.select_related(
        'workflow'
    )
    serializer_class = TaskSerializer
    permission_classes = ModelViewSet.permission_classes + [

    ]
    filter_backends = ModelViewSet.filter_backends + [
    ]


class PingViewSet(ViewSet):
    permission_classes = [AllowAny, ]
    authentication_classes = []

    def get_bearer_token(self, request):
        auth = get_authorization_header(request).split()

        token = None

        if len(auth):
            token = auth[1].decode()

        return token

    @method_decorator(ensure_csrf_cookie)
    def list(self, request, *args, **kwargs):
        status_code = status.HTTP_200_OK

        serializer = PingSerializer(instance={
            'message': 'pong',
            'version': request.version,
            'now': timezone.template_localtime(timezone.now()),
        })

        return Response(serializer.data, status=status_code)


class RefreshStorageViewSet(ViewSet):

    def list(self, request, *args, **kwargs):

        try:
            c = pexpect.spawn("supervisorctl restart celery", timeout=240)
            result = c.read()
            _l.info('RefreshStorageViewSet.celery result %s' % result)
            c = pexpect.spawn("supervisorctl restart celerybeat", timeout=240)
            result = c.read()
            _l.info('RefreshStorageViewSet.celerybeat result %s' % result)

            c = pexpect.spawn("supervisorctl restart flower", timeout=240)
            result = c.read()
            _l.info('RefreshStorageViewSet.flower result %s' % result)
        except Exception as e:
            _l.info("Could not restart celery")

        celery_workflow.init_app()

        return Response({'status': 'ok'})


class DefinitionViewSet(ViewSet):

    def list(self, request, *args, **kwargs):
        workflow_definitions = []

        for user_code, definition in sorted(celery_workflow.workflows.items()):
            _l.info('DefinitionViewSet.definition %s' % definition)

            workflow_definitions.append(
                {"user_code": user_code, **definition['workflow']}
            )

        return Response(workflow_definitions)


class LogFileViewSet(ViewSet):
    def list(self, request):
        log_file_path = '/var/log/finmars/workflow/django.log'

        if not os.path.exists(log_file_path):
            return Response({"error": "Log file not found"}, status=404)

        # Read the last 2MB of your log file
        bytes_to_read = 2 * 1024 * 1024  # 2MB in bytes

        with open(log_file_path, 'r') as log_file:
            log_file.seek(max(0, log_file.tell() - bytes_to_read), 0)

            log_content = log_file.read()

        return HttpResponse(log_content, content_type="text/plain")

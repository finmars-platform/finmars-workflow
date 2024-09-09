import logging
import os
import traceback

import django_filters
import pexpect
from django.core.management import call_command
from django.db import connection
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.authentication import get_authorization_header
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet


from workflow.filters import (
    WorkflowQueryFilter,
    WholeWordsSearchFilter,
    CharFilter,
    WorkflowSearchParamFilter,
) 
      
from workflow.models import Workflow, Task, Schedule
from workflow.serializers import (
    WorkflowSerializer,
    TaskSerializer,
    PingSerializer,
    WorkflowLightSerializer,
    BulkSerializer,
    RunWorkflowSerializer,
    ScheduleSerializer,
)
from workflow.workflows import execute_workflow

from workflow.user_sessions import create_session, execute_code, sessions, execute_file
from workflow.workflows import execute_workflow

_l = logging.getLogger('workflow')

from workflow.system import get_system_workflow_manager

system_workflow_manager = get_system_workflow_manager()


class WorkflowFilterSet(FilterSet):
    name = django_filters.CharFilter()
    user_code = django_filters.CharFilter()
    status = django_filters.MultipleChoiceFilter(field_name='status', choices=Workflow.STATUS_CHOICES)
    created = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Workflow
        fields = []


class WorkflowViewSet(ModelViewSet):
    queryset = Workflow.objects.select_related(
        'owner', 'crontab'
    )
    serializer_class = WorkflowSerializer
    permission_classes = ModelViewSet.permission_classes + [

    ]
    filter_class = WorkflowFilterSet
    filter_backends = ModelViewSet.filter_backends + [
        WorkflowSearchParamFilter,
        WorkflowQueryFilter,
        WholeWordsSearchFilter,
        OrderingFilter,
    ]
    search_fields = ['payload_data']
    ordering_fields = [
        'name', 'user_code', 'created', 'modified', 'status', 'owner', 'is_manager',
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="light",
        serializer_class=WorkflowLightSerializer,
    )
    def list_light(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginator.post_paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['POST'], url_path='run-workflow', serializer_class=RunWorkflowSerializer)
    def run_workflow(self, request, pk=None, *args, **kwargs):
        user_code, payload, platform_task_id = (
            request.data["user_code"],
            request.data["payload"],
            request.data.get("platform_task_id")
        )

        user_code = f'{request.space_code}.{user_code}'

        system_workflow_manager.get_by_user_code(user_code, sync_remote=True)

        data, _ = execute_workflow(request.user.username, user_code, payload, request.realm_code, request.space_code,
                                   platform_task_id)

        _l.info('data %s' % data)

        return Response(data)

    @action(detail=True, methods=('POST',), url_path='relaunch')
    def relaunch(self, request, pk=None, *args, **kwargs):
        obj = Workflow.objects.get(id=pk)
        data, _ = execute_workflow(request.user.username, obj.user_code, obj.payload, request.realm_code,
                                   request.space_code)

        return Response(data)

    @action(detail=True, methods=('POST',), url_path='cancel')
    def cancel(self, request, pk=None, *args, **kwargs):
        workflow = Workflow.objects.get(id=pk)
        workflow.cancel()

        return Response(workflow.to_dict())

    @action(detail=False, methods=('POST',), url_path='bulk-cancel', serializer_class=BulkSerializer)
    def bulk_cancel(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        valid = serializer.is_valid(raise_exception=False)

        data = serializer.validated_data
        workflows = Workflow.objects.filter(id__in=data['ids'], status=Workflow.STATUS_PROGRESS)
        for workflow in workflows:
            workflow.cancel()

        return Response({'status': 'ok'})

    @action(detail=False, methods=('POST',), url_path='bulk-delete', serializer_class=BulkSerializer)
    def bulk_delete(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        workflows = Workflow.objects.filter(id__in=data['ids'])
        for workflow in workflows:
            workflow.cancel()
            workflow.delete()

        return Response({'status': 'ok'})


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

            #c = pexpect.spawn("supervisorctl stop celery", timeout=240)
            #result = c.read()
            #_l.info('RefreshStorageViewSet.stop celery result %s' % result)
            c = pexpect.spawn("supervisorctl stop celerybeat", timeout=240)
            result = c.read()
            _l.info('RefreshStorageViewSet.stop celerybeat result %s' % result)
            c = pexpect.spawn("supervisorctl stop flower", timeout=240)
            result = c.read()
            _l.info('RefreshStorageViewSet.stop flower result %s' % result)

            #c = pexpect.spawn("python /var/app/manage.py sync_remote_storage_to_local_storage", timeout=240)
            system_workflow_manager.sync_remote_storage_to_local_storage(request.space_code)

            #c = pexpect.spawn("supervisorctl start celery", timeout=240)
            #result = c.read()
            #_l.info('RefreshStorageViewSet.celery result %s' % result)
            c = pexpect.spawn("supervisorctl start celerybeat", timeout=240)

            result = c.read()
            _l.info('RefreshStorageViewSet.celerybeat result %s' % result)

            c = pexpect.spawn("supervisorctl start flower", timeout=240)
            result = c.read()
            _l.info('RefreshStorageViewSet.flower result %s' % result)

            system_workflow_manager.register_workflows(request.space_code)
        except Exception as e:
            _l.info("Could not restart celery.exception %s" % e)
            _l.info("Could not restart celery.traceback %s" % traceback.format_exc())

        return Response({'status': 'ok'})


class DefinitionViewSet(ViewSet):

    def list(self, request, *args, **kwargs):
        workflow_definitions = []

        for user_code, definition in sorted(system_workflow_manager.workflows.items()):
            # _l.info('DefinitionViewSet.definition %s' % definition)

            if definition["workflow"]["space_code"] == request.space_code:
                workflow_definitions.append(
                    {"user_code": user_code, **definition['workflow']}
                )

        return Response(workflow_definitions)


class LogFileViewSet(ViewSet):
    def list(self, request, *args, **kwargs):
        log_file_path = '/var/log/finmars/workflow/django.log'

        if not os.path.exists(log_file_path):
            return Response({"error": "Log file not found"}, status=404)

        # Read the last 2MB of your log file
        bytes_to_read = 2 * 1024 * 1024  # 2MB in bytes

        with open(log_file_path, 'r') as log_file:
            log_file.seek(max(0, log_file.tell() - bytes_to_read), 0)

            log_content = log_file.read()

        return HttpResponse(log_content, content_type="text/plain")


class CodeExecutionViewSet(ViewSet):

    def create(self, request, *args, **kwargs):
        """
        This function handles POST request to execute code.
        It expects 'code' and 'file_path' in the request data.
        """
        user_id = request.user.id  # or however you get the user's ID
        code = request.data.get('code')
        file_path = request.data.get('file_path')

        # Ensure the user session is created
        if user_id not in sessions:
            create_session(user_id)

        try:
            # Try to execute the code
            output = execute_code(user_id, file_path, code)
            return Response({"detail": "Code executed successfully.", "result": output})

        except Exception as e:
            # Catch any errors during code execution
            return Response({"error": str(e)}, status=400)


class FileExecutionViewSet(ViewSet):

    # force serializer to make it visible in Django Browserable API
    def create(self, request, *args, **kwargs):
        """
        This function handles POST request to execute code.
        It expects 'code' and 'file_path' in the request data.
        """
        user_id = request.user.id  # or however you get the user's ID
        data = request.data.get('data', {})
        file_path = request.data.get('file_path')

        # Ensure the user session is created
        if user_id not in sessions:
            create_session(user_id)

        try:
            # Try to execute the code
            output = execute_file(user_id, file_path, data)
            return Response(output)

        except Exception as e:
            # Catch any errors during code execution
            return Response({"error": str(e)}, status=400)


class RealmMigrateSchemeView(ViewSet):
    permission_classes = [AllowAny, ]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        try:
            # Assume search_path is set by RealmAndSpaceMiddleware
            call_command("migrate")

            return Response({"status": "ok"})
        except Exception as e:
            _l.error(f"RealmMigrateSchemeView.exception: {str(e)}")
            _l.error(f"RealmMigrateSchemeView.traceback: {traceback.format_exc()}")

            return Response({"status": "error", "message": str(e)})


class ScheduleViewSet(ModelViewSet):
    queryset = Schedule.objects.select_related('owner', 'crontab')
    serializer_class = ScheduleSerializer
    permission_classes = ModelViewSet.permission_classes + [
    ]
    filter_backends = ModelViewSet.filter_backends + [
    ]

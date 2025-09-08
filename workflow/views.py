import logging
import os
import traceback

import django_filters
from django.core.management import call_command
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

from workflow.filters import (
    WholeWordsSearchFilter,
    WorkflowQueryFilter,
    WorkflowSearchParamFilter,
)
from workflow.models import Schedule, Task, Workflow, WorkflowTemplate
from workflow.serializers import (
    BulkSerializer,
    PingSerializer,
    ResumeWorkflowSerializer,
    RunWorkflowSerializer,
    ScheduleSerializer,
    TaskSerializer,
    WorkflowLightSerializer,
    WorkflowSerializer,
    WorkflowTemplateSerializer,
)
from workflow.system import get_system_workflow_manager
from workflow.user_sessions import create_session, execute_code, execute_file, sessions
from workflow.workflows import execute_workflow
from workflow_app import celery_app

_l = logging.getLogger("workflow")

system_workflow_manager = get_system_workflow_manager()


class WorkflowTemplateFilterSet(FilterSet):
    name = django_filters.CharFilter()
    user_code = django_filters.CharFilter()
    created_at = django_filters.DateFromToRangeFilter()

    class Meta:
        model = WorkflowTemplate
        fields = []


class WorkflowTemplateViewSet(ModelViewSet):
    queryset = WorkflowTemplate.objects.select_related(
        "owner",
    )
    serializer_class = WorkflowTemplateSerializer
    permission_classes = ModelViewSet.permission_classes + []
    filter_class = WorkflowTemplateFilterSet
    filter_backends = ModelViewSet.filter_backends + [
        WorkflowSearchParamFilter,
        WorkflowQueryFilter,
        WholeWordsSearchFilter,
        OrderingFilter,
    ]
    search_fields = ["data"]
    ordering_fields = [
        "name",
        "user_code",
        "created_at",
        "modified_at",
        "owner",
    ]

    @action(
        detail=False,
        methods=["POST"],
        url_path="run-workflow",
        serializer_class=RunWorkflowSerializer,
    )
    def run_workflow(self, request, pk=None, *args, **kwargs):
        user_code, payload, platform_task_id = (
            request.data["user_code"],
            request.data["payload"],
            request.data.get("platform_task_id"),
        )

        if request.space_code not in user_code:
            user_code = f"{request.space_code}.{user_code}"

        system_workflow_manager.get_by_user_code(user_code, sync_remote=True)

        data = execute_workflow(
            request.user.username,
            user_code,
            payload,
            request.realm_code,
            request.space_code,
            platform_task_id,
        )

        _l.info("data %s", data)

        return Response(data)


class WorkflowFilterSet(FilterSet):
    name = django_filters.CharFilter()
    user_code = django_filters.CharFilter()
    status = django_filters.MultipleChoiceFilter(field_name="status", choices=Workflow.STATUS_CHOICES)
    created_at = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Workflow
        fields = []


class WorkflowViewSet(ModelViewSet):
    queryset = Workflow.objects.select_related("owner", "crontab")
    serializer_class = WorkflowSerializer
    permission_classes = ModelViewSet.permission_classes + []
    filter_class = WorkflowFilterSet
    filter_backends = ModelViewSet.filter_backends + [
        WorkflowSearchParamFilter,
        WorkflowQueryFilter,
        WholeWordsSearchFilter,
        OrderingFilter,
    ]
    search_fields = ["payload_data"]
    ordering_fields = [
        "name",
        "user_code",
        "created_at",
        "modified_at",
        "status",
        "owner",
        "is_manager",
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

    @action(
        detail=False,
        methods=["POST"],
        url_path="run-workflow",
        serializer_class=RunWorkflowSerializer,
    )
    def run_workflow(self, request, pk=None, *args, **kwargs):
        user_code, payload, platform_task_id = (
            request.data["user_code"],
            request.data["payload"],
            request.data.get("platform_task_id"),
        )

        if request.space_code not in user_code:
            user_code = f"{request.space_code}.{user_code}"

        _l.info("user_code %s", user_code)

        system_workflow_manager.get_by_user_code(user_code, sync_remote=True)

        data = execute_workflow(
            request.user.username,
            user_code,
            payload,
            request.realm_code,
            request.space_code,
            platform_task_id,
        )

        _l.info("data %s", data)

        return Response(data)

    @action(detail=True, methods=("POST",), url_path="relaunch")
    def relaunch(self, request, pk=None, *args, **kwargs):
        obj = Workflow.objects.get(id=pk)
        data = execute_workflow(
            request.user.username,
            obj.user_code,
            obj.payload,
            request.realm_code,
            request.space_code,
        )

        return Response(data)

    @action(detail=True, methods=("POST",), url_path="cancel")
    def cancel(self, request, pk=None, *args, **kwargs):
        workflow = Workflow.objects.get(id=pk)

        if workflow.status in [Workflow.STATUS_INIT, Workflow.STATUS_PROGRESS, Workflow.STATUS_WAIT]:
            workflow.cancel()

            return Response(workflow.to_dict())

        else:
            return Response({"message": "Could not Cancel finished task"})

    @action(
        detail=False,
        methods=("POST",),
        url_path="bulk-cancel",
        serializer_class=BulkSerializer,
    )
    def bulk_cancel(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        valid = serializer.is_valid(raise_exception=False)  # noqa: F841

        data = serializer.validated_data
        workflows = Workflow.objects.filter(id__in=data["ids"], status=Workflow.STATUS_PROGRESS)
        for workflow in workflows:
            workflow.cancel()

        return Response({"status": "ok"})

    @action(
        detail=False,
        methods=("POST",),
        url_path="bulk-delete",
        serializer_class=BulkSerializer,
    )
    def bulk_delete(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        workflows = Workflow.objects.filter(id__in=data["ids"])
        for workflow in workflows:
            workflow.cancel()
            workflow.delete()

        return Response({"status": "ok"})

    # Pause Workflow Action
    @action(detail=True, methods=["PUT"], url_path="pause")
    def pause_workflow(self, request, pk=None, *args, **kwargs):
        try:
            workflow = self.get_object()  # Get the workflow instance
            if workflow.status != Workflow.STATUS_PROGRESS:
                return Response(
                    {"message": "Cannot pause workflow that is not in progress."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            workflow.status = Workflow.STATUS_WAIT
            workflow.save()

            return Response(
                {"message": f"Workflow {workflow.id} paused successfully."},
                status=status.HTTP_200_OK,
            )

        except Workflow.DoesNotExist:
            return Response({"message": "Workflow not found."}, status=status.HTTP_404_NOT_FOUND)

    # Resume Workflow Action
    @action(
        detail=True,
        methods=["PUT"],
        url_path="resume",
        serializer_class=ResumeWorkflowSerializer,
    )
    def resume_workflow(self, request, pk=None, *args, **kwargs):
        try:
            # Use the serializer to validate the input data
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            workflow = self.get_object()  # Get the workflow instance
            if workflow.status != Workflow.STATUS_WAIT:
                return Response(
                    {"message": "Cannot resume workflow that is not paused."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if there are any running tasks associated with this workflow
            active_tasks = Task.objects.filter(
                workflow_id=workflow.id,
                status__in=[Task.STATUS_PROGRESS, Task.STATUS_INIT],
            )

            if active_tasks.exists():
                return Response(
                    {"message": "Cannot resume workflow while there are active tasks running."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update the payload if provided
            new_payload = serializer.validated_data.get("payload")
            if new_payload:
                workflow.payload = new_payload

            # Update workflow status to progress
            workflow.status = Workflow.STATUS_PROGRESS
            workflow.save()

            from workflow.tasks.workflows import process_next_node

            # Trigger the next task from the stored `current_node_id`
            if workflow.current_node_id:
                nodes = {node["id"]: node for node in workflow.workflow_template.data["workflow"]["nodes"]}
                connections = workflow.workflow_template.data["workflow"]["connections"]
                adjacency_list = {node_id: [] for node_id in nodes}
                for connection in connections:
                    adjacency_list[connection["source"]].append(connection["target"])

                process_next_node.apply_async(
                    kwargs={
                        "current_node_id": workflow.current_node_id,
                        "workflow_id": workflow.id,
                        # Fetch nodes, adjacency_list, and connections from the workflow data
                        "nodes": nodes,
                        "adjacency_list": adjacency_list,
                        "connections": connections,
                        "context": {
                            "realm_code": workflow.space.realm_code,
                            "space_code": workflow.space.space_code,
                        },
                    },
                    queue="workflow",
                )

                return Response(
                    {"message": f"Workflow {workflow.id} resumed successfully."},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"message": "No node to resume from."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Workflow.DoesNotExist:
            return Response({"message": "Workflow not found."}, status=status.HTTP_404_NOT_FOUND)


class TaskViewSet(ModelViewSet):
    queryset = Task.objects.select_related("workflow")
    serializer_class = TaskSerializer
    permission_classes = ModelViewSet.permission_classes + []
    filter_backends = ModelViewSet.filter_backends + []


class PingViewSet(ViewSet):
    permission_classes = [
        AllowAny,
    ]
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

        serializer = PingSerializer(
            instance={
                "message": "pong",
                "version": request.version,
                "now": timezone.template_localtime(timezone.now()),
            }
        )

        return Response(serializer.data, status=status_code)


class RefreshStorageViewSet(ViewSet):
    def list(self, request, *args, **kwargs):
        try:
            # c = pexpect.spawn("supervisorctl stop celery", timeout=240)
            # result = c.read()
            # _l.info('RefreshStorageViewSet.stop celery result %s' % result)
            # c = pexpect.spawn("supervisorctl stop celerybeat", timeout=240)
            # result = c.read()
            # _l.info("RefreshStorageViewSet.stop celerybeat result %s" % result)
            # c = pexpect.spawn("supervisorctl stop flower", timeout=240)
            # result = c.read()
            # _l.info("RefreshStorageViewSet.stop flower result %s" % result)

            # c = pexpect.spawn("python /var/app/manage.py sync_remote_storage_to_local_storage", timeout=240)
            system_workflow_manager.sync_remote_storage_to_local_storage(request.space_code)

            # c = pexpect.spawn("supervisorctl start celery", timeout=240)
            # result = c.read()
            # _l.info('RefreshStorageViewSet.celery result %s' % result)
            # c = pexpect.spawn("supervisorctl start celerybeat", timeout=240)
            #
            # result = c.read()
            # _l.info("RefreshStorageViewSet.celerybeat result %s" % result)
            #
            # c = pexpect.spawn("supervisorctl start flower", timeout=240)
            # result = c.read()
            # _l.info("RefreshStorageViewSet.flower result %s" % result)

            system_workflow_manager.register_workflows(request.space_code)
        except Exception as e:
            _l.info("Could not restart celery.exception %s", e)
            _l.info("Could not restart celery.traceback %s", traceback.format_exc())

        return Response({"status": "ok"})


class DefinitionViewSet(ViewSet):
    def list(self, request, *args, **kwargs):
        workflow_definitions = []

        for user_code, definition in sorted(system_workflow_manager.workflows.items()):
            # _l.info('DefinitionViewSet.definition %s' % definition)

            if definition["workflow"]["space_code"] == request.space_code:
                workflow_definitions.append({"user_code": user_code, **definition["workflow"]})

        return Response(workflow_definitions)


class LogFileViewSet(ViewSet):
    def list(self, request, *args, **kwargs):
        log_file_path = "/var/log/finmars/workflow/django.log"

        if not os.path.exists(log_file_path):
            return Response({"error": "Log file not found"}, status=404)

        # Read the last 2MB of your log file
        bytes_to_read = 2 * 1024 * 1024  # 2MB in bytes

        with open(log_file_path) as log_file:
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
        code = request.data.get("code")
        file_path = request.data.get("file_path")

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
        data = request.data.get("data", {})
        file_path = request.data.get("file_path")

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
    permission_classes = [
        AllowAny,
    ]
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
    queryset = Schedule.objects.select_related("owner", "crontab")
    serializer_class = ScheduleSerializer
    permission_classes = ModelViewSet.permission_classes + []
    filter_backends = ModelViewSet.filter_backends + []

    @action(detail=True, methods=["put"], url_path="run-manual")
    def run_manual(self, request, *args, **kwargs):
        try:
            schedule = self.get_object()  # Get the schedule instance

            if not schedule.enabled:
                return Response(
                    {"message": "Cannot run a disabled schedule."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            from workflow.tasks.workflows import execute

            # Trigger the Celery task to run the workflow manually
            execute.apply_async(
                args=[
                    f"{schedule.space.space_code}.{schedule.workflow_user_code}",
                    schedule.payload,
                    schedule.is_manager,
                ],
                kwargs={
                    "context": {
                        "realm_code": schedule.space.realm_code,
                        "space_code": schedule.space.space_code,
                    },
                    "crontab_id": schedule.crontab.id,
                    "schedule_id": schedule.id,
                },
                queue="workflow",
            )

            return Response(
                {"message": "Schedule is being run manually."},
                status=status.HTTP_202_ACCEPTED,
            )

        except Schedule.DoesNotExist:
            return Response({"error": "Schedule not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CeleryStatusViewSet(ViewSet):
    """
    A simple ViewSet that returns Celery queue and worker status.
    """

    def list(self, request, *args, **kwargs):
        insp = celery_app.control.inspect()
        data = {
            "workers": insp.stats() or {},
            "active": insp.active() or {},
            "reserved": insp.reserved() or {},
            "scheduled": insp.scheduled() or {},
        }

        return Response(data)

import json
import traceback
import pexpect

from workflow.celery_workflow import celery_workflow
from workflow.models import Workflow, Task

from rest_framework.viewsets import ModelViewSet, ViewSet

from workflow.serializers import WorkflowSerializer, TaskSerializer, PingSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.authentication import get_authorization_header
from rest_framework import status
from rest_framework.decorators import action

import logging

from workflow.workflows import execute_workflow

_l = logging.getLogger('workflow')

class WorkflowViewSet(ModelViewSet):
    queryset = Workflow.objects.select_related(
        'owner'
    )
    serializer_class = WorkflowSerializer
    permission_classes = ModelViewSet.permission_classes + [

    ]
    filter_backends = ModelViewSet.filter_backends + [
    ]

    @action(detail=False, methods=('POST',), url_path='run-workflow')
    def run_workflow(self, request, pk=None):

        project, name, payload = (
            request.data["project"],
            request.data["name"],
            request.data["payload"],
        )
        data, _ = execute_workflow(request.user.username, project, name, payload)

        _l.info('data %s' % data)

        return Response(data)

    @action(detail=True, methods=('POST',), url_path='relaunch')
    def relaunch(self, request, pk=None):

        obj = Workflow.objects.get(id=pk)
        data, _ = execute_workflow(request.user.username, obj.project, obj.name, obj.payload)

        return Response(data)


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
            pexpect.spawn("supervisorctl restart celery", timeout=240)
            pexpect.spawn("supervisorctl restart celerybeat", timeout=240)
        except Exception as e:
            _l.info("Could not restart celery")

        celery_workflow.init_app()

        return Response({'status': 'ok'})



class DefinitionViewSet(ViewSet):

    def list(self, request, *args, **kwargs):

        workflow_definitions = []

        for fullname, definition in sorted(celery_workflow.workflows.items()):

            project, name = fullname.split(".", 1)

            workflow_definitions.append(
                {"fullname": fullname, "project": project, "name": name, **definition}
            )

        return Response(workflow_definitions)


import traceback

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

import logging
_l = logging.getLogger('workflow')

class WorkflowViewSet(ModelViewSet):
    queryset = Workflow.objects.select_related(
        'user'
    )
    serializer_class = WorkflowSerializer
    permission_classes = ModelViewSet.permission_classes + [

    ]
    filter_backends = ModelViewSet.filter_backends + [
    ]


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


class DefinitionViewSet(ViewSet):

    def list(self, request, *args, **kwargs):

        workflow_definitions = []

        for fullname, definition in sorted(celery_workflow.workflows.items()):

            project, name = fullname.split(".", 1)

            workflow_definitions.append(
                {"fullname": fullname, "project": project, "name": name, **definition}
            )

        return Response(workflow_definitions)


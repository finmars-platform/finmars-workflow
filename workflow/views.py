from workflow.models import Workflow, Task

from rest_framework.viewsets import ModelViewSet, ViewSet

from workflow.serializers import WorkflowSerializer, TaskSerializer


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


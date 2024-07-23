import json
from rest_framework import serializers

from workflow.fields import SpaceField
from workflow.models import Workflow, Task


class TaskSerializer(serializers.ModelSerializer):
    space = SpaceField()

    payload = serializers.JSONField(allow_null=True, required=False)
    result = serializers.JSONField(allow_null=True, required=False)
    progress = serializers.JSONField(allow_null=True, required=False)
    previous = serializers.JSONField(allow_null=True, required=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['worker_name']:
            representation['worker_name'] = representation['worker_name'].replace('celery@', '')
        return representation

    class Meta:
        model = Task
        fields = ['id',
                  'space',
                  'name', 'source_code',
                  'workflow', 'status', 'celery_task_id', 'source_code',
                  'previous', 'is_hook',
                  'payload', 'result', 'progress',

                  'created', 'modified', 'log', 'worker_name',
                  'finished_at'
                  ]


class WorkflowSerializer(serializers.ModelSerializer):
    space = SpaceField()

    payload = serializers.JSONField(allow_null=True, required=False)
    tasks = TaskSerializer(many=True)

    class Meta:
        model = Workflow
        fields = ['id', 'name', 'user_code',
                  'owner', 'space',
                  'status',
                  'payload', 'created', 'modified', 'tasks', 'periodic',
                  'is_manager']


class WorkflowLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = ['id', 'name', 'user_code',
                  'owner',
                  'status',
                  'created', 'modified', 'periodic',
                  'is_manager']


class PingSerializer(serializers.Serializer):
    message = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)
    is_authenticated = serializers.BooleanField(read_only=True)
    is_anonymous = serializers.BooleanField(read_only=True)
    now = serializers.DateTimeField(read_only=True)


class BulkSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())


class RunWorkflowSerializer(serializers.Serializer):
    user_code = serializers.CharField(required=True)
    payload = serializers.CharField(allow_blank=True)

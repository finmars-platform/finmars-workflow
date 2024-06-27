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

    class Meta:
        model = Task
        fields = ['id',
                  'space',
                  'name', 'source_code',
                  'workflow', 'status', 'celery_task_id', 'source_code',
                  'previous', 'is_hook',
                  'payload', 'result', 'progress',

                  'created', 'modified', 'log',
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


class CeleryWorkerSerializer(serializers.Serializer):
    worker_name = serializers.CharField(required=True)
    worker_type = serializers.CharField(default="worker")
    memory_limit = serializers.CharField()
    queue = serializers.CharField(default="workflow")

    id = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_id(self, instance):
        return instance["worker_name"]

    def get_status(self, instance):
        try:
            return instance["status"]
        except Exception as e:
            return {
                "status": "unknown",
                "error_message": None
            }

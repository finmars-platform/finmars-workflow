from rest_framework import serializers

from workflow.models import Workflow, Task


class TaskSerializer(serializers.ModelSerializer):
    payload = serializers.JSONField(allow_null=True, required=False)
    result = serializers.JSONField(allow_null=True, required=False)
    progress = serializers.JSONField(allow_null=True, required=False)
    previous = serializers.JSONField(allow_null=True, required=False)

    class Meta:
        model = Task
        fields = ['id',
                  'name', 'source_code',
                  'workflow', 'status', 'celery_task_id', 'source_code',
                  'previous', 'is_hook',
                  'payload', 'result', 'progress',

                  'created', 'modified'
                  ]


class WorkflowSerializer(serializers.ModelSerializer):
    payload = serializers.JSONField(allow_null=True, required=False)
    tasks = TaskSerializer(many=True)

    class Meta:
        model = Workflow
        fields = ['id', 'name', 'user_code', 'project', 'owner', 'status', 'payload', 'created', 'modified', 'tasks', 'periodic']


class PingSerializer(serializers.Serializer):
    message = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)
    is_authenticated = serializers.BooleanField(read_only=True)
    is_anonymous = serializers.BooleanField(read_only=True)
    now = serializers.DateTimeField(read_only=True)

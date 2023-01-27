
from rest_framework import serializers

from workflow.models import Workflow, Task


class WorkflowSerializer(serializers.ModelSerializer):

    payload = serializers.JSONField(allow_null=True, required=False)

    class Meta:
        model = Workflow
        fields = ['id', 'name', 'project', 'owner', 'status', 'payload']



class TaskSerializer(serializers.ModelSerializer):

    payload = serializers.JSONField(allow_null=True, required=False)
    result = serializers.JSONField(allow_null=True, required=False)
    progress = serializers.JSONField(allow_null=True, required=False)

    class Meta:
        model = Task
        fields = ['id',
                  'workflow', 'status', 'celery_task_id', 'source_code'
                  'payload', 'result', 'progress']


class PingSerializer(serializers.Serializer):
    message = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)
    is_authenticated = serializers.BooleanField(read_only=True)
    is_anonymous = serializers.BooleanField(read_only=True)
    now = serializers.DateTimeField(read_only=True)
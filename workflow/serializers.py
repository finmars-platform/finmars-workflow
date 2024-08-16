import json
from rest_framework import serializers

from workflow.fields import SpaceField, OwnerField
from workflow.models import Workflow, Task, Schedule
from workflow.system import get_system_workflow_manager


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
    crontab_line = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = ['id', 'name', 'user_code',
                  'owner',
                  'status',
                  'created', 'modified', 'periodic',
                  'is_manager', 'crontab_line']

    def get_crontab_line(self, obj):
        if obj.crontab:
            return obj.crontab.human_readable


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


class FileExecutionSerializer(serializers.Serializer):
    file_path = serializers.CharField(max_length=1024)
    data = serializers.JSONField()


class ScheduleSerializer(serializers.ModelSerializer):
    owner = OwnerField()
    space = SpaceField()
    payload = serializers.JSONField(allow_null=True, required=False)
    crontab_line = serializers.CharField()
    user_code = serializers.ChoiceField(choices=[])
    owner_username = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = ['id', 'user_code', 'space', 'owner', 'created', 'modified', 'payload', 'crontab_line',
                  'enabled', 'owner_id', 'owner_username']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        manager = get_system_workflow_manager()
        space_code = self.context['request'].space_code
        workflow_codes = filter(lambda k: k.startswith(space_code), manager.workflows.keys())
        self.fields['user_code'].choices = [workflow_code[len(space_code)+1:] for workflow_code in workflow_codes]

    def validate_crontab_line(self, value):
        try:
            minute, hour, day, month, weekday = value.split(' ')
        except ValueError:
            raise serializers.ValidationError("Wrong crontab format. Make sure there are 5 space-separated values")
        return value

    def get_owner_username(self, obj):
        return obj.owner.username

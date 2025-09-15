import json

from rest_framework import serializers

from workflow.fields import OwnerField, SpaceField
from workflow.finmars import Storage
from workflow.models import Schedule, Task, Workflow, WorkflowTemplate


class TaskSerializer(serializers.ModelSerializer):
    space = SpaceField()

    payload = serializers.JSONField(allow_null=True, required=False)
    result = serializers.JSONField(allow_null=True, required=False)
    progress = serializers.JSONField(allow_null=True, required=False)
    previous = serializers.JSONField(allow_null=True, required=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation["worker_name"]:
            representation["worker_name"] = representation["worker_name"].replace("celery@", "")
        return representation

    class Meta:
        model = Task
        fields = [
            "id",
            "space",
            "name",
            "source_code",
            "node_id",
            "workflow",
            "status",
            "celery_task_id",
            "source_code",
            "previous",
            "is_hook",
            "payload",
            "result",
            "progress",
            "created_at",
            "modified_at",
            "log",
            "worker_name",
            "error_message",
            "finished_at",
        ]


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    space = SpaceField()
    owner = OwnerField()
    data = serializers.JSONField(allow_null=True, required=False)

    class Meta:
        model = WorkflowTemplate
        fields = [
            "id",
            "name",
            "user_code",
            "notes",
            "owner",
            "space",
            "created_at",
            "modified_at",
            "data",
        ]

    def save_to_storage(self, instance):
        storage = Storage()

        pieces = instance.user_code.split(":")

        module_name = pieces[1]
        module_path = pieces[0].split(".")

        # why we have this hardcode inctead "/".join(module_path + modele_name) + /workflow.json ?
        path = f"workflows/{module_path[0]}/{module_path[1]}/{module_path[2]}/{module_name}/workflow.json"

        storage.save_text(path, json.dumps(instance.data, indent=4))

    def create(self, validated_data):
        instance = super().create(validated_data)
        self.save_to_storage(instance)
        return instance

    # Override the update method to write a JSON file
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self.save_to_storage(instance)
        return instance


class SimpleWorkflowSerializer(serializers.ModelSerializer):
    space = SpaceField()

    workflow_template_object = WorkflowTemplateSerializer(read_only=True, source="workflow_template")
    payload = serializers.JSONField(allow_null=True, required=False)
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Workflow

        fields = [
            "id",
            "name",
            "user_code",
            "owner",
            "space",
            "node_id",
            "current_node_id",
            "status",
            "workflow_template",
            "workflow_template_object",
            "payload",
            "created_at",
            "modified_at",
            "tasks",
            "periodic",
            "finished_at",
            "is_manager",
        ]


class WorkflowSerializer(serializers.ModelSerializer):
    space = SpaceField()

    workflow_template_object = WorkflowTemplateSerializer(read_only=True, source="workflow_template")
    payload = serializers.JSONField(allow_null=True, required=False)
    tasks = TaskSerializer(many=True, read_only=True)
    parent = SimpleWorkflowSerializer(read_only=True)
    workflow_version = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = [
            "id",
            "name",
            "user_code",
            "owner",
            "space",
            "node_id",
            "current_node_id",
            "status",
            "workflow_template",
            "workflow_template_object",
            "payload",
            "created_at",
            "modified_at",
            "tasks",
            "periodic",
            "finished_at",
            "parent",
            "workflow_version",
            "is_manager",
        ]

    def get_workflow_version(self, obj) -> int:
        if obj.workflow_template:
            if workflow_template_data := WorkflowTemplateSerializer(obj.workflow_template).data:
                if data := workflow_template_data.get("data"):
                    if isinstance(data, str):
                        data = json.loads(data)

                    if (version := data.get("version")) and isinstance(version, str) and version.isdigit():
                        return int(version)
        return 1


class WorkflowLightSerializer(serializers.ModelSerializer):
    crontab_line = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = [
            "id",
            "name",
            "user_code",
            "owner",
            "status",
            "created_at",
            "modified_at",
            "periodic",
            "is_manager",
            "crontab_line",
        ]

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
    # user_code = serializers.ChoiceField(choices=[])
    owner_username = serializers.SerializerMethodField()

    last_run_at = serializers.DateTimeField(read_only=True)
    next_run_at = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = [
            "id",
            "user_code",
            "name",
            "space",
            "owner",
            "created_at",
            "modified_at",
            "payload",
            "crontab_line",
            "is_manager",
            "workflow_user_code",
            "notes",
            "next_run_at",
            "last_run_at",
            "enabled",
            "owner_id",
            "owner_username",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # manager = get_system_workflow_manager()
        # space_code = self.context['request'].space_code
        # workflow_codes = filter(lambda k: k.startswith(space_code), manager.workflows.keys())
        # self.fields['user_code'].choices = [workflow_code[len(space_code)+1:] for workflow_code in workflow_codes]

    def validate_crontab_line(self, value):
        try:
            minute, hour, day, month, weekday = value.split(" ")
        except ValueError as e:
            raise serializers.ValidationError(
                "Wrong crontab format. Make sure there are 5 space-separated values"
            ) from e
        return value

    def get_owner_username(self, obj):
        return obj.owner.username

    def get_next_run_at(self, obj):
        # Get the next run time using the model method
        next_run_at = obj.get_next_run_at()
        return next_run_at if next_run_at else None


class ResumeWorkflowSerializer(serializers.Serializer):
    payload = serializers.JSONField(
        required=False,
        help_text="Optional payload to update the workflow before resuming.",
    )


class CeleryTaskSerializer(serializers.Serializer):
    acknowledged = serializers.BooleanField()
    args = serializers.ListField()
    delivery_info = serializers.DictField()
    hostname = serializers.CharField()
    id = serializers.CharField()
    kwargs = serializers.DictField()
    name = serializers.CharField()
    time_start = serializers.FloatField()
    type = serializers.CharField()
    worker_pid = serializers.IntegerField()

    def to_representation(self, instance):
        data = super().to_representation(instance)

        kwargs = instance.get("kwargs", {})
        context = kwargs.get("context", {})
        realm_code = context.get("realm_code", "")
        space_code = context.get("space_code", "")

        hostname = instance.get("hostname", "")
        if "workflow" in hostname:
            workflow_id = kwargs.get("workflow_id")
            if workflow_id and realm_code and space_code:
                data["url"] = f"/{realm_code}/{space_code}/w/workflow/{workflow_id}"
            else:
                data["url"] = None
        elif "backend" in hostname:
            task_id = kwargs.get("task_id")
            if task_id and realm_code and space_code:
                data["url"] = f"/{realm_code}/{space_code}/api/v1/tasks/task/{task_id}"
            else:
                data["url"] = None
        else:
            data["url"] = None

        return data


class CeleryWorkerSerializer(serializers.Serializer):
    active_tasks = CeleryTaskSerializer(many=True)
    scheduled_tasks = CeleryTaskSerializer(many=True)
    pending_tasks = CeleryTaskSerializer(many=True)
    active_tasks_count = serializers.IntegerField()
    pending_tasks_count = serializers.IntegerField()
    scheduled_tasks_count = serializers.IntegerField()
    total_tasks_count = serializers.IntegerField()


class CeleryWorkerTypeSerializer(serializers.Serializer):
    def to_representation(self, instance):
        result = {}
        for worker_name, worker_data in instance.items():
            result[worker_name] = CeleryWorkerSerializer(worker_data).data
        return result


class CeleryMonitoringSerializer(serializers.Serializer):
    def to_representation(self, instance):
        result = {}
        for worker_type, workers in instance.items():
            result[worker_type] = CeleryWorkerTypeSerializer(workers).data
        return result


class RabbitMQQueueSerializer(serializers.Serializer):
    name = serializers.CharField()
    messages = serializers.IntegerField()
    messages_ready = serializers.IntegerField()
    messages_unacknowledged = serializers.IntegerField()
    consumers = serializers.IntegerField()
    consumer_utilisation = serializers.FloatField()


class RabbitMQQueueGroupSerializer(serializers.Serializer):
    def to_representation(self, instance):
        result = {}
        for queue_name, queue_data in instance.items():
            result[queue_name] = RabbitMQQueueSerializer(queue_data).data
        return result


class RabbitMQMonitoringSerializer(serializers.Serializer):
    def to_representation(self, instance):
        result = {}
        for group_name, queues in instance.items():
            result[group_name] = RabbitMQQueueGroupSerializer(queues).data
        return result

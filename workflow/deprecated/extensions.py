import json
import os
from json.decoder import JSONDecodeError
from pathlib import Path

import sentry_sdk
import yaml
from celery import Celery
from celery.exceptions import SoftTimeLimitExceeded
from flask_json_schema import JsonSchema
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from pluginbase import PluginBase
from sentry_sdk.integrations import celery as sentry_celery
from sentry_sdk.utils import capture_internal_exceptions
from sqlalchemy.schema import MetaData


from workflow.exceptions import SchemaNotFound, SchemaNotValid, WorkflowNotFound
from workflow.storage import get_storage
from workflow_app import settings

storage = get_storage()


class CeleryWorkflow:
    def __init__(self):
        self.app = None
        self.workflows = None

    def set_app(self, app):
        self.app = app

    def init_app(self):


        workflow_path = settings.BASE_API_URL + '/workflows'

        workflowies, files = storage.listdir(workflow_path)

        self.workflows = {}

        # print('files %s' % files)

        for file in files:

            if '.yml' in file or '.yaml' in file:
                f = storage.open(workflow_path + '/' + file).read()

                self.workflows.update(yaml.load(f, Loader=yaml.SafeLoader))

        # print("Workflows are loaded")

        # print('self.workflows %s' % self.workflows)

        if self.workflows:
            self.load_user_tasks_from_storage_to_local_filesystem()
            self.import_user_tasks()
            self.read_schemas()

    def get_by_name(self, name):
        workflow = self.workflows.get(name)
        if not workflow:
            raise WorkflowNotFound(f"Workflow {name} not found")
        return workflow

    def get_tasks(self, name):
        return self.get_by_name(name)["tasks"]

    def get_hook_task(self, name, hook_name):
        if (
                "hooks" in self.get_by_name(name)
                and hook_name in self.get_by_name(name)["hooks"]
        ):
            return self.get_by_name(name)["hooks"][hook_name]
        return None

    def get_failure_hook_task(self, name):
        return self.get_hook_task(name, "failure")

    def get_success_hook_task(self, name):
        return self.get_hook_task(name, "success")

    def get_queue(self, name):
        try:
            return self.get_by_name(name)["queue"]
        except KeyError:
            return "workflow"

    def load_user_tasks_from_storage_to_local_filesystem(self):

        workflow_path = settings.BASE_API_URL + '/workflows/tasks'

        workflowies, files = storage.listdir(workflow_path)

        for filename in files:

            if '.py' in filename:

                # print("Going to sync file %s " % filename)

                with storage.open(workflow_path + '/' + filename) as f:

                    f_content = f.read()

                    os.makedirs(os.path.dirname(settings.workflow_LOCAL_DIR + '/tasks/' + filename), exist_ok=True)

                    with open(settings.workflow_LOCAL_DIR + '/tasks/' + filename, 'wb') as new_file:
                        new_file.write(f_content)


    def import_user_tasks(self):
        self.plugin_base = PluginBase(package="workflow.foobar")

        folder = Path(settings.workflow_LOCAL_DIR).resolve()
        self.plugin_source = self.plugin_base.make_plugin_source(
            searchpath=[str(folder)]
        )

        tasks = Path(folder / "tasks").glob("**/*.py")

        # print('tasks %s' % tasks)

        with self.plugin_source:
            for task in tasks:

                try:

                    if task.stem == "__init__":
                        continue

                    name = str(task.relative_to(folder))[:-3].replace("/", ".")
                    __import__(
                        self.plugin_source.base.package + "." + name,
                        globals(),
                        {},
                        ["__name__"],
                    )
                except Exception as e:
                    print("Could not load user script %s. Error %s" % (task, e))

        print("Tasks are loaded")

    def read_schemas(self):
        folder = Path(settings.BASE_API_URL + '/workflows/').resolve()

        for name, conf in self.workflows.items():
            if "schema" in conf:
                path = Path(folder / "schemas" / f"{conf['schema']}.json")

                try:
                    schema = json.loads(open(path).read())
                except FileNotFoundError:
                    raise SchemaNotFound(
                        f"Schema '{conf['schema']}' not found ({path})"
                    )
                except JSONDecodeError as e:
                    raise SchemaNotValid(f"Schema '{conf['schema']}' not valid ({e})")

                self.workflows[name]["schema"] = schema


# Celery Extension
class FlaskCelery(Celery):
    def __init__(self, *args, **kwargs):
        kwargs["include"] = ["workflow.tasks"]
        super(FlaskCelery, self).__init__(*args, **kwargs)

        if "app" in kwargs:
            self.init_app(kwargs["app"])

    def init_app(self, app):
        self.app = app

        print('FlaskCelery.app %s' % app)

        self.conf.update(app.config.get("CELERY_CONF", {}))


# Sentry Extension
class workflowSentry:
    def __init__(self):
        self.app = None

    def init_app(self, app):
        self.app = app

        if settings.SENTRY_DSN:
            sentry_celery._make_event_processor = self.custom_event_processor
            sentry_sdk.init(
                dsn=self.app.config["SENTRY_DSN"],
                integrations=[sentry_celery.CeleryIntegration()],
            )

    def enrich_tags(self, tags, workflow_id, task):


        with self.app.app_context():
            from workflow.models import Workflow
            workflow_obj = Workflow.objects.get(id=workflow_id)
            workflow = {
                "id": str(workflow_obj.id),
                "project": workflow_obj.project,
                "name": str(workflow_obj),
            }

        tags.update(
            {
                "celery_task_name": task.name,
                "workflow_workflow_id": workflow.get("id"),
                "workflow_workflow_project": workflow.get("project"),
                "workflow_workflow_name": workflow.get("name"),
            }
        )
        return tags

    def enrich_extra(self, extra, args, kwargs):
        extra.update({"workflow-payload": kwargs["payload"], "task-args": args})
        return extra

    def custom_event_processor(self, task, uuid, args, kwargs, request=None):
        """
        This function is the same as the original, except that we
        add custom tags and extras about the workflow object.

        Published under a BSD-2 license and available at:
        https://github.com/getsentry/sentry-python/blob/0.16.3/sentry_sdk/integrations/celery.py#L176
        """

        def event_processor(event, hint):
            with capture_internal_exceptions():
                tags = event.setdefault("tags", {})
                tags["celery_task_id"] = uuid
                extra = event.setdefault("extra", {})
                extra["celery-job"] = {
                    "task_name": task.name,
                    "args": args,
                    "kwargs": kwargs,
                }

                # workflow custom fields (references are used by Sentry,
                # no need to retrieve the new values)
                self.enrich_tags(tags, kwargs["workflow_id"], task)
                self.enrich_extra(extra, args, kwargs)

            if "exc_info" in hint:
                with capture_internal_exceptions():
                    if issubclass(hint["exc_info"][0], SoftTimeLimitExceeded):
                        event["fingerprint"] = [
                            "celery",
                            "SoftTimeLimitExceeded",
                            getattr(task, "name", task),
                        ]

            return event

        return event_processor


# List of extensions
db = SQLAlchemy(
    metadata=MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(column_0_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
)

print("==== workflow Extensions ====")

migrate = Migrate()
schema = JsonSchema()
cel = FlaskCelery("workflow")
cel_workflows = CeleryWorkflow()
sentry = workflowSentry()

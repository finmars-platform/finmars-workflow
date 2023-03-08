import json
import os
import shutil
import traceback
from json.decoder import JSONDecodeError
from pathlib import Path

import yaml
from pluginbase import PluginBase

from workflow.exceptions import SchemaNotFound, SchemaNotValid, WorkflowNotFound
from workflow.storage import get_storage
from workflow.utils import build_celery_schedule
from workflow_app import celery_app
from workflow_app import settings

storage = get_storage()

import logging

_l = logging.getLogger('workflow')


class CeleryWorkflow:
    def __init__(self):

        self.workflows = None

    def init_app(self):

        try:
            _l.info('CeleryWorkflow.init_app')
            # _l.info('settings.BASE_API_URL %s' % settings.BASE_API_URL)

            workflow_path = settings.BASE_API_URL + '/workflows/'

            workflowies, files = storage.listdir(workflow_path)

            self.workflows = {}

            # _l.info('files %s' % files)

            for file in files:

                if '.yml' in file or '.yaml' in file:
                    f = storage.open(workflow_path + '/' + file).read()

                    self.workflows.update(yaml.load(f, Loader=yaml.SafeLoader))

            _l.info("Workflows are loaded")

            _l.info('self.workflows %s' % self.workflows)

            if self.workflows:
                self.load_user_tasks_from_storage_to_local_filesystem()
                self.import_user_tasks()
                self.read_schemas()

        except Exception as e:
            _l.error("CeleryWorkflow.init_app error %s" % e)
            _l.error("CeleryWorkflow.init_app traceback %s" % traceback.format_exc())

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

    def get_before_start_hook_task(self, name):
        return self.get_hook_task(name, "before_start")

    def get_queue(self, name):
        try:
            return self.get_by_name(name)["queue"]
        except KeyError:
            return "workflow"

    def load_user_tasks_from_storage_to_local_filesystem(self):

        try:
            shutil.rmtree(settings.MEDIA_ROOT + '/tasks/')
        except Exception as e:
            _l.error('load_user_tasks_from_storage_to_local_filesystem.e %s' % e)

        workflow_path = settings.BASE_API_URL + '/workflows/tasks/'

        workflowies, files = storage.listdir(workflow_path)

        for filename in files:

            if '.py' in filename:
                _l.info("Going to sync file %s " % filename)

                with storage.open(workflow_path + '/' + filename) as f:
                    f_content = f.read()

                    os.makedirs(os.path.dirname(settings.MEDIA_ROOT + '/tasks/' + filename), exist_ok=True)

                    with open(settings.MEDIA_ROOT + '/tasks/' + filename, 'wb') as new_file:
                        new_file.write(f_content)

    def import_user_tasks(self):
        self.plugin_base = PluginBase(package="workflow.foobar")

        folder = Path(settings.MEDIA_ROOT).resolve()
        self.plugin_source = self.plugin_base.make_plugin_source(
            searchpath=[str(folder)]
        )

        tasks = Path(folder / "tasks").glob("**/*.py")

        # _l.info('tasks %s' % tasks)

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
                    _l.info("Could not load user script %s. Error %s" % (task, e))

        _l.info("Tasks are loaded")

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


def init_periodic_tasks():
    for workflow, conf in celery_workflow.workflows.items():

        # A dict is built for the periodic cleaning if the retention is valid

        if "periodic" in conf:
            periodic_conf = conf.get("periodic")
            periodic_payload = periodic_conf.get("payload", {})
            schedule_str, schedule_value = build_celery_schedule(
                workflow, periodic_conf
            )

            celery_app.conf.beat_schedule.update(
                {
                    f"periodic-{workflow}-{schedule_str}": {
                        "task": "workflow.tasks.workflows.execute",
                        "schedule": schedule_value,
                        "args": (
                            workflow,
                            periodic_payload,
                        ),
                        'options': {'queue': 'workflow'},
                    }
                }
            )

    _l.info('Schedule %s' % celery_app.conf.beat_schedule)


def cancel_existing_tasks():
    from workflow.models import Task
    tasks = Task.objects.filter(status__in=[Task.STATUS_PROGRESS, Task.STATUS_INIT])

    for task in tasks:
        task.status = Task.STATUS_CANCELED

        task.save()

    _l.info("Canceled %s tasks "% len(tasks))


_l.info("==== Load Tasks & Workflow ====")

celery_workflow = CeleryWorkflow()
celery_workflow.init_app()
_l.info("==== Init Periodic Tasks ====")
cancel_existing_tasks()
try:
    init_periodic_tasks()
except Exception as e:
    _l.error("Could not init periodic tasks exception: %s" % e)
    _l.error("Could not init periodic tasks traceback: %s" % traceback.format_exc())

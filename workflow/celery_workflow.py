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
from workflow.utils import build_celery_schedule, construct_path
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

            root_workflows_folder_path = construct_path('/', settings.BASE_API_URL, 'workflows')

            configuration_directories, _ = storage.listdir(root_workflows_folder_path)

            self.workflows = {}

            # _l.info('files %s' % files)

            # We are going through
            # workflows/[configuration_code]/[user_code]/
            # [configuration_code] splits to pieces
            # e.g. com.finmars.local
            # workflows/com/[organization_name][module_name]/[user_code]/

            # and looking for workflow.yaml files

            _l.info("init_app.going to check %s folder" % root_workflows_folder_path)

            for configuration_directory in configuration_directories:

                organization_folder_path = construct_path(root_workflows_folder_path, configuration_directory)
                _l.info(f"init_app.going to check {organization_folder_path} folder")

                organization_directories, _ = storage.listdir(organization_folder_path)

                for organization_directory in organization_directories:

                    module_folder_path = construct_path(organization_folder_path, organization_directory)
                    _l.info(f"init_app.going to check {module_folder_path} folder")

                    modules_directories, _ = storage.listdir(module_folder_path)

                    _l.info('init_app.modules_directories %s' % modules_directories)

                    for module_directory in modules_directories:

                        workflow_folder_path = construct_path(module_folder_path, module_directory)

                        workflow_directories, _ = storage.listdir(workflow_folder_path)

                        _l.info('init_app.workflow_directories %s' % workflow_directories)

                        for workflow_directory in workflow_directories:

                            workflow_yaml_path = construct_path(
                                construct_path(workflow_folder_path, workflow_directory), 'workflow.yaml')

                            _l.info("init_app.Trying to load workflow config file:  %s" % workflow_yaml_path)

                            try:

                                f = storage.open(workflow_yaml_path).read()

                                yaml_config = yaml.load(f, Loader=yaml.SafeLoader)

                                # _l.info('config_user_code %s' % yaml_config['workflow']['user_code'])

                                self.workflows[yaml_config['workflow']['user_code']] = yaml_config

                                _l.info("init_app.loaded: %s" % workflow_yaml_path)
                            except Exception as e:

                                _l.error("init_app. could not load %s" % workflow_yaml_path)
                                _l.error("init_app. could not load error %s" % e)

                                workflow_yaml_path = construct_path(
                                    construct_path(workflow_folder_path, workflow_directory), 'workflow.yml')

                                try:

                                    f = storage.open(workflow_yaml_path).read()

                                    yaml_config = yaml.load(f, Loader=yaml.SafeLoader)

                                    # _l.info('config_user_code %s' % yaml_config['workflow']['user_code'])

                                    self.workflows[yaml_config['workflow']['user_code']] = yaml_config

                                    _l.info("init_app.loaded: %s" % workflow_yaml_path)

                                except Exception as e:

                                    _l.error("init_app. could not load %s" % workflow_yaml_path)
                                    _l.error("init_app. could not load error %s" % e)

            _l.info("init_app.workflows are loaded")

            _l.info('self.workflows %s' % self.workflows)

            if self.workflows:
                self.load_user_tasks_from_storage_to_local_filesystem()
                self.import_user_tasks()
                # self.read_schemas()

        except Exception as e:
            _l.error("CeleryWorkflow.init_app error %s" % e)
            _l.error("CeleryWorkflow.init_app traceback %s" % traceback.format_exc())

    def get_by_user_code(self, user_code):
        workflow = self.workflows.get(user_code)
        if not workflow:
            raise WorkflowNotFound(f"Workflow {user_code} not found")
        return workflow['workflow']

    def get_tasks(self, user_code):
        return self.get_by_user_code(user_code)["tasks"]

    def get_hook_task(self, user_code, hook_name):
        if (
                "hooks" in self.get_by_user_code(user_code)
                and hook_name in self.get_by_user_code(user_code)["hooks"]
        ):
            return self.get_by_user_code(user_code)["hooks"][hook_name]
        return None

    def get_failure_hook_task(self, name):
        return self.get_hook_task(name, "failure")

    def get_success_hook_task(self, name):
        return self.get_hook_task(name, "success")

    def get_before_start_hook_task(self, name):
        return self.get_hook_task(name, "before_start")

    def get_queue(self, user_code):
        try:
            return self.get_by_user_code(user_code)["queue"]
        except KeyError:
            return "workflow"

    def load_user_tasks_from_storage_to_local_filesystem(self):

        try:
            # Remove local-synced Tasks
            shutil.rmtree(settings.MEDIA_ROOT + '/tasks/')
        except Exception as e:
            _l.error('load_user_tasks_from_storage_to_local_filesystem.e %s' % e)

        workflows_folder_path = construct_path('/', settings.BASE_API_URL, 'workflows')

        configuration_directories, _ = storage.listdir(workflows_folder_path)

        for configuration_directory in configuration_directories:

            organization_folder_path = construct_path(workflows_folder_path, configuration_directory)

            organization_directories, _ = storage.listdir(organization_folder_path)

            for organization_directory in organization_directories:

                module_folder_path = construct_path(organization_folder_path, organization_directory)

                modules_directories, _ = storage.listdir(module_folder_path)

                for module_directory in modules_directories:

                    workflow_folder_path = construct_path(module_folder_path, module_directory)

                    workflow_directories, _ = storage.listdir(workflow_folder_path)

                    for workflow_directory in workflow_directories:

                        file_folder_path = construct_path(workflow_folder_path, workflow_directory)

                        _, files = storage.listdir(file_folder_path)

                        for filename in files:

                            if '.py' in filename:
                                filepath = workflows_folder_path + '/' + configuration_directory + '/' + organization_directory + '/' + module_directory + '/' + workflow_directory + '/' + filename

                                _l.info(
                                    "load_user_tasks_from_storage_to_local_filesystem.Going to sync file %s " % filepath)

                                with storage.open(filepath) as f:
                                    f_content = f.read()

                                    os.makedirs(os.path.dirname(os.path.join(settings.MEDIA_ROOT, 'tasks', filepath.lstrip('/'))),
                                                exist_ok=True)

                                    with open(os.path.join(settings.MEDIA_ROOT, 'tasks', filepath.lstrip('/')), 'wb') as new_file:
                                        new_file.write(f_content)

                                _l.info(
                                    "load_user_tasks_from_storage_to_local_filesystem.Going to sync file %s DONE " % filepath)

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

                    _l.info('name %s' % name)

                    __import__(
                        self.plugin_source.base.package + "." + name,
                        globals(),
                        {},
                        ["__name__"],
                    )
                except Exception as e:
                    _l.info("Could not load user script %s. Error %s" % (task, e))

        _l.info("Tasks are loaded")

    # NOT IMPLEMENTED YET
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
    for user_code, config in celery_workflow.workflows.items():

        # A dict is built for the periodic cleaning if the retention is valid

        workflow = config['workflow']

        is_manager = workflow.get('is_manager', False)

        if "periodic" in workflow:
            periodic_conf = workflow.get("periodic")
            periodic_payload = periodic_conf.get("payload", "{}")
            schedule_str, schedule_value = build_celery_schedule(
                user_code, periodic_conf
            )

            celery_app.conf.beat_schedule.update(
                {
                    f"periodic-{user_code}-{schedule_str}": {
                        "task": "workflow.tasks.workflows.execute",
                        "schedule": schedule_value,
                        "args": (
                            user_code,
                            json.loads(periodic_payload),
                            is_manager
                        ),
                        'options': {'queue': 'workflow'},
                    }
                }
            )

    _l.info('Schedule %s' % celery_app.conf.beat_schedule)


def cancel_existing_tasks():
    from workflow.models import Task
    from workflow.models import Workflow
    tasks = Task.objects.filter(status__in=[Task.STATUS_PROGRESS, Task.STATUS_INIT])
    workflows = Workflow.objects.filter(status__in=[Workflow.STATUS_PROGRESS, Workflow.STATUS_INIT])

    for task in tasks:
        task.status = Task.STATUS_CANCELED

        try:  # just in case if rabbitmq still holds a task
            if task.celery_task_id:
                celery_app.control.revoke(task.celery_task_id, terminate=True)

        except Exception as e:
            _l.error("Something went wrong %s" % e)

        task.mark_task_as_finished()

        task.save()

    for workflow in workflows:
        workflow.status = Workflow.STATUS_CANCELED
        workflow.save()

    _l.info("Canceled %s tasks " % len(tasks))


celery_workflow = CeleryWorkflow()

import sys


def init_celery():
    if ('makemigrations' in sys.argv or 'migrate' in sys.argv):
        _l.info("Celery is not inited. Probably Migration context")
    else:
        _l.info("==== Load Tasks & Workflow ====")

        celery_workflow.init_app()

        try:
            _l.info("==== Cancel Existing Tasks ====")
            # cancel_existing_tasks() # IMPORTANT do not execute it here, it breaks running tasks, when worker respawned
        except Exception as e:
            _l.error("Could not cancel_existing_tasks exception: %s" % e)
            _l.error("Could not cancel_existing_tasks traceback: %s" % traceback.format_exc())
        try:
            _l.info("==== Init Periodic Tasks ====")
            init_periodic_tasks()
        except Exception as e:
            _l.error("Could not init periodic tasks exception: %s" % e)
            _l.error("Could not init periodic tasks traceback: %s" % traceback.format_exc())


try:

    init_celery()

except Exception as e:
    _l.error("Could not init_celery exception: %s" % e)
    _l.error("Could not init_celery traceback: %s" % traceback.format_exc())

    raise Exception(e)
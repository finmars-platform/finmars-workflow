import fnmatch
import importlib
import json
import os
import shutil
import sys
import traceback
from pathlib import Path

from django.db import connection

import yaml
from pluginbase import PluginBase

from workflow.exceptions import WorkflowNotFound
from workflow.models import Space
from workflow.storage import get_storage
from workflow.utils import build_celery_schedule, construct_path, get_all_tenant_schemas
from workflow_app import celery_app, settings

storage = get_storage()

import logging

_l = logging.getLogger("workflow")


class SystemWorkflowManager:
    def __init__(self):
        self.workflows = {}

    def register_workflows(self, space_code=None):

        schemas = get_all_tenant_schemas()

        if space_code:
            if space_code.lower() not in schemas:
                raise Exception(f"Schema '{space_code}' does not exist")
            schemas = [space_code]

        for schema in schemas:

            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema};")

            _l.info(f"Loading workflows for schema: {schema}")

            self.load_workflows_for_schema(schema)

        if not space_code:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO public;")

    def sync_remote_storage_to_local_storage(self, space_code=None):

        schemas = get_all_tenant_schemas()

        if space_code:
            if space_code.lower() not in schemas:
                raise Exception(f"Schema '{space_code}' does not exist")
            schemas = [space_code]

        for schema in schemas:

            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema};")

            _l.info(f"Sync storage files for schema: {schema}")

            self.sync_remote_storage_to_local_storage_for_schema()

            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO public;")

    def load_workflows_for_schema(self, schema):
        try:

            space = Space.objects.all().first()
            # Construct the root path for workflows
            local_workflows_folder_path = construct_path(
                settings.WORKFLOW_STORAGE_ROOT, "local", space.space_code, "workflows"
            )

            # Use Pathlib to simplify path manipulations
            root_path = Path(local_workflows_folder_path)

            _l.info("local_workflows_folder_path %s" % local_workflows_folder_path)

            # Iterate through all files in the /workflows directory and subdirectories
            for workflow_file in root_path.glob("**/workflow.*"):

                _l.debug("workflow_file %s" % workflow_file)

                if workflow_file.suffix in [".yaml", ".yml", ".json"]:
                    try:
                        with open(str(workflow_file), "r") as f:
                            if workflow_file.suffix in [".yaml", ".yml"]:
                                config = yaml.load(f, Loader=yaml.SafeLoader)
                            elif workflow_file.suffix == ".json":
                                config = json.load(f)
                            else:
                                _l.warning(f"Unsupported file format: {workflow_file}")
                                continue

                        user_code = config["workflow"]["user_code"]

                        config["workflow"]["realm_code"] = space.realm_code
                        config["workflow"]["space_code"] = space.space_code

                        self.workflows[space.space_code + "." + user_code] = config
                        _l.debug(
                            f"Loaded workflow for user code: {space.space_code}.{user_code}"
                        )

                    except Exception as e:
                        _l.warning(
                            f"Could not load workflow config file: {workflow_file} - {e}"
                        )
                else:
                    _l.debug(f"Skipped unsupported file format: {workflow_file}")

        except Exception as e:
            _l.error(f"Error loading workflows for schema {schema}: {e}")

    def get_by_user_code(self, user_code, sync_remote=False):
        workflow = self.workflows.get(user_code)

        if not workflow and sync_remote:
            space_code = user_code.split(".")[0]
            path = user_code[len(space_code) + 1 :].replace(".", "/").replace(":", "/")
            module_path, _ = path.rsplit("/", maxsplit=1)
            self.sync_remote_storage_to_local_storage_for_schema(module_path)
            self.register_workflows(space_code)
            workflow = self.workflows.get(user_code)

        if not workflow:
            raise WorkflowNotFound(f"Workflow {user_code} not found")
        return workflow["workflow"]

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

    def get_imports(self, user_code):
        return self.get_by_user_code(user_code).get("imports")

    def sync_remote_storage_to_local_storage_for_schema(
        self, module_path="", patterns=("*.yaml", "*.yml", "*.json", "*.py")
    ):

        space = Space.objects.all().first()

        remote_workflows_folder_path = construct_path(space.space_code, "workflows")
        local_workflows_folder_path = construct_path(
            settings.WORKFLOW_STORAGE_ROOT,
            "local",
            space.space_code,
            "workflows",
            module_path,
        )

        # Check if the local workflows directory exists before attempting to remove it
        if os.path.exists(local_workflows_folder_path):
            _l.info(
                f"Removing local workflows directory: {local_workflows_folder_path}"
            )
            try:
                shutil.rmtree(local_workflows_folder_path)
                _l.info(
                    "====[CLEAR DIRECTORY]==== Successfully removed local workflows directory."
                )
            except Exception as e:
                _l.error(f"Failed to remove local workflows directory: {e}")
        else:
            _l.info(
                f"Local workflows directory does not exist, no need to remove: {local_workflows_folder_path}"
            )

        _l.info(
            "remote_workflows_folder_path %s"
            % construct_path(remote_workflows_folder_path, module_path)
        )

        module_path_components = []
        if module_path:
            module_path_components = module_path.split("/")

        configuration_directories, _ = storage.listdir(remote_workflows_folder_path)
        count = 0

        for configuration_directory in configuration_directories:
            if (
                len(module_path_components) > 0
                and configuration_directory != module_path_components[0]
            ):
                continue
            organization_folder_path = construct_path(
                remote_workflows_folder_path, configuration_directory
            )
            organization_directories, _ = storage.listdir(organization_folder_path)

            for organization_directory in organization_directories:
                if (
                    len(module_path_components) > 1
                    and organization_directory != module_path_components[1]
                ):
                    continue
                module_folder_path = construct_path(
                    organization_folder_path, organization_directory
                )
                modules_directories, _ = storage.listdir(module_folder_path)

                for module_directory in modules_directories:
                    if (
                        len(module_path_components) > 2
                        and module_directory != module_path_components[2]
                    ):
                        continue
                    workflow_folder_path = construct_path(
                        module_folder_path, module_directory
                    )
                    workflow_directories, _ = storage.listdir(workflow_folder_path)

                    for workflow_directory in workflow_directories:
                        if (
                            len(module_path_components) > 3
                            and workflow_directory != module_path_components[3]
                        ):
                            continue
                        file_folder_path = construct_path(
                            workflow_folder_path, workflow_directory
                        )
                        _, files = storage.listdir(file_folder_path)

                        # _l.info("sync_remote_storage_to_local_storage_for_schema.files %s" % files)

                        for filename in files:
                            try:
                                filepath = (
                                    remote_workflows_folder_path
                                    + "/"
                                    + configuration_directory
                                    + "/"
                                    + organization_directory
                                    + "/"
                                    + module_directory
                                    + "/"
                                    + workflow_directory
                                    + "/"
                                    + filename
                                )

                                # Log the file syncing
                                # _l.info(f"Syncing file: {filepath}")

                                if any(
                                    fnmatch.fnmatch(filename, pattern)
                                    for pattern in patterns
                                ):

                                    with storage.open(filepath) as f:
                                        f_content = f.read()

                                        # Probably some error here, refactor later
                                        # Should pointing just to space_code directory, not to tasks
                                        local_path = os.path.join(
                                            settings.WORKFLOW_STORAGE_ROOT,
                                            "local",
                                            filepath.lstrip("/"),
                                        )
                                        os.makedirs(
                                            os.path.dirname(local_path), exist_ok=True
                                        )

                                        with open(local_path, "wb") as new_file:
                                            new_file.write(f_content)

                                        count = count + 1

                            except Exception as e:
                                _l.error(f"Could not sync file: {filename} - {e}")
                                # _l.info("load_user_tasks_from_storage_to_local_filesystem.Going to sync file %s DONE " % filepath)

        _l.info(
            "sync_remote_storage_to_local_storage_for_schema.Done syncing %s files"
            % count
        )

    def import_user_tasks(self, workflow_path="**", raise_exception=False):
        self.plugin_base = PluginBase(package="workflow.foobar")

        space = Space.objects.all().first()

        local_workflows_folder_path = construct_path(
            settings.WORKFLOW_STORAGE_ROOT, "local", space.space_code, "workflows"
        )

        folder = Path(local_workflows_folder_path).resolve()

        _l.info("import_user_tasks %s" % local_workflows_folder_path)

        self.plugin_source = self.plugin_base.make_plugin_source(
            searchpath=[str(folder)]
        )

        tasks = Path(folder).glob(f"{workflow_path}/*.py")

        # _l.info('tasks %s' % tasks)

        for task in tasks:
            if task.stem == "__init__":
                continue
            module_name = (
                str(task.relative_to(folder)).replace("/", ".").rsplit(".", 1)[0]
            )

            try:
                # Load the module with a specific and isolated namespace
                spec = importlib.util.spec_from_file_location(module_name, task)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = (
                    module  # Optional: register to sys.modules if needed globally
                )
                spec.loader.exec_module(module)
            except Exception as e:
                _l.info(f"Could not load user script {task}. Error {e}")
                if raise_exception:
                    raise e

        # with self.plugin_source:
        #     for task in tasks:
        #
        #         try:
        #
        #             if task.stem == "__init__":
        #                 continue
        #
        #             name = str(task.relative_to(folder))[:-3].replace("/", ".")
        #
        #             # _l.info('name %s' % name)
        #
        #             __import__(
        #                 self.plugin_source.base.package + "." + name,
        #                 globals(),
        #                 {},
        #                 ["__name__"],
        #             )
        #         except Exception as e:
        #             _l.info("Could not load user script %s. Error %s" % (task, e))

        _l.info("Tasks are loaded")

    def cancel_all_existing_tasks(self, worker_name):
        from workflow.models import Task, Workflow

        # find workflows through tasks
        tasks = Task.objects.filter(
            status__in=[Task.STATUS_PROGRESS, Task.STATUS_INIT], worker_name=worker_name
        )
        workflow_ids = [task.workflow_id for task in tasks]
        workflows = Workflow.objects.filter(
            status__in=[Workflow.STATUS_PROGRESS, Workflow.STATUS_INIT],
            id__in=workflow_ids,
        )
        for workflow in workflows:
            workflow.cancel()

        # now find tasks without workflows
        tasks = Task.objects.filter(
            status__in=[Task.STATUS_PROGRESS, Task.STATUS_INIT], worker_name=worker_name
        )
        for task in tasks:
            task.status = Task.STATUS_CANCELED

            try:  # just in case if rabbitmq still holds a task
                if task.celery_task_id:
                    celery_app.control.revoke(task.celery_task_id, terminate=True)

            except Exception as e:
                _l.error("Something went wrong %s" % e)

            task.mark_task_as_finished()

            task.save()

        _l.info("Canceled %s tasks " % len(tasks))

    def init_periodic_tasks(self):

        for user_code, config in self.workflows.items():

            # A dict is built for the periodic cleaning if the retention is valid

            workflow = config["workflow"]

            is_manager = workflow.get("is_manager", False)

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
                                is_manager,
                            ),
                            "kwargs": {
                                "context": {
                                    "realm_code": workflow["realm_code"],
                                    "space_code": workflow["space_code"],
                                }
                            },
                            "options": {"queue": "workflow"},
                        }
                    }
                )

        _l.info("Schedule %s" % celery_app.conf.beat_schedule)


system_workflow_manager = None


def get_system_workflow_manager():
    global system_workflow_manager

    if system_workflow_manager is None:
        system_workflow_manager = SystemWorkflowManager()

    return system_workflow_manager

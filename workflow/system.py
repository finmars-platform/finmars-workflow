import json
import os
import shutil
import sys
import traceback
from pathlib import Path

import yaml

from pluginbase import PluginBase

from workflow.exceptions import WorkflowNotFound
from workflow.models import Space
from workflow.storage import get_storage
from workflow.utils import build_celery_schedule, construct_path, get_all_tenant_schemas
from workflow_app import celery_app
from workflow_app import settings
from django.db import connection




storage = get_storage()

import logging

_l = logging.getLogger('workflow')

class SystemWorkflowManager:
    def __init__(self):
        self.workflows = {}

    def register_workflows_all_schemas(self):

        schemas = get_all_tenant_schemas()
        for schema in schemas:

            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema};")

            _l.info(f'Loading workflows for schema: {schema}')

            self.load_workflows_for_schema(schema)

            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO public;")

        # Initialize periodic tasks after loading all workflows
        self.init_periodic_tasks()

    def sync_remote_storage_to_local_storage_all_schemas(self):

        schemas = get_all_tenant_schemas()
        for schema in schemas:

            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema};")

            _l.info(f'Sync storage files for schema: {schema}')

            self.sync_remote_storage_to_local_storage_for_schema()

            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO public;")

    def load_workflows_for_schema(self, schema):
        try:

            space = Space.objects.all().first()
            # Construct the root path for workflows
            local_workflows_folder_path = construct_path(settings.MEDIA_ROOT, 'local', space.space_code, 'workflows')

            # Use Pathlib to simplify path manipulations
            root_path = Path(local_workflows_folder_path)

            _l.info('local_workflows_folder_path %s' % local_workflows_folder_path)

            # Iterate through all files in the /workflows directory and subdirectories
            for workflow_file in root_path.glob('**/*'):

                _l.debug('workflow_file %s' % workflow_file)

                if workflow_file.suffix in ['.yaml', '.yml', '.json']:
                    try:
                        with open(str(workflow_file), 'r') as f:
                            if workflow_file.suffix in ['.yaml', '.yml']:
                                config = yaml.load(f, Loader=yaml.SafeLoader)
                            elif workflow_file.suffix == '.json':
                                config = json.load(f)
                            else:
                                _l.warning(f"Unsupported file format: {workflow_file}")
                                continue

                        user_code = config['workflow']['user_code']

                        config['workflow']['realm_code'] = space.realm_code
                        config['workflow']['space_code'] = space.space_code

                        self.workflows[space.space_code + '.' + user_code] = config
                        _l.debug(f"Loaded workflow for user code: {space.space_code}.{user_code}")

                    except Exception as e:
                        _l.error(f"Could not load workflow config file: {workflow_file} - {e}")
                else:
                    _l.debug(f"Skipped unsupported file format: {workflow_file}")

            if self.workflows:
                # _l.info('workflows %s' % self.workflows)
                self.import_user_tasks()

        except Exception as e:
            _l.error(f"Error loading workflows for schema {schema}: {e}")

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

    def sync_remote_storage_to_local_storage_for_schema(self):

        space = Space.objects.all().first()

        remote_workflows_folder_path = construct_path(space.space_code, 'workflows')
        local_workflows_folder_path = construct_path(settings.MEDIA_ROOT, 'local',  space.space_code, 'workflows')

        # Check if the local workflows directory exists before attempting to remove it
        if os.path.exists(local_workflows_folder_path):
            _l.info(f"Removing local workflows directory: {local_workflows_folder_path}")
            try:
                shutil.rmtree(local_workflows_folder_path)
                _l.info("====[CLEAR DIRECTORY]==== Successfully removed local workflows directory.")
            except Exception as e:
                _l.error(f"Failed to remove local workflows directory: {e}")
        else:
            _l.info(f"Local workflows directory does not exist, no need to remove: {local_workflows_folder_path}")

        _l.info('remote_workflows_folder_path %s' % remote_workflows_folder_path)

        configuration_directories, _ = storage.listdir(remote_workflows_folder_path)

        count = 0

        for configuration_directory in configuration_directories:

            organization_folder_path = construct_path(remote_workflows_folder_path, configuration_directory)

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

                        # _l.info("sync_remote_storage_to_local_storage_for_schema.files %s" % files)

                        for filename in files:
                            try:
                                filepath = remote_workflows_folder_path + '/' + configuration_directory + '/' + organization_directory + '/' + module_directory + '/' + workflow_directory + '/' + filename

                                # Log the file syncing
                                # _l.info(f"Syncing file: {filepath}")

                                if filename.endswith('.yaml') or filename.endswith('.yml') or filename.endswith('.json') or filename.endswith('.py'):

                                    with storage.open(filepath) as f:
                                        f_content = f.read()

                                        # Probably some error here, refactor later
                                        # Should pointing just to space_code directory, not to tasks
                                        local_path = os.path.join(settings.MEDIA_ROOT, 'local', filepath.lstrip('/'))
                                        os.makedirs(os.path.dirname(local_path), exist_ok=True)

                                        with open(local_path, 'wb') as new_file:
                                            new_file.write(f_content)

                                        count = count + 1

                            except Exception as e:
                                _l.error(f"Could not sync file: {filename} - {e}")
                                    # _l.info("load_user_tasks_from_storage_to_local_filesystem.Going to sync file %s DONE " % filepath)

        _l.info("sync_remote_storage_to_local_storage_for_schema.Done syncing %s files" % count)

    def import_user_tasks(self):
        self.plugin_base = PluginBase(package="workflow.foobar")

        folder = Path(settings.MEDIA_ROOT).resolve()

        self.plugin_source = self.plugin_base.make_plugin_source(
            searchpath=[str(folder)]
        )

        tasks = Path(folder / "local").glob("**/*.py")

        # _l.info('tasks %s' % tasks)

        with self.plugin_source:
            for task in tasks:

                try:

                    if task.stem == "__init__":
                        continue

                    name = str(task.relative_to(folder))[:-3].replace("/", ".")

                    # _l.info('name %s' % name)

                    __import__(
                        self.plugin_source.base.package + "." + name,
                        globals(),
                        {},
                        ["__name__"],
                    )
                except Exception as e:
                    _l.info("Could not load user script %s. Error %s" % (task, e))

        _l.info("Tasks are loaded")

    def cancel_all_existing_tasks(self):
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

    def init_periodic_tasks(self):

        for user_code, config in self.workflows.items():

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


system_workflow_manager = None

def get_system_workflow_manager():
    global system_workflow_manager

    if system_workflow_manager is None:
        system_workflow_manager = SystemWorkflowManager()

    return system_workflow_manager

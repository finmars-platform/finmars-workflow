import os.path
import time
import traceback

from celery import chain
from celery.utils import uuid
from celery.utils.log import get_task_logger
from django.db import connection

from workflow.models import Task, Workflow, User, Space
from workflow.tasks.base import BaseTask
from workflow.utils import schema_exists, set_schema_from_context
from workflow_app import celery_app

logger = get_task_logger(__name__)
import logging

_l = logging.getLogger('workflow')

@celery_app.task(bind=True)
def ping(self):
    # type: () -> str
    """Simple task that just returns 'pong'."""
    return "pong"


@celery_app.task(bind=True)
def start(self, workflow_id, *args, **kwargs):

    context = kwargs.get('context')
    set_schema_from_context(context)

    logger.info(f"Opening the workflow {workflow_id}")
    workflow = Workflow.objects.get(id=workflow_id)

    workflow.status = Workflow.STATUS_PROGRESS
    workflow.save()


@celery_app.task(bind=True)
def end(self, workflow_id, *args, **kwargs):
    # Waiting for the workflow status to be marked in error if a task failed
    time.sleep(0.5)

    context = kwargs.get('context')
    set_schema_from_context(context)

    logger.info(f"Closing the workflow {workflow_id}")
    workflow = Workflow.objects.get(id=workflow_id)

    if workflow.status != Workflow.STATUS_ERROR:
        workflow.status = Workflow.STATUS_SUCCESS
        workflow.save()


@celery_app.task(bind=True)
def mark_as_canceled_init_tasks(self, workflow_id, *args, **kwargs):
    logger.info(f"Mark as cancelled pending tasks of the workflow {workflow_id}")

    context = kwargs.get('context')
    set_schema_from_context(context)

    tasks = Task.objects.filter(workflow_id=workflow_id, status=Task.STATUS_INIT)
    for task in tasks:
        task.status = Task.STATUS_CANCELED
        task.mark_task_as_finished()
        task.save()


@celery_app.task(bind=True)
def failure_hooks_launcher(self, workflow_id, queue, tasks_names, payload, *args, **kwargs):
    logger.info('failure_hooks_launcher %s' % workflow_id)

    context = kwargs.get('context')
    set_schema_from_context(context)

    canvas = []

    for task_name in tasks_names:
        task_id = uuid()

        # We create the Celery task specifying its UID
        signature = celery_app.tasks.get(task_name).subtask(
            kwargs={"workflow_id": workflow_id, "payload": payload, "context": context},
            queue='workflow',
            task_id=task_id,
        )

        # workflow task has the same UID
        task = Task(
            celery_task_id=task_id,
            name=task_name,
            workflow_id=workflow_id,
            status=Task.STATUS_INIT,
            is_hook=True,
        )
        task.save()

        logger.info('failure_hooks_launcher.task %s' % task)

        canvas.append(signature)

    canvas = chain(*canvas, task_id=uuid())

    result = canvas.apply_async()

    if result.ready():
        try:
            result.get()
        except Exception as e:
            logger.error("failure_hooks_launcher.result.get e %s" % e)
            pass

    logger.info("Going to cancel init tasks")

    task_id = uuid()
    signature_mark_as_canceled = celery_app.tasks.get(
        "workflow.tasks.workflows.mark_as_canceled_init_tasks"
    ).subtask(
        kwargs={"workflow_id": workflow_id},
        queue='workflow',
        task_id=task_id,
    )

    logger.info('signature_mark_as_canceled %s' % signature_mark_as_canceled)

    signature_mark_as_canceled.apply_async()


# Neede in Schedules
# class Schedule(PeriodicTask, TimeStampedModel):
# def save(self, *args, **kwargs):
#     self.queue = "workflow"
#     self.task = "workflow.tasks.workflows.execute"

@celery_app.task(bind=True)
def execute(self, user_code, payload, is_manager, *args, **kwargs):
    from workflow.system import get_system_workflow_manager
    manager = get_system_workflow_manager()

    try:

        logger.info("periodic.execute %s" % user_code)

        context = kwargs.get('context')

        set_schema_from_context(context)

        finmars_bot = User.objects.get(username='finmars_bot')
        space = Space.objects.get(space_code=context.get('space_code'))

        c_obj = Workflow(owner=finmars_bot, space=space, user_code=user_code, payload=payload, periodic=True,
                         is_manager=is_manager, crontab_id=kwargs.get('crontab_id'))
        c_obj.save()

        manager.get_by_user_code(user_code, sync_remote=True)

        # Build the workflow and execute it
        from workflow.builder import WorkflowBuilder
        workflow = WorkflowBuilder(c_obj.id)
        workflow.run()

        c_obj_dict = c_obj.to_dict()
        #
        # # Force commit before ending the function to ensure the ongoing transaction
        # # does not end up in a "idle in transaction" state on PostgreSQL
        # c_obj.commit()

        return c_obj_dict

    except Exception as e:
        logger.error('periodic task error: %s' % e, exc_info=True)


@celery_app.task(bind=True, base=BaseTask)
def execute_workflow_step(self, *args, **kwargs):
    from workflow.api import get_registered_task, clear_registered_task
    from workflow.system import get_system_workflow_manager

    clear_registered_task()
    manager = get_system_workflow_manager()

    context = kwargs.get('context')
    set_schema_from_context(context)

    path = self.task.name
    if path.endswith('.task'):
        path = path[:-5]
    module_path = path.replace('.', '/').replace(':', '/')

    manager.sync_remote_storage_to_local_storage_for_schema(module_path)
    manager.import_user_tasks(module_path, raise_exception=True)

    imports = kwargs.get('imports') or {}
    if isinstance(imports, dict):
        imports = imports.get('dirs')
    if isinstance(imports, list):
        for extra_path in imports:
            extra_path = os.path.normpath(os.path.join(module_path, extra_path))
            last_segment = extra_path.split('/')[-1]
            if '*' in last_segment or '?' in last_segment:
                # given a wildcard for file name
                extra_path, pattern = extra_path.rsplit('/', maxsplit=1)
            else:
                pattern = '*.*'
            manager.sync_remote_storage_to_local_storage_for_schema(extra_path, [pattern])

    func = get_registered_task()
    if func:
        logger.info('executing %s', func.__name__)
        result = func(self, *args, **kwargs)
        return result
    else:
        raise Exception(f'no function to execute for {self.task.name}')


@celery_app.task(bind=True)
def execute_dynamic_workflow(self, *args, **kwargs):
    logger.info(f"Opening the workflow with ID: {kwargs.get('workflow_id', None)}")

    # Log the context passed to the workflow
    context = kwargs.get('context')
    logger.info(f"Workflow context received: {context}")
    set_schema_from_context(context)

    # Get workflow from database
    workflow_id = kwargs.get('workflow_id')
    workflow = Workflow.objects.get(id=workflow_id)
    logger.info(f"Workflow fetched from database: {workflow}")

    # Update workflow status to in-progress
    workflow.status = Workflow.STATUS_PROGRESS
    workflow.save()
    logger.info(f"Workflow status updated to: {workflow.status}")

    # Log workflow data to get steps and connections
    workflow_data = workflow.workflow_template.data
    logger.info(f"Workflow data loaded: {workflow_data}")

    nodes = {node['id']: node for node in workflow_data['workflow']['nodes']}
    connections = workflow_data['workflow']['connections']

    # Log nodes and connections
    logger.info(f"Nodes parsed from workflow data: {nodes}")
    logger.info(f"Connections parsed from workflow data: {connections}")

    # Create an adjacency list for connections
    adjacency_list = {node_id: [] for node_id in nodes}
    for connection in connections:
        adjacency_list[connection['source']].append(connection['target'])

    # Log the adjacency list for debugging purposes
    logger.info(f"Adjacency list created: {adjacency_list}")

    # Start from nodes without incoming edges (root nodes)
    start_nodes = [node_id for node_id in nodes if not any(node_id == conn['target'] for conn in connections)]
    logger.info(f"Start nodes determined: {start_nodes}")

    # Execute tasks from start nodes
    for start_node in start_nodes:
        logger.info(f"Dispatching task for start node: {start_node}")

        execute_next_task.apply_async(kwargs={
            "current_node_id": start_node,
            "workflow_id": workflow_id,
            "nodes": nodes,
            "adjacency_list": adjacency_list,
            "context": context
        }, queue="workflow")

    logger.info("All start nodes have been dispatched.")


@celery_app.task(bind=True)
def execute_next_task(self, current_node_id, workflow_id, nodes, adjacency_list, previous_output=None, **kwargs):

    context = kwargs.get('context')
    logger.info(f"execute_next_task context received: {context}")
    set_schema_from_context(context)

    try:

        # Fetch workflow and task information
        logger.info(f"Fetching workflow with ID: {workflow_id}")
        workflow = Workflow.objects.get(id=workflow_id)
        current_node = nodes[current_node_id]
        task_name = current_node['data']['user_code']

        logger.info(f"Executing task for Node ID: {current_node_id}, Task Name: {task_name}")

        # Create Celery signature for the current task
        task_id = uuid()
        signature = execute_workflow_step.s(
            workflow_id=workflow.id,
            payload=workflow.payload,
            context={
                "realm_code": workflow.space.realm_code,
                "space_code": workflow.space.space_code,
            },
            imports=None,
            previous_output=previous_output
        ).set(task_id=task_id)

        # Create a Task object for tracking purposes
        task = Task(
            celery_task_id=task_id,
            name=task_name,
            workflow_id=workflow.id,
            node_id=current_node_id,
            status=Task.STATUS_INIT,
            space=workflow.space
        )
        task.save()

        # Run the task synchronously and get the result
        result = signature.apply()  # Execute the task and get the result immediately
        output = result.result  # This is the output from execute_workflow_step

        # TODO, szhitenev
        # important, somehow context is changed after execute_workflow_step
        # research later
        context = kwargs.get('context')
        set_schema_from_context(context)

        logger.info(f"Task {task_name} executed successfully, result: {output}")

        # Check for next nodes to execute
        # what if two branches in parallel and one finished before other?
        # TODO szhitenev
        next_node_ids = adjacency_list.get(current_node_id, [])
        if not next_node_ids:
            logger.info(f"No next nodes found for current node ID: {current_node_id}. Marking workflow as complete.")

            logger.info(f'workflow owner {workflow.owner}')
            # If there are no next nodes, update the workflow status to SUCCESS
            workflow.status = Workflow.STATUS_SUCCESS
            workflow.save()
            logger.info(f"Workflow ID {workflow.id} status updated to SUCCESS.")
            return

        # Decide what the next step will be, based on the current task's output
        for next_node_id in next_node_ids:
            next_node = nodes.get(next_node_id)
            if not next_node:
                logger.error(f"Next node with ID {next_node_id} does not exist in the workflow nodes.")
                continue

            logger.info(f"Processing next node: {next_node_id}, Name: {next_node['name']}")

            # Execute the next task recursively by calling `execute_next_task` again
            execute_next_task.apply_async(kwargs={
                "current_node_id": next_node_id,
                "workflow_id": workflow_id,
                "nodes": nodes,
                "adjacency_list": adjacency_list,
                "previous_output": output,
                "context": kwargs.get('context')
            }, queue="workflow")

    except Exception as e:
        logger.error(f"Error executing task : {e}")




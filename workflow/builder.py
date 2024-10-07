import logging

from celery import chain, group
from celery.utils import uuid

from workflow.exceptions import WorkflowSyntaxError
from workflow.models import Workflow, Task
from workflow.tasks.workflows import start, end, failure_hooks_launcher, execute_workflow_step
from workflow_app import celery_app

_l = logging.getLogger('workflow')

from workflow.system import get_system_workflow_manager

system_workflow_manager = get_system_workflow_manager()


class WorkflowBuilder(object):
    def __init__(self, workflow_id, workflow_data):
        self.workflow_id = workflow_id
        self._workflow = None
        self.workflow_data = workflow_data  # Pass in the workflow data (which might have a version)


    @property
    def workflow(self):
        if not self._workflow:
            self._workflow = Workflow.objects.get(id=self.workflow_id)
        return self._workflow

    def new_task(self, task_name, is_hook=False, single=True, node_id=None):
        task_id = uuid()

        prefixed_name = self.workflow.space.space_code + '.' + task_name
        queue = self.custom_queues.get(prefixed_name, self.queue)

        signature = execute_workflow_step.subtask(
            kwargs={
                "workflow_id": self.workflow_id,
                "payload": self.workflow.payload,
                "context": {
                    "realm_code": self.workflow.space.realm_code,
                    "space_code": self.workflow.space.space_code,
                },
                "imports": self.imports
            },
            queue=queue,
            task_id=task_id,
        )

        task = Task(
            celery_task_id=task_id,
            name=task_name,
            previous=self.previous,
            workflow_id=self.workflow.id,
            node_id=node_id,
            status=Task.STATUS_INIT,
            space=self._workflow.space,
            is_hook=is_hook,
        )
        task.save()

        if single:
            self.previous = [signature.id]

        return signature

    def parse_queues(self):
        if isinstance(self.queue, dict):
            self.custom_queues = self.queue.get("customs", {})
            self.queue = self.queue.get("default", "celery")
        if not isinstance(self.queue, str) or not isinstance(self.custom_queues, dict):
            raise WorkflowSyntaxError()

    def parse_connections(self):
        """
        Parse connections from Rete.js JSON structure (version 2) to determine the order of execution.
        """
        workflow = self.workflow_data['workflow']
        nodes = {node['id']: node for node in workflow['nodes']}
        connections = workflow['connections']

        # Step 1: Build adjacency list from connections
        adjacency_list = {}
        incoming_count = {}

        # Initialize adjacency list and incoming count for all nodes
        for node_id in nodes.keys():
            adjacency_list[node_id] = []
            incoming_count[node_id] = 0

        # Fill in adjacency list and incoming count based on connections
        for connection in connections:
            source = connection['source']
            target = connection['target']
            adjacency_list[source].append(target)
            incoming_count[target] += 1

        # Step 2: Find all nodes with no incoming connections (start nodes)
        start_nodes = [node_id for node_id, count in incoming_count.items() if count == 0]

        # Step 3: Use Kahn’s algorithm for topological sorting
        sorted_order = []
        queue = start_nodes[:]

        while queue:
            current_node = queue.pop(0)
            sorted_order.append(current_node)

            for neighbor in adjacency_list[current_node]:
                incoming_count[neighbor] -= 1
                if incoming_count[neighbor] == 0:
                    queue.append(neighbor)

        # Step 4: Add any unprocessed nodes (disconnected nodes)
        all_node_ids = set(nodes.keys())
        processed_node_ids = set(sorted_order)

        _l.info('all_node_ids %s' % all_node_ids)
        _l.info('processed_node_ids %s' % processed_node_ids)

        # Find nodes that are not in the sorted order (i.e., disconnected nodes)
        disconnected_nodes = all_node_ids - processed_node_ids

        # Add disconnected nodes to the sorted order
        sorted_order.extend(disconnected_nodes)

        # Step 5: Create task connections dictionary with user_codes
        task_connections = []

        for node_id in sorted_order:
            node = nodes[node_id]
            task_connections.append({
                'id': node_id,
                'name': node['name'],
                'user_code': node['data']['user_code'],
                'connections': adjacency_list[node_id]
            })

        return task_connections

    def build_canvas_from_connections(self, task_connections):
        canvas = []

        # Traverse tasks in the sorted order to build the canvas
        for task in task_connections:
            node_id = task['id']
            task_name = task['name']
            user_code = task['user_code']

            # Add the current task to the canvas
            signature = self.new_task(user_code, node_id=node_id)
            canvas.append(signature)

        return canvas

    def parse_flat_tasks(self, tasks, is_hook=False):
        """
        Parse tasks from the older flat structure (version 1).
        """
        canvas = []

        for task in tasks:
            if isinstance(task, str):
                signature = self.new_task(task, is_hook)
                canvas.append(signature)
            elif isinstance(task, dict):
                name = list(task)[0]
                if "type" not in task[name] and task[name]["type"] != "group":
                    raise WorkflowSyntaxError()

                sub_canvas_tasks = [
                    self.new_task(t, is_hook, single=False) for t in task[name]["tasks"]
                ]

                sub_canvas = group(*sub_canvas_tasks, task_id=uuid())
                canvas.append(sub_canvas)
                self.previous = [s.id for s in sub_canvas_tasks]
            else:
                raise WorkflowSyntaxError()

        return canvas

    def build(self):

        self.custom_queues = {}

        self.canvas = []
        self.previous = []

        # Retrieve general task and queue information
        self.queue = system_workflow_manager.get_queue(str(self.workflow))
        self.tasks = system_workflow_manager.get_tasks(str(self.workflow))


        # Initialize hooks
        self.failure_hook = system_workflow_manager.get_failure_hook_task(str(self.workflow))
        self.failure_hook_canvas = []

        self.success_hook = system_workflow_manager.get_success_hook_task(str(self.workflow))
        self.success_hook_canvas = []

        self.before_start_hook = system_workflow_manager.get_before_start_hook_task(str(self.workflow))

        self.parse_queues()

        self.imports = system_workflow_manager.get_imports(str(self.workflow))

        # Check the version of the workflow and build accordingly
        if self.workflow_data.get("version") == "2":
            # Version 2: Use the DAG-based approach with connections
            task_connections = self.parse_connections()
            _l.info('task_connections %s' % task_connections)
            self.canvas = self.build_canvas_from_connections(task_connections)
        else:

            # Version 1: Use the older flat list of tasks approach
            self.canvas = self.parse_flat_tasks(self.tasks)

        # Add Before-Start Hook if present
        if self.before_start_hook:
            initial_previous = self.previous
            self.previous = None
            self.before_start_hook_canvas = self.parse_flat_tasks([self.before_start_hook], True)[0]

            _l.info(f'Before start hook canvas: {self.before_start_hook_canvas}')

            self.canvas.insert(0, self.before_start_hook_canvas.set(queue=self.queue))
            self.previous = initial_previous

        # Add Workflow Start
        self.canvas.insert(0, start.si(self.workflow.id, context={
            "realm_code": self.workflow.space.realm_code,
            "space_code": self.workflow.space.space_code,
        }).set(queue=self.queue))

        # Add Workflow End
        self.canvas.append(end.si(self.workflow.id, context={
            "realm_code": self.workflow.space.realm_code,
            "space_code": self.workflow.space.space_code,
        }).set(queue=self.queue))

    def build_hooks(self):
        initial_previous = self.previous

        # Failure Hook
        if self.failure_hook and not self.failure_hook_canvas:
            self.previous = None
            self.failure_hook_canvas = [
                failure_hooks_launcher.si(
                    self.workflow.id,
                    self.queue,
                    [self.failure_hook],
                    self.workflow.payload,
                    context={
                        "realm_code": self.workflow.space.realm_code,
                        "space_code": self.workflow.space.space_code,
                    }
                ).set(queue=self.queue),
            ]

        # Success Hook
        if self.success_hook and not self.success_hook_canvas:
            self.success_hook_canvas = [self.parse_flat_tasks([self.success_hook], True)[0]]

        self.previous = initial_previous

    def run(self):
        _l.info(f'Celery app backend: {celery_app.backend}')

        if not self.canvas:
            self.build()

        canvas = chain(*self.canvas, task_id=uuid())

        self.build_hooks()

        try:
            return canvas.apply_async(
                link=self.success_hook_canvas,
                link_error=self.failure_hook_canvas,
            )
        except Exception as e:
            _l.error(f'Error running workflow: {e}')
            self.workflow.status = Workflow.STATUS_ERROR
            self.workflow.save()
            raise e

    def cancel(self):
        status_to_cancel = set([Task.STATUS_PROGRESS])
        for task in self.workflow.tasks:
            if task.status in status_to_cancel:
                celery_app.control.revoke(task.celery_task_id, terminate=True)
                task.mark_task_as_finished()
                task.status = Task.STATUS_CANCELED
                task.save()
        self.workflow.status = Workflow.STATUS_CANCELED
        self.workflow.save()

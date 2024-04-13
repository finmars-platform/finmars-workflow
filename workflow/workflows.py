import logging

from workflow.builder import WorkflowBuilder

from workflow.models import Workflow, User, Space

_l = logging.getLogger('workflow')


def execute_workflow(username, user_code, payload={}, realm_code=None, space_code=None):
    user = User.objects.get(username=username)

    from workflow.system import get_system_workflow_manager
    system_workflow_manager = get_system_workflow_manager()

    # Check if the workflow exists
    try:
        wf = system_workflow_manager.get_by_user_code(user_code)
    except Exception:
        raise Exception(f"Workflow {user_code} not found")

    space = Space.objects.get(space_code=space_code)

    # Create the workflow in DB
    obj = Workflow(owner=user, space=space, user_code=user_code, payload=payload,
                   is_manager=wf.get('is_manager', False))
    obj.save()

    # Build the workflow and execute it
    data = obj.to_dict()
    workflow = WorkflowBuilder(obj.id)
    workflow.run()

    _l.info(f"Workflow sent : {workflow.canvas}")
    return obj.to_dict(), workflow

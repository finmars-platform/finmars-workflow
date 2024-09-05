import logging

from workflow.builder import WorkflowBuilder
from workflow.models import Space, User, Workflow

_l = logging.getLogger("workflow")


def execute_workflow(
    username,
    user_code,
    payload={},
    realm_code=None,
    space_code=None,
    platform_task_id=None,
):
    user = User.objects.get(username=username)

    from workflow.system import get_system_workflow_manager

    system_workflow_manager = get_system_workflow_manager()

    wf = system_workflow_manager.get_by_user_code(user_code)
    space = Space.objects.get(space_code=space_code)

    # Create the workflow in DB
    obj = Workflow(
        owner=user,
        space=space,
        user_code=user_code,
        payload=payload,
        is_manager=wf.get("is_manager", False),
        platform_task_id=platform_task_id,
    )
    obj.save()

    # Build the workflow and execute it
    data = obj.to_dict()
    workflow = WorkflowBuilder(obj.id)
    workflow.run()

    _l.info(f"Workflow sent : {workflow.canvas}")
    return obj.to_dict(), workflow

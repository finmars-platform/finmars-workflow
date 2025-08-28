import logging

from workflow.builder import WorkflowBuilder
from workflow.models import Space, User, Workflow, WorkflowTemplate
from workflow.tasks.workflows import execute_workflow_v2

_l = logging.getLogger("workflow")


def execute_workflow(
    username,
    user_code,
    payload=None,
    realm_code=None,
    space_code=None,
    platform_task_id=None,
    crontab_id=None,
):
    if payload is None:
        payload = {}

    user = User.objects.get(username=username)

    from workflow.system import get_system_workflow_manager  # noqa: PLC0415

    system_workflow_manager = get_system_workflow_manager()

    wf = system_workflow_manager.get_by_user_code(user_code, sync_remote=True)
    space = Space.objects.get(space_code=space_code)

    workflow_template = None

    _l.info("Looking for worklow template %s", user_code)

    space_less_user_code = ".".join(user_code.split(".")[1:])

    try:  # noqa: SIM105
        workflow_template = WorkflowTemplate.objects.get(user_code=space_less_user_code, space=space)
    except WorkflowTemplate.DoesNotExist:
        pass

    # Create the workflow in DB
    obj = Workflow(
        owner=user,
        space=space,
        user_code=user_code,
        payload=payload,
        workflow_template=workflow_template,
        is_manager=wf["workflow"].get("is_manager", False),
        platform_task_id=platform_task_id,
        crontab_id=crontab_id,
    )
    obj.save()

    # Build the workflow and execute it

    if wf.get("version") == "2":
        _l.info("Execute new version")

        execute_workflow_v2.apply_async(
            kwargs={
                "workflow_id": obj.id,
                "context": {"space_code": space_code, "realm_code": realm_code},
            },
            queue="workflow",
        )

    else:
        _l.info("Execute old version")
        workflow = WorkflowBuilder(obj.id, wf)
        workflow.build()  # Build the workflow execution plan
        workflow.run()  # Run the workflow

        _l.info(f"Workflow sent : {workflow.canvas}")

    return obj.to_dict()

import logging

from workflow.builder import WorkflowBuilder
from workflow.celery_workflow import celery_workflow
from workflow.models import Workflow, User

_l = logging.getLogger('workflow')


def execute_workflow(username, user_code, payload={}):
    user = User.objects.get(username=username)

    # Check if the workflow exists
    try:
        wf = celery_workflow.get_by_user_code(user_code)
    except Exception:
        raise Exception(f"Workflow {user_code} not found")

    # Create the workflow in DB
    obj = Workflow(owner=user, user_code=user_code, payload=payload, is_manager=wf.get('is_manager', False))
    obj.save()

    # Build the workflow and execute it
    data = obj.to_dict()
    workflow = WorkflowBuilder(obj.id)
    workflow.run()

    _l.info(f"Workflow sent : {workflow.canvas}")
    return obj.to_dict(), workflow


import logging

from workflow.builder import WorkflowBuilder
from workflow.celery_workflow import celery_workflow
from workflow.models import Workflow, User
from workflow.utils import validate

_l = logging.getLogger('workflow')

def execute_workflow(username, project, user_code, payload={}):
    fullname = f"{project}.{user_code}"

    user = User.objects.get(username=username)

    # Check if the workflow exists
    try:
        wf = celery_workflow.get_by_name(fullname)
        if "schema" in wf:
            validate(payload, wf["schema"])
    except Exception:
        raise Exception(f"Workflow {fullname} not found")

    # Create the workflow in DB
    obj = Workflow(owner=user, project=project, user_code=user_code, payload=payload)
    obj.save()

    # Build the workflow and execute it
    data = obj.to_dict()
    workflow = WorkflowBuilder(obj.id)
    workflow.run()

    _l.info(f"Workflow sent : {workflow.canvas}")
    return obj.to_dict(), workflow
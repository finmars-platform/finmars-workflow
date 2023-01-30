# Raise Exception Task

This is example of raising an exception inside task



```python
# tasks/raise_exception.py
from workflow.api import task
from workflow.finmars import execute_transaction_import, get_task


@task(name="run_simple_import")
def run_simple_import(*args, **kwargs):

    payload = kwargs['payload']

    filepath = payload['filepath'] # e.g. "test (1).csv"
    scheme_user_code = payload['scheme_user_code'] # e.g. ""Transactions_v3_0""

    # After executing, you receive a object with task_id
    result = execute_simple_import({"file_path": filepath,
                                         "scheme_user_code": scheme_user_code})

    # With this task id you could ask Finmars Core about it status
    task = get_task(result['task_id'])

    return task

@task(name="run_transaction_import")
def run_transaction_import(*args, **kwargs):
    
    # Input of previous task
    input = args[0]
    payload = kwargs['payload']
    
    if input['status'] != 'success' and input['status'] != 'D':
        # Here we raise exception if something wrong, and from this line Workflow Stops it execution
        raise Exception("Finmars Simple Import Failed, Could not Continue. Abort")

    filepath = payload['filepath'] # e.g. "test (1).csv"
    scheme_user_code = payload['scheme_user_code'] # e.g. ""Transactions_v3_0""

    # After executing, you receive a object with task_id
    result = execute_transaction_import({"file_path": filepath,
                                         "scheme_user_code": scheme_user_code})

    # With this task id you could ask Finmars Core about it status
    task = get_task(result['task_id'])

    return task

```

And its YAML file

```yaml
#raise-exception.yaml
---

raise_exception.run:
  tasks:
    - run_simple_import
    - run_transaction_import
```
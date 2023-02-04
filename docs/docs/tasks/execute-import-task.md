# Execute Import Task

This is example of executing simple import

```python
# tasks/execute-import.py
from workflow.api import task
from workflow.finmars import execute_transaction_import, get_task

import time


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
```

And its YAML file

```yaml
#execute-import.yaml
---

execute_import.run:
  tasks:
    - run_simple_import
```
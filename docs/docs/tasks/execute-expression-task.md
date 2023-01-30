# Execute Expression Task

This is example of executing expression in Finmars Core

```python
# tasks/execute-expression.py
from workflow.api import task
from workflow.finmars import execute_expression


@task(name="execute_expression")
def execute_expression(*args, **kwargs):

    result = execute_expression("send_system_message('Hello Workflow')")

    return result


```

Now go to homepage and check your System Messages

And its YAML file

```yaml
#execute-expression.yaml
---

execute_expression.run:
  tasks:
    - execute_expression
```
# Args vs Kwags

In your task you have access to *args and **kwargs arguments

`*args` - its your all positions arguments, e.g `args[0`] give you value of your first argument
`**kwargs` - its Key Word Arguments - e.g `kwargs["payload"]`

So, Idea is `args[0]` is result of previous task, and the `kwargs["payload"]` its data object on workflow level, and every
task has accss to it

also you have `kwargs["workflow_id"]`

```python
# tasks/simple.py
from workflow.api import task

import time


@task(name="EXTRACT")
def extract(*args, **kwargs):
    
    # args[0] will be None if its first task and there is not before_start_hook
    
    return {"status": "success"}


@task(name="TRANSFORM")
def transform(*args, **kwargs):
    
    
    if args[0]['status'] != 'success':
        raise Exception("Previous task has failed. Abort")


@task(name="LOAD")
def load(*args, **kwargs):
    print("Loading data")
    time.sleep(10)


```

And its YAML file

```yaml
#simple.yaml
---
# Simple ETL example
#
# +-----------+      +-------------+      +--------+
# |  EXTRACT  +----->+  TRANSFORM  +----->+  LOAD  |
# +-----------+      +-------------+      +--------+
#
simple.ETL:
  tasks:
    - EXTRACT
    - TRANSFORM
    - LOAD
```
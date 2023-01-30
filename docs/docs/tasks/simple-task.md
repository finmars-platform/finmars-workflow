# Simple Task

This is example of simplies pipeline



```python
# tasks/simple.py
from workflow.api import task

import time

@task(name="EXTRACT")
def extract(*args, **kwargs):
    print("Extracting data")
    time.sleep(10)


@task(name="TRANSFORM")
def transform(*args, **kwargs):
    print("Transforming data")
    raise Exception("Something Went Wrong")
    time.sleep(10)


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
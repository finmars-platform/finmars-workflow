# Scheduled Workflow

Celery provides a scheduler used to periodically execute some tasks. This scheduler is named
the [Celery beat](https://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html).

Director allows you to periodically schedule a whole workflow using a simple YAML syntax.

You can use the `periodic > interval` key with a number argument (in seconds):

```yaml
example.CHAIN:
  tasks:
    - A
    - B
    - C
  periodic:
    interval: 60
```

You can also use the `periodic > crontab` key with a string argument:

```yaml
example.CHAIN_CRONTAB:
  tasks:
    - A
    - B
    - C
  periodic:
    crontab: "0 */3 * * *"
```

The format is the following (the [official documentation](https://docs.celeryproject.org/en/v4.4.7/userguide/periodic-tasks.html#crontab-schedules) of the `crontab` function gives some examples of each attribute):

```yaml
periodic:
  crontab: "minute hour day_of_month month_of_year day_of_week"
```

So in the first example, the *example.CHAIN* workflow will be executed **every 60 seconds** and the second one, *example.CHAIN_CRONTAB*, **every three hours**.


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


@task(name="BEFORE_START")
def before_start(*args, **kwargs):
    # this would be a payload for workflow
    return {
        'test': 123
    }

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
  periodic:
    interval: 60
    payload: '{"date": "2023-01-01"}'
  hooks:
    before_start: BEFORE_START
```
# Retry Task

This is example of how to retry task

Link to Retry logic in [Celery Docs](https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying)

```python
# tasks/simple.py
from workflow.api import task

from workflow.finmars import execute_pricing_procedure


@task(bind=True, name="download_prices")
def download_prices(*args, **kwargs):
    
    try:
        payload = kwargs['payload']
        
        response = execute_pricing_procedure(payload={
            'user_code': 'Daily FX Rates and Prices (Finmars)'
        })
        
        if response['status'] == 'E':
            raise Exception("Prices are not downloaded")
        
    except Exception as e:
        raise self.retry(exc=e)
    

```

And its YAML file

```yaml
#retry-task.yaml
---

retry_task.run:
  tasks:
    - download_prices
```

## Retry Task with custom delay

```python
# tasks/simple.py
from workflow.api import task

from workflow.finmars import execute_pricing_procedure


@task(bind=True, name="download_prices", default_retry_delay=30 * 60)
def download_prices(*args, **kwargs):
    
    try:
        payload = kwargs['payload']
        
        response = execute_pricing_procedure(payload={
            'user_code': 'Daily FX Rates and Prices (Finmars)'
        })
        
        if response['status'] == 'E':
            raise Exception("Prices are not downloaded")
        
    except Exception as e:
        # overrides the default delay to retry after 1 minute
        raise self.retry(exc=e, countdown=60)
    

```

And its YAML file

```yaml
#retry-task.yaml
---

retry_task.run:
  tasks:
    - download_prices
```


## Retry Task with retry limit


```python
# tasks/simple.py
from workflow.api import task

from workflow.finmars import execute_pricing_procedure


@task(bind=True, name="download_prices", default_retry_delay=30 * 60, max_retries=10)
def download_prices(*args, **kwargs):
    
    try:
        payload = kwargs['payload']
        
        response = execute_pricing_procedure(payload={
            'user_code': 'Daily FX Rates and Prices (Finmars)'
        })
        
        if response['status'] == 'E':
            raise Exception("Prices are not downloaded")
        
    except Exception as e:
        # overrides the default delay to retry after 1 minute
        raise self.retry(exc=e, countdown=60)
    

```

And its YAML file

```yaml
#retry-task.yaml
---

retry_task.run:
  tasks:
    - download_prices
```
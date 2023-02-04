# Workflow Documentation

Workflow is a microservice in Finmars ecosystem to provide manage and execute Scheduled/Async Task/Pipelines

![Workflow](img/director.gif)


## Usage

### Write your code in Python

```python
# tasks/orders.py
from workflow.api import task
from .utils import Order, Mail

@task(name="ORDER_PRODUCT")
def order_product(*args, **kwargs):
    order = Order(
      user=kwargs["payload"]["user"],
      product=kwargs["payload"]["product"]
    ).save()
    return {"id": order.id}

@task(name="SEND_MAIL")
def send_mail(*args, **kwargs):
    order_id = args[0]["id"]
    mail = Mail(
      title=f"Your order #{order_id} has been received",
      user=kwargs["payload"]["user"]
    )
    mail.send()
```

### Build your workflows in YAML

```yaml
# workflows.yml
product.ORDER:
  tasks:
    - ORDER_PRODUCT
    - SEND_MAIL
```

### Run it


Use the WebUI to execute your workflows:

![Execute Workflow](../img/execute_workflow.png)

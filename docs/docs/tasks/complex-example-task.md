# Complex Task

This is example of complex pipeline



```python
# tasks/complex.py
import time
from workflow.api import task
from workflow.finmars import execute_expression, execute_transaction_import, get_task, execute_task, execute_simple_import


@task(name="run_import_portfolios")
def run_import_portfolios(*args, **kwargs):

    payload = kwargs["payload"]

    return {'status': 'warning'}

    #result = execute_expression("1 + 1")

    result = execute_expression("send_system_message('Workflow Importing Portfolios')")

    time.sleep(5)

    result = execute_simple_import({"file_path": payload['file_path'], "scheme_user_code": "szhitenev_simple_portfolios"})

    time.sleep(5)

    task = get_task(result['task_id'])

    #return task
    return {'status': 'warning'}

@task(name="run_import_counterparties")
def run_import_counterparties(*args, **kwargs):

    payload = kwargs["payload"]

    #result = execute_expression("1 + 1")

    result = execute_expression("send_system_message('Workflow Importing Counterparties')")


    #return payload
    return {'status': 'warning'}


@task(name="run_import_accounts")
def run_import_accounts(*args, **kwargs):

    # Intntional Error

    payload = kwargs["payload"]

    try:

        #result = execute_expression("1 + 1")

        result = execute_expression("send_system_message('Workflow importing accounts')")

        result = execute_simple_import({"file_path": "szhitenev_portfolios.csv", "scheme_user_code": "szhitnev_simple_portfolios"})

        # for example API DOWN
        raise Exception("Finmars API 500 response")

        task = get_task(result['task_id'])


        return task

    except Exception as e:

        execute_expression("send_system_message('Workflow importing accounts Failed')")

        return {'status': 'warning', 'error_message': str(e)}


@task(name="run_import_transactions", default_retry_delay=30 * 60)
def run_import_transactions(*args, **kwargs):

    return args[0]

    payload = kwargs["payload"]

    if payload['status'] == 'warning':
        raise Exception("Could not proceed")

    return payload

    #result = execute_expression("1 + 1")

    result = execute_expression("send_system_message('Workflow Importing Transactions')")

    time.sleep(5)

    result = execute_transaction_import({"file_path": "szhitenev_transactions.csv", "scheme_user_code": "szhitnev_simple_transactions"})

    time.sleep(5)

    task = get_task(result['task_id'])



    return task



@task(name="calculate_portfolio_register_record")
def calculate_portfolio_register_record(*args, **kwargs):

    payload = kwargs["payload"]

    #result = execute_expression("1 + 1")

    result = execute_expression("send_system_message('Workflow Portfolio Register record')")

    result = execute_task('portfolios.calculate_portfolio_register_record')

    task = get_task(result['task_id'])

    return task


@task(name="calculate_portfolio_price_history")
def calculate_portfolio_price_history(*args, **kwargs):

    payload = kwargs["payload"]

    #result = execute_expression("1 + 1")

    result = execute_expression("send_system_message('Workflow Portfolio Price History Calculate')")

    result = execute_task('portfolios.calculate_portfolio_register_price_history')

    task = get_task(result['task_id'])

    return task
```

And its YAML file

```yaml
#complex.yaml
tasks:
  - EXAMPLE_GROUP:
      type: group
      tasks:
        - run_import_portfolios
        - run_import_accounts
        - run_import_counterparties
  - run_import_transactions
  - calculate_portfolio_register_record
  - calculate_portfolio_price_history
```
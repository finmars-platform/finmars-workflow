import json
import logging
import time

import requests
from rest_framework_simplejwt.tokens import RefreshToken

from workflow.models import User
from workflow_app import settings

_l = logging.getLogger('workflow')


def execute_expression(expression):
    bot = User.objects.get(username="finmars_bot")

    refresh = RefreshToken.for_user(bot)

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': 'Bearer %s' % refresh.access_token}
    data = {
        'expression': expression,
        'is_eval': True
    }

    url = settings.HOST_URL + '/' + settings.BASE_API_URL + '/api/v1/utils/expression/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def execute_expression_procedure(payload):
    bot = User.objects.get(username="finmars_bot")

    refresh = RefreshToken.for_user(bot)

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': 'Bearer %s' % refresh.access_token}
    data = payload

    url = settings.HOST_URL + '/' + settings.BASE_API_URL + '/api/v1/procedures/expression-procedure/execute/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def execute_data_procedure(payload):
    bot = User.objects.get(username="finmars_bot")

    refresh = RefreshToken.for_user(bot)

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': 'Bearer %s' % refresh.access_token}
    data = payload

    url = settings.HOST_URL + '/' + settings.BASE_API_URL + '/api/v1/procedures/data-procedure/execute/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def execute_pricing_procedure(payload):
    bot = User.objects.get(username="finmars_bot")

    refresh = RefreshToken.for_user(bot)

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': 'Bearer %s' % refresh.access_token}
    data = payload

    url = settings.HOST_URL + '/' + settings.BASE_API_URL + '/api/v1/procedures/pricing-procedure/execute/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def execute_task(task_name, payload):
    bot = User.objects.get(username="finmars_bot")

    refresh = RefreshToken.for_user(bot)

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': 'Bearer %s' % refresh.access_token}
    data = {
        'task_name': task_name,
        'payload': payload
    }

    url = settings.HOST_URL + '/' + settings.BASE_API_URL + '/api/v1/tasks/task/execute/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def get_task(id):
    bot = User.objects.get(username="finmars_bot")

    refresh = RefreshToken.for_user(bot)

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': 'Bearer %s' % refresh.access_token}

    url = settings.HOST_URL + '/' + settings.BASE_API_URL + '/api/v1/tasks/task/%s/' % id

    response = requests.get(url=url, headers=headers)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def _wait_task_to_complete_recursive(task_id=None, retries=5, retry_interval=60, counter=None):

    if counter == retries:
        raise Exception("Task exceeded retries %s count" % retries)

    result = get_task(task_id)

    counter = counter + 1

    if result.status != 'progress' and result.status != 'P':
        return result

    time.sleep(retry_interval)

    return _wait_task_to_complete_recursive(task_id=task_id, retries=retries, retry_interval=retry_interval, counter=counter)


def wait_task_to_complete(task_id=None, retries=5, retry_interval=60):

    counter = 0
    result = None

    result = _wait_task_to_complete_recursive(task_id=task_id, retries=retries, retry_interval=retry_interval, counter=counter)

    return result

def execute_transaction_import(payload):
    bot = User.objects.get(username="finmars_bot")

    refresh = RefreshToken.for_user(bot)

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': 'Bearer %s' % refresh.access_token}
    data = payload

    url = settings.HOST_URL + '/' + settings.BASE_API_URL + '/api/v1/import/transaction-import/execute/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def execute_simple_import(payload):
    bot = User.objects.get(username="finmars_bot")

    refresh = RefreshToken.for_user(bot)

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': 'Bearer %s' % refresh.access_token}
    data = payload

    url = settings.HOST_URL + '/' + settings.BASE_API_URL + '/api/v1/import/simple-import/execute/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()

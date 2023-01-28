import json
import logging

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


def execute_task(payload):
    bot = User.objects.get(username="finmars_bot")

    refresh = RefreshToken.for_user(bot)

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': 'Bearer %s' % refresh.access_token}
    data = payload

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

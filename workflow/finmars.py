import csv
import datetime
import importlib
import json
import logging
import os
import time
from datetime import timedelta

import pandas as pd
import requests
from django.core.files.base import ContentFile
from flatten_json import flatten
from rest_framework_simplejwt.tokens import RefreshToken

from workflow.models import User
from workflow_app import settings

_l = logging.getLogger('workflow')


class DjangoStorageHandler(logging.Handler):
    def __init__(self, log_file, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_file = log_file

    def emit(self, record):
        log_entry = self.format(record)

        storage = Storage()

        storage.append_text(self.log_file, log_entry)

        # with storage.open(self.log_file, 'a') as log_file:
        #     log_file.write(log_entry + '\n')


def get_access_token():
    bot = User.objects.get(username="finmars_bot")
    new_token = RefreshToken.for_user(bot)

    return new_token


def create_logger(name, log_format=None):
    if not log_format:
        log_format = "[%(asctime)s][%(levelname)s][%(name)s][%(filename)s:%(funcName)s:%(lineno)d] - %(message)s"
    formatter = logging.Formatter(log_format)

    log_dir = "/.system/log/"

    log_file = os.path.join(log_dir, str(name) + ".log")
    file_handler = DjangoStorageHandler(log_file)
    file_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    logger.addHandler(file_handler)

    return logger


def execute_expression(expression):

    refresh = get_access_token()

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': f'Bearer {refresh.access_token}'}

    data = {
        'expression': expression,
        'is_eval': True
    }

    url = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + '/api/v1/utils/expression/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def execute_expression_procedure(payload):

    refresh = get_access_token

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': f'Bearer {refresh.access_token}'}

    data = payload

    url = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + '/api/v1/procedures/expression-procedure/execute/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def execute_data_procedure(payload):

    refresh = get_access_token()

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': f'Bearer {refresh.access_token}'}

    data = payload

    url = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + '/api/v1/procedures/data-procedure/execute/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def get_data_procedure_instance(id):

    refresh = get_access_token()

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': f'Bearer {refresh.access_token}'}

    url = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + '/api/v1/procedures/data-procedure-instance/%s/' % id

    response = requests.get(url=url, headers=headers, verify=settings.VERIFY_SSL)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def execute_pricing_procedure(payload):

    refresh = get_access_token()

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': f'Bearer {refresh.access_token}'}

    data = payload

    url = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + '/api/v1/procedures/pricing-procedure/execute/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def execute_task(task_name, payload={}):

    refresh = get_access_token()

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': f'Bearer {refresh.access_token}'}


    data = {
        'task_name': task_name,
        'payload': payload
    }

    url = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + '/api/v1/tasks/task/execute/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def get_task(id):

    refresh = get_access_token()

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': f'Bearer {refresh.access_token}'}

    url = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + '/api/v1/tasks/task/%s/' % id

    response = requests.get(url=url, headers=headers, verify=settings.VERIFY_SSL)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def _wait_task_to_complete_recursive(task_id=None, retries=5, retry_interval=60, counter=None):
    if counter == retries:
        raise Exception("Task exceeded retries %s count" % retries)

    try:
        result = get_task(task_id)

        if result['status'] not in ['progress', 'P', 'I']:
            return result
    except Exception as e:
        _l.error("_wait_task_to_complete_recursive %s" % e)

    counter = counter + 1

    time.sleep(retry_interval)

    return _wait_task_to_complete_recursive(task_id=task_id, retries=retries, retry_interval=retry_interval,
                                            counter=counter)


def wait_task_to_complete(task_id=None, retries=5, retry_interval=60):
    counter = 0
    result = None

    result = _wait_task_to_complete_recursive(task_id=task_id, retries=retries, retry_interval=retry_interval,
                                              counter=counter)

    return result


def _wait_procedure_to_complete_recursive(procedure_instance_id=None, retries=5, retry_interval=60, counter=None):
    if counter == retries:
        raise Exception("Task exceeded retries %s count" % retries)

    result = get_data_procedure_instance(procedure_instance_id)

    counter = counter + 1

    if result['status'] not in ['progress', 'P', 'I']:
        return result

    time.sleep(retry_interval)

    return _wait_procedure_to_complete_recursive(procedure_instance_id=procedure_instance_id, retries=retries,
                                                 retry_interval=retry_interval, counter=counter)


def wait_procedure_to_complete(procedure_instance_id=None, retries=5, retry_interval=60):
    counter = 0
    result = None

    result = _wait_procedure_to_complete_recursive(procedure_instance_id=procedure_instance_id, retries=retries,
                                                   retry_interval=retry_interval, counter=counter)

    return result


def execute_transaction_import(payload):

    refresh = get_access_token()

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': f'Bearer {refresh.access_token}'}
    data = payload

    url = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + '/api/v1/import/transaction-import/execute/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def execute_simple_import(payload):

    refresh = get_access_token()

    # _l.info('refresh %s' % refresh.access_token)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': f'Bearer {refresh.access_token}'}

    data = payload

    url = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + '/api/v1/import/simple-import/execute/'

    response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


def request_api(path, method='get', data=None):

    refresh = get_access_token()

    headers = {'Content-type': 'application/json', 'Accept': 'application/json',
               'Authorization': f'Bearer {refresh.access_token}'}

    url = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + path

    response = None

    if method.lower() == 'get':

        response = requests.get(url=url, headers=headers, verify=settings.VERIFY_SSL)

    elif method.lower() == 'post':

        response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

    elif method.lower() == 'put':

        response = requests.put(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

    elif method.lower() == 'patch':

        response = requests.patch(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

    elif method.lower() == 'delete':

        response = requests.delete(url=url, headers=headers, verify=settings.VERIFY_SSL)

    if response.status_code != 200 and response.status_code != 201 and response.status_code != 204:
        raise Exception(response.text)

    if response.status_code != 204:
        return response.json()

    return {"status": "no_content"}


class Storage():

    def __init__(self):

        from workflow.storage import get_storage

        self.storage = get_storage()

        self.base_path = settings.BASE_API_URL

    def listdir(self, path):
        return self.storage.listdir('/' + self.base_path + path)

    def open(self, name, mode='rb'):

        # TODO permission check

        if name[0] == '/':
            name = self.base_path + name
        else:
            name = self.base_path + '/' + name

        return self.storage.open(name, mode)

    def read_json(self, filepath, mode='rb'):
        with self.open(filepath, mode) as state:
            state_content = json.loads(state.read())
        return state_content

    def read_csv(self, filepath, mode='rb'):
        with self.open(filepath, mode) as f:
            reader = csv.DictReader(f)
            data = list(reader)
        return data

    def read(self, filepath, mode='rb'):

        # Open the file from your storage backend
        file_obj = self.open(filepath, mode)  # 'rb' is to read in binary mode

        try:
            # Read the file's contents
            file_content = file_obj.read()
            return file_content
        finally:
            # Make sure we close the file object
            file_obj.close()

    def delete(self, name):

        # TODO permission check

        if name[0] == '/':
            name = self.base_path + name
        else:
            name = self.base_path + '/' + name

        return self.storage.delete(name)

    def exists(self, name):

        # TODO permission check

        if name[0] == '/':
            name = self.base_path + name
        else:
            name = self.base_path + '/' + name

        return self.storage.exists(name)

    def save(self, name, content):

        if name[0] == '/':
            name = self.base_path + name
        else:
            name = self.base_path + '/' + name

        return self.storage.save(name, content)

    def save_text(self, name, content):

        if name[0] == '/':
            name = self.base_path + name
        else:
            name = self.base_path + '/' + name

        return self.storage.save(name, ContentFile(content.encode('utf-8')))

    def append_text(self, name, content):

        if self.storage.exists(name):
            with self.open(name, 'r') as file:
                content = file.read()
                content = content + content + '\n'

        return self.storage.save(name, ContentFile(content.encode('utf-8')))


class Utils():

    def get_current_space_code(self):
        return settings.BASE_API_URL

    def get_list_of_dates_between_two_dates(self, date_from, date_to, to_string=False):
        result = []
        format = '%Y-%m-%d'

        if not isinstance(date_from, datetime.date):
            date_from = datetime.datetime.strptime(date_from, format).date()

        if not isinstance(date_to, datetime.date):
            date_to = datetime.datetime.strptime(date_to, format).date()

        diff = date_to - date_from

        for i in range(diff.days + 1):
            day = date_from + timedelta(days=i)
            if to_string:
                result.append(str(day))
            else:
                result.append(day)

        return result

    def is_business_day(self, date):
        return bool(len(pd.bdate_range(date, date)))

    def get_yesterday(self, ):
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        return yesterday

    def get_list_of_business_days_between_two_dates(self, date_from, date_to, to_string=False):
        result = []
        format = '%Y-%m-%d'

        if not isinstance(date_from, datetime.date):
            date_from = datetime.datetime.strptime(date_from, format).date()

        if not isinstance(date_to, datetime.date):
            date_to = datetime.datetime.strptime(date_to, format).date()

        diff = date_to - date_from

        for i in range(diff.days + 1):
            day = date_from + timedelta(days=i)

            if self.is_business_day(day):

                if to_string:
                    result.append(str(day))
                else:
                    result.append(day)

        return result

    def import_from_storage(self, file_path):
        # get the directory and the filename without extension

        if file_path[0] == '/':
            file_path = os.path.join(settings.MEDIA_ROOT + '/tasks/' + settings.BASE_API_URL + file_path)
        else:
            file_path = os.path.join(settings.MEDIA_ROOT + '/tasks/' + settings.BASE_API_URL + '/' + file_path)

        _l.info('import_from_storage.file_path %s' % file_path)

        directory, filename = os.path.split(file_path)
        module_name, _ = os.path.splitext(filename)

        _l.info('import_from_storage.module_name %s' % module_name)
        _l.info('import_from_storage.file_path %s' % file_path)

        loader = importlib.machinery.SourceFileLoader(module_name, file_path)
        module = loader.load_module()

        # add the directory to sys.path
        # spec = importlib.util.spec_from_file_location(module_name, file_path)
        #
        # if spec is None:
        #     raise ImportError(f"Cannot import file {filename}")
        #
        # module = importlib.util.module_from_spec(spec)
        #
        # # execute the module
        # spec.loader.exec_module(module)
        #
        # # return the module
        return module

    def relative_import_from_storage(self, file_path, base_path):

        """
        Imports a module from a given file path, resolving the path from a specified base path.

        :param file_path: Relative or absolute path to the Python file to import.
        :param base_path: Base directory against which relative paths should be resolved.
        :return: The imported module.
        """

        # Resolve the relative file_path against the provided base directory
        absolute_file_path = os.path.normpath(os.path.join(base_path, file_path))

        _l.info(f'Normalized file path: {absolute_file_path}')

        # Continue with your existing logic, but use absolute_file_path instead of file_path
        directory, filename = os.path.split(absolute_file_path)
        module_name, _ = os.path.splitext(filename)

        _l.info(f'import_from_storage.module_name {module_name}')
        _l.info(f'import_from_storage.file_path {absolute_file_path}')

        loader = importlib.machinery.SourceFileLoader(module_name, absolute_file_path)
        module = loader.load_module()

        # add the directory to sys.path
        # spec = importlib.util.spec_from_file_location(module_name, file_path)
        #
        # if spec is None:
        #     raise ImportError(f"Cannot import file {filename}")
        #
        # module = importlib.util.module_from_spec(spec)
        #
        # # execute the module
        # spec.loader.exec_module(module)
        #
        # # return the module
        return module

    def tree_to_flat(self, data, **kwargs):

        return flatten(data, **kwargs)


class Vault():

    def get_secret(self, path):

        refresh = get_access_token() # TODO refactor, should be permission check

        # _l.info('refresh %s' % refresh.access_token)

        pieces = path.split('/')
        engine_name = pieces[0]
        secret_path = pieces[1]

        headers = {'Content-type': 'application/json', 'Accept': 'application/json',
                   'Authorization': f'Bearer {refresh.access_token}'}

        url = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + f'/api/v1/vault/vault-secret/get/?engine_name={engine_name}&path={secret_path}'

        response = requests.get(url=url, headers=headers, verify=settings.VERIFY_SSL)

        if response.status_code != 200:
            raise Exception(response.text)

        return response.json()['data']['data']


storage = Storage()

utils = Utils()

vault = Vault()

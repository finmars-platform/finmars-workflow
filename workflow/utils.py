import logging
import os
import sys

from celery.schedules import crontab
from jsonschema.validators import validator_for
from django.db import connection

from workflow.exceptions import WorkflowSyntaxError

_l = logging.getLogger('workflow')


def validate(payload, schema):
    """Validate a payload according to a given schema"""
    validator_cls = validator_for(schema)
    validator = validator_cls(schema=schema)
    errors = list(validator.iter_errors(payload))
    if errors:
        raise Exception("Payload is not valid", errors)


def format_schema_errors(e):
    """Format FlaskJsonSchema validation errors"""
    return {
        "error": e.message,
        "errors": [validation_err.message for validation_err in e.errors],
    }


def build_celery_schedule(workflow_name, data):
    """A celery schedule can accept seconds or crontab"""

    _l.info('build_celery_schedule %s' % workflow_name)

    def _handle_schedule(schedule):
        try:
            value = float(schedule)
        except ValueError:
            m, h, dw, dm, my = schedule.split(" ")
            value = crontab(
                minute=m,
                hour=h,
                day_of_month=dm,
                month_of_year=my,
                day_of_week=dw,
            )
        return value

    def _handle_crontab(ct):
        m, h, dm, my, dw = ct.split(" ")
        return crontab(
            minute=m,
            hour=h,
            day_of_month=dm,
            month_of_year=my,
            day_of_week=dw,
        )

    excluded_keys = ["payload"]
    keys = [k for k in data.keys() if k not in excluded_keys]

    schedule_functions = {
        # Legacy syntax for backward compatibility
        "schedule": _handle_schedule,
        # Current syntax
        "crontab": _handle_crontab,
        "interval": float,
    }

    if len(keys) != 1 or keys[0] not in schedule_functions.keys():
        # When there is no key (schedule, interval, crontab) in the periodic configuration
        raise WorkflowSyntaxError(workflow_name)

    schedule_key = keys[0]
    schedule_input = data[schedule_key]
    try:
        # Apply the function mapped to the schedule type
        return str(schedule_input), schedule_functions[schedule_key](schedule_input)
    except Exception as e:
        _l.error("build_celery_schedule.e %s" % e)

        raise WorkflowSyntaxError(workflow_name)


def send_alert(workflow):
    from workflow.models import Workflow
    from workflow.models import User
    from workflow.models import Task
    from workflow_app import settings
    from rest_framework_simplejwt.tokens import RefreshToken
    import requests
    import json

    if workflow.status == Workflow.STATUS_ERROR:

        # _l.info("Going to report Error to Finmars")

        try:

            bot = User.objects.get(username="finmars_bot")

            refresh = RefreshToken.for_user(bot)

            # _l.info('refresh %s' % refresh.access_token)

            headers = {'Content-type': 'application/json', 'Accept': 'application/json',
                       'Authorization': 'Bearer %s' % refresh.access_token}

            error_task = workflow.tasks.filter(status=Task.STATUS_ERROR).first()

            error_description = 'Unknown'

            if error_task:
                error_description = str(error_task.error_message)

            _l.info("Going to report Error to Finmars")

            data = {
                "expression": "send_system_message(type='error', title='Workflow Failed. " + str(
                    workflow.user_code) + " (" + str(
                    workflow.id) + ")', description='Something Went Wrong. See Task for the details', action_status='required')",
                "is_eval": True
            }

            if workflow.space.realm_code:
                url = 'https://' + settings.DOMAIN_NAME + '/' + workflow.space.realm_code + '/' + workflow.space.space_code + '/api/v1/utils/expression/'
            else:
                url = 'https://' + settings.DOMAIN_NAME + '/' + workflow.space.space_code + '/api/v1/utils/expression/'

            response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

            # _l.info('response %s' % response.text)

        except Exception as e:
            _l.error("Could not send system message to finmars. Error %s" % e)


def construct_path(*args):
    return os.path.join(*args)


def schema_exists(schema_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = %s;
        """, [schema_name])
        return cursor.fetchone() is not None


def get_all_tenant_schemas():
    # List to hold tenant schemas
    tenant_schemas = []

    # SQL to fetch all non-system schema names
    # ('pg_catalog', 'information_schema', 'public') # do later in 1.9.0. where is not public schemes left
    sql = """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
        AND schema_name NOT LIKE 'pg_toast%'
        AND schema_name NOT LIKE 'pg_temp_%'
        """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        tenant_schemas = [row[0] for row in cursor.fetchall()]

    return tenant_schemas


def is_special_execution_context():
    """Check if the current execution context is for special operations like migrations or tests."""
    special_commands = {'test', 'makemigrations', 'migrate', 'migrate_all_schemes', 'clearsessions', 'collectstatic', 'sync_remote_storage_to_local_storage_all_spaces'}
    return any(cmd in sys.argv for cmd in special_commands)


def set_schema_from_context(context):

    if context:
        if context.get('space_code'):

            if schema_exists(context.get('space_code')):

                space_code = context.get('space_code')
                with connection.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {space_code};")

            else:
                raise Exception('No space_code in database schemas')
        else:
            raise Exception('No space_code in context')
    else:
        raise Exception('No context in kwargs')
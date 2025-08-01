import datetime
import json
import re
import traceback
from http import HTTPStatus

from django.http import HttpResponse
from django.utils.timezone import now

from finmars_standardized_errors.models import ErrorRecord

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

import logging

_l = logging.getLogger('finmars')


class ExceptionMiddleware(MiddlewareMixin):

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        # print('exception %s' % exception)

        _l.error("ExceptionMiddleware process error %s" % request.build_absolute_uri())
        _l.error(traceback.format_exc())

        lines = traceback.format_exc().splitlines()[-6:]
        traceback_lines = []

        http_code_to_message = {v.value: v.description for v in HTTPStatus}

        for line in lines:
            traceback_lines.append(re.sub(r'File ".*[\\/]([^\\/]+.py)"', r'File "\1"', line))

        url = request.build_absolute_uri()
        username = str(request.user.username)
        message = http_code_to_message[500]

        data = {
            'error': {
                'url': url,
                'username': username,
                'details': {
                    'traceback': '\n'.join(traceback_lines),
                    'error_message': repr(exception),
                },
                'message': message,
                'status_code': 500,
                'datetime': str(datetime.datetime.strftime(now(), '%Y-%m-%d %H:%M:%S'))
            }
        }

        ErrorRecord.objects.create(url=url, username=username, status_code=500, message=message, details={
            'traceback': '\n'.join(traceback_lines),
            'error_message': repr(exception),
        })

        response_json = json.dumps(data, indent=2, sort_keys=True)

        return HttpResponse(response_json, status=500, content_type="application/json")

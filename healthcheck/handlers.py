import datetime
import locale
import logging
import socket
import time
from timeit import default_timer as timer

import psutil
from django.db import DatabaseError, IntegrityError

from healthcheck.conf import HEALTHCHECK
from healthcheck.exceptions import (
    HealthCheckException,
    ServiceReturnedUnexpectedResult,
    ServiceUnavailable,
    ServiceWarning,
)
from healthcheck.models import HealthcheckTestModel

_l = logging.getLogger("healthcheck")

host = socket.gethostname()

DISK_USAGE_MAX = HEALTHCHECK["DISK_USAGE_MAX"]
MEMORY_MIN = HEALTHCHECK["MEMORY_MIN"]


class BaseHealthCheck:
    def __init__(self):
        self.errors = []

    def check_status(self):
        raise NotImplementedError

    def run_check(self):
        start = timer()
        self.errors = []
        try:
            self.check_status()
        except HealthCheckException as e:
            self.add_error(e, e)
        except BaseException:
            _l.exception("Unexpected Error!")
            raise
        finally:
            self.time_taken = timer() - start

    def add_error(self, error, cause=None):
        if isinstance(error, HealthCheckException):
            pass
        elif isinstance(error, str):
            msg = error
            error = HealthCheckException(msg)
        else:
            msg = "unknown error"
            error = HealthCheckException(msg)
        if isinstance(cause, BaseException):
            _l.exception(str(error))
        else:
            _l.error(str(error))
        self.errors.append(error)

    def pretty_status(self):
        if self.errors:
            return {"errors": [str(e) for e in self.errors]}

        return self.get_info()

    def get_info(self):
        return "working"

    @property
    def status(self):
        return int(not self.errors)

    def identifier(self):
        return self.__class__.__name__


class DiskUsagePlugin(BaseHealthCheck):
    def check_status(self):
        try:
            du = psutil.disk_usage("/")
            if DISK_USAGE_MAX and du.percent >= DISK_USAGE_MAX:
                raise ServiceWarning(f"{host} {du.percent}% disk usage exceeds {DISK_USAGE_MAX}%")
        except ValueError as e:
            self.add_error(ServiceReturnedUnexpectedResult("ValueError"), e)

    def get_info(self):
        data = []

        item = {}

        du = psutil.disk_usage("/")

        item["componentType"] = "system"
        item["observedValue"] = du.percent
        item["observedUnit"] = "percent"
        item["time"] = datetime.datetime.now().isoformat()
        item["status"] = "pass"
        item["output"] = ""

        data.append(item)

        return data

    def identifier(self):
        return "disk:utilization"


class MemoryUsagePlugin(BaseHealthCheck):
    def check_status(self):
        try:
            memory = psutil.virtual_memory()
            if MEMORY_MIN and memory.available < (MEMORY_MIN * 1024 * 1024):
                locale.setlocale(locale.LC_ALL, "")
                avail = f"{int(memory.available / 1024 / 1024):n}"
                threshold = f"{MEMORY_MIN:n}"
                raise ServiceWarning(f"{host} {avail} MB available RAM below {threshold} MB")
        except ValueError as e:
            self.add_error(ServiceReturnedUnexpectedResult("ValueError"), e)

    def get_info(self):
        data = []

        item = {}

        memory = psutil.virtual_memory()

        available_memory_mb = int(memory.used / 1024 / 1024)
        item["componentType"] = "system"
        item["observedValue"] = available_memory_mb
        item["observedUnit"] = "MiB"
        item["time"] = datetime.datetime.now().isoformat()
        item["status"] = "pass"
        item["output"] = ""

        data.append(item)

        return data

    def identifier(self):
        return "memory:utilization"


class DatabasePlugin(BaseHealthCheck):
    response_time = None

    def check_status(self):
        try:
            start_time = time.time()

            obj = HealthcheckTestModel.objects.create(name="First")
            self.response_time = time.time() - start_time

            obj.name = "Second"
            obj.save()
            obj.delete()
        except IntegrityError as err:
            raise ServiceReturnedUnexpectedResult("Integrity Error") from err
        except DatabaseError as err:
            raise ServiceUnavailable("Database error") from err

    def get_info(self):
        data = []

        item = {}

        response_time_ms = int(round(self.response_time * 1000))

        item["componentType"] = "datastore"
        item["observedValue"] = response_time_ms
        item["observedUnit"] = "ms"
        item["time"] = datetime.datetime.now().isoformat()
        item["status"] = "pass"
        item["output"] = ""

        data.append(item)

        return data

    def identifier(self):
        return "database:responseTime"


class UptimePlugin(BaseHealthCheck):
    def check_status(self):
        pass

    def get_info(self):
        data = []

        item = {}

        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())

        item["componentType"] = "system"
        item["observedValue"] = uptime.total_seconds()
        item["observedUnit"] = "s"
        item["time"] = datetime.datetime.now().isoformat()
        item["status"] = "pass"
        item["output"] = ""

        data.append(item)

        return data

    def identifier(self):
        return "uptime"

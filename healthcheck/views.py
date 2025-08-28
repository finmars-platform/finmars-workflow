from concurrent.futures import ThreadPoolExecutor

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.views import APIView

from healthcheck.handlers import DatabasePlugin, DiskUsagePlugin, MemoryUsagePlugin, UptimePlugin


class HealthcheckView(APIView):
    _errors = None
    _plugins = None

    @property
    def errors(self):
        if not self._errors:
            self._errors = self.run_check()
        return self._errors

    @property
    def plugins(self):
        if not self._plugins:
            self._plugins = [DiskUsagePlugin(), MemoryUsagePlugin(), DatabasePlugin(), UptimePlugin()]
        return self._plugins

    def run_check(self):
        errors = []

        def _run(plugin):
            plugin.run_check()
            try:
                return plugin
            finally:
                from django.db import connections  # noqa: PLC0415

                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(self.plugins) or 1) as executor:
            for plugin in executor.map(_run, self.plugins):
                errors.extend(plugin.errors)

        return errors

    @method_decorator(never_cache, name="dispatch")
    def get(self, request, *args, **kwargs):
        data = {}
        data["version"] = 1
        data["checks"] = {}
        data["status"] = "pass"
        data["notes"] = ""
        data["description"] = ""
        data["output"] = ""
        status_code = 200

        if self.errors:
            status_code = 500
            data["status"] = "fail"

        # for item in self.plugins:
        #
        #     key = str(item.identifier())
        #
        #     data['checks'][key] = item.pretty_status()

        return JsonResponse(data, status=status_code)

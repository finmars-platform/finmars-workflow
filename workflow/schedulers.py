from celery.utils.log import get_logger
from django.db.utils import DatabaseError, InterfaceError
from django_celery_beat.schedulers import DatabaseScheduler as DCBScheduler

from workflow.models import Schedule
from workflow.utils import get_all_tenant_schemas, set_schema_from_context

logger = get_logger(__name__)
debug, info, warning = logger.debug, logger.info, logger.warning


class DatabaseScheduler(DCBScheduler):
    Model = Schedule

    def all_as_schedule(self):
        debug("DatabaseScheduler: Fetching database schedule")
        schemas = get_all_tenant_schemas()
        s = {}
        for schema in schemas:
            set_schema_from_context({"space_code": schema})
            for model in self.Model.objects.enabled():
                try:  # noqa: SIM105
                    s[f"{schema}:{model.name}"] = self.Entry(model, app=self.app)
                except ValueError:
                    pass
        return s

    def schedule_changed(self):
        last = self._last_timestamp
        ts = None
        schemas = get_all_tenant_schemas()
        for schema in schemas:
            set_schema_from_context({"space_code": schema})
            try:
                last_change_in_schema = self.Changes.last_change()
                if last_change_in_schema:
                    if ts:
                        ts = max(ts, last_change_in_schema)
                    else:
                        ts = last_change_in_schema
            except DatabaseError as exc:
                logger.exception("Database gave error: %r", exc)
                return False
            except InterfaceError:
                warning("DatabaseScheduler: InterfaceError in schedule_changed(), waiting to retry in next call...")
                return False
        try:
            if ts and ts > (last if last else ts):
                return True
        finally:
            self._last_timestamp = ts
        return False

from celery.utils.log import get_logger
from django.core.exceptions import ObjectDoesNotExist
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

    def sync(self):
        """Persist each dirty entry UNDER ITS OWN tenant schema.

        Entries are keyed ``"<schema>:<name>"`` by :meth:`all_as_schedule`. The
        base :class:`DatabaseScheduler.sync` saves them under whatever
        ``search_path`` happens to be active at sync time, so in this
        multitenant setup ``last_run_at`` / ``total_run_count`` land in the
        wrong schema (or nowhere) and never advance for the tenant. beat then
        keeps re-sending the same scheduled task on every cycle while the due
        window is open — observed as ``portfolio_history`` firing 3-4x/night in
        space0uph9. ``total_run_count`` staying ``0`` in the DB is the tell-tale
        of that bug. Setting the schema per entry before ``save()`` fixes it.
        """
        info("DatabaseScheduler: Writing entries (multitenant, per-schema)...")
        _failed = set()
        try:
            while self._dirty:
                name = self._dirty.pop()
                schema = name.split(":", 1)[0]
                try:
                    set_schema_from_context({"space_code": schema})
                    self.schedule[name].save()
                except (KeyError, ObjectDoesNotExist):
                    _failed.add(name)
        except DatabaseError as exc:
            logger.exception("DatabaseScheduler: Database error while sync: %r", exc)
        except InterfaceError:
            warning("DatabaseScheduler: InterfaceError in sync(), waiting to retry in next call...")
        finally:
            # Re-queue entries we could not save so the next sync retries them.
            self._dirty |= _failed

import logging
from typing import Any

import requests
from django.conf import settings

from workflow_app import celery_app

logger = logging.getLogger(__name__)


class CeleryMonitoring:
    def __init__(self):
        self.insp = celery_app.control.inspect()
        self.task_types = ["active_tasks", "scheduled_tasks", "pending_tasks"]

    def get_tasks_data(self) -> dict[str, Any]:
        try:
            tasks_data = {
                "active_tasks": self.insp.active() or {},
                "scheduled_tasks": self.insp.scheduled() or {},
                "pending_tasks": self.insp.reserved() or {},
            }

            data: dict[str, Any] = {}
            for task_type in self.task_types:
                for full_worker_name, tasks in tasks_data[task_type].items():
                    worker_type, worker_name = full_worker_name.split("@")

                    if worker_type not in data:
                        data[worker_type] = {}

                    if worker_name not in data[worker_type]:
                        data[worker_type][worker_name] = {
                            "active_tasks": [],
                            "scheduled_tasks": [],
                            "pending_tasks": [],
                            "active_tasks_count": 0,
                            "pending_tasks_count": 0,
                            "scheduled_tasks_count": 0,
                            "total_tasks_count": 0,
                        }

                    for task in tasks:
                        data[worker_type][worker_name][task_type].append(task)
                        data[worker_type][worker_name][f"{task_type}_count"] += 1
                        data[worker_type][worker_name]["total_tasks_count"] += 1

            return data

        except Exception as e:
            logger.error(f"Error getting Celery tasks data: {e}")
            return {}


class RabbitMQMonitoring:
    def __init__(self):
        self.host = settings.RABBITMQ_HOST
        self.username = settings.RABBITMQ_USER
        self.password = settings.RABBITMQ_PASSWORD
        self.management_port = getattr(settings, "RABBITMQ_MANAGEMENT_PORT", 15672)
        self.auth = (self.username, self.password)
        self.base_url = f"http://{self.host}:{self.management_port}/api"

    def _make_request(self, endpoint: str) -> dict[str, Any] | None:
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, auth=self.auth, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error requesting {endpoint}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            return None

    def get_main_queues_info(self) -> dict[str, dict[str, Any]]:
        queues_data = self._make_request("queues")
        if not queues_data:
            return {}

        main_queues: dict[str, dict[str, Any]] = {}
        for queue in queues_data:
            if not isinstance(queue, dict):
                continue
            queue_name = queue.get("name", "")

            if any(skip in queue_name for skip in [".celery.pidbox", "celeryev."]):
                continue

            if queue_name.startswith("backend-"):
                group = "backend"
                display_name = queue_name
            elif queue_name == "workflow":
                group = "workflow"
                display_name = queue_name
            else:
                logger.warning(f"Unknown queue: {queue_name}")
                continue

            if group not in main_queues:
                main_queues[group] = {}

            main_queues[group][display_name] = {
                "name": queue_name,
                "messages": queue.get("messages", 0),
                "messages_ready": queue.get("messages_ready", 0),
                "messages_unacknowledged": queue.get("messages_unacknowledged", 0),
                "consumers": queue.get("consumers", 0),
                "consumer_utilisation": queue.get("consumer_utilisation", 0),
            }

        return main_queues


def get_celery_tasks_data() -> dict[str, Any]:
    monitor = CeleryMonitoring()
    return monitor.get_tasks_data()


def get_rabbitmq_queues_info() -> dict[str, dict[str, Any]]:
    monitor = RabbitMQMonitoring()
    return monitor.get_main_queues_info()

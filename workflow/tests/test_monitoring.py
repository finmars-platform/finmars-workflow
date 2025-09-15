from unittest.mock import patch

from rest_framework.test import APIClient

from workflow.models import Space, User
from workflow.tests.base import BaseTestCase


class MonitoringViewSetTestCase(BaseTestCase):
    def setUp(self):
        self.client = APIClient()
        self.realm_code = f"realm{self.random_string(5)}"
        self.space_code = f"space{self.random_string(5)}"
        self.space = Space.objects.create(realm_code=self.realm_code, space_code=self.space_code)
        self.user = User.objects.create(
            username=self.random_string(5),
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(self.user)

    @patch("workflow.views.get_celery_tasks_data")
    def test_celery_monitoring_view_success(self, mock_get_tasks_data):
        mock_tasks_data = {
            "workflow": {
                "worker00": {
                    "active_tasks": [
                        {
                            "acknowledged": False,
                            "args": [None],
                            "delivery_info": {
                                "exchange": "",
                                "priority": None,
                                "redelivered": False,
                                "routing_key": "workflow",
                            },
                            "hostname": "workflow@worker00",
                            "id": "task1",
                            "kwargs": {"context": {"realm_code": "realm1", "space_code": "space1"}, "workflow_id": 1},
                            "name": "workflow.tasks.test",
                            "time_start": 1757891351.975915,
                            "type": "workflow.tasks.test",
                            "worker_pid": 78733,
                        }
                    ],
                    "scheduled_tasks": [],
                    "pending_tasks": [],
                    "active_tasks_count": 1,
                    "pending_tasks_count": 0,
                    "scheduled_tasks_count": 0,
                    "total_tasks_count": 1,
                }
            }
        }
        mock_get_tasks_data.return_value = mock_tasks_data

        url = f"/{self.realm_code}/{self.space_code}/workflow/api/monitoring/celery/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("workflow", data)
        self.assertIn("worker00", data["workflow"])
        self.assertEqual(data["workflow"]["worker00"]["active_tasks_count"], 1)
        self.assertEqual(data["workflow"]["worker00"]["total_tasks_count"], 1)

    @patch("workflow.views.get_celery_tasks_data")
    def test_celery_monitoring_view_error(self, mock_get_tasks_data):
        mock_get_tasks_data.side_effect = Exception("Celery connection failed")

        url = f"/{self.realm_code}/{self.space_code}/workflow/api/monitoring/celery/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Celery connection failed")

    @patch("workflow.views.get_rabbitmq_queues_info")
    def test_rabbitmq_monitoring_view_success(self, mock_get_queues_info):
        mock_queues_data = {
            "workflow": {
                "workflow": {
                    "name": "workflow",
                    "messages": 5,
                    "messages_ready": 3,
                    "messages_unacknowledged": 2,
                    "consumers": 1,
                    "consumer_utilisation": 0.8,
                }
            },
            "backend": {
                "backend-task1": {
                    "name": "backend-task1",
                    "messages": 10,
                    "messages_ready": 8,
                    "messages_unacknowledged": 2,
                    "consumers": 2,
                    "consumer_utilisation": 0.6,
                }
            },
        }
        mock_get_queues_info.return_value = mock_queues_data

        url = f"/{self.realm_code}/{self.space_code}/workflow/api/monitoring/rabbitmq/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("workflow", data)
        self.assertIn("backend", data)
        self.assertIn("workflow", data["workflow"])
        self.assertIn("backend-task1", data["backend"])

        workflow_queue = data["workflow"]["workflow"]
        self.assertEqual(workflow_queue["messages"], 5)
        self.assertEqual(workflow_queue["consumers"], 1)

    @patch("workflow.views.get_rabbitmq_queues_info")
    def test_rabbitmq_monitoring_view_error(self, mock_get_queues_info):
        mock_get_queues_info.side_effect = Exception("RabbitMQ connection failed")

        url = f"/{self.realm_code}/{self.space_code}/workflow/api/monitoring/rabbitmq/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "RabbitMQ connection failed")

    @patch("workflow.views.get_celery_tasks_data")
    @patch("workflow.views.get_rabbitmq_queues_info")
    def test_monitoring_endpoints_consistency(self, mock_rabbitmq, mock_celery):
        mock_celery.return_value = {}
        mock_rabbitmq.return_value = {}

        celery_url = f"/{self.realm_code}/{self.space_code}/workflow/api/monitoring/celery/"
        rabbitmq_url = f"/{self.realm_code}/{self.space_code}/workflow/api/monitoring/rabbitmq/"

        celery_response = self.client.get(celery_url)
        rabbitmq_response = self.client.get(rabbitmq_url)

        self.assertEqual(celery_response.status_code, 200)
        self.assertEqual(rabbitmq_response.status_code, 200)

        mock_celery.assert_called_once()
        mock_rabbitmq.assert_called_once()

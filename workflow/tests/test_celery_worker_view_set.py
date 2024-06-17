from unittest.mock import patch, ANY
from rest_framework import status
from rest_framework.test import APIClient
from .base import BaseTestCase


class CeleryWorkerViewSetTestCase(BaseTestCase):
    def setUp(self):
        self.realm_code = f"realm{self.random_string(5)}"
        self.space_code = f"space{self.random_string(5)}"
        self.url_prefix = f"/{self.realm_code}/{self.space_code}/workflow/api/worker"
        self.client = APIClient()
        worker_name = f"test_worker_{self.random_string(5)}"
        self.worker = dict(
            id=worker_name,
            worker_name=worker_name,
            worker_type="worker",
            status="unknown",
            notes="Test worker",
            memory_limit="2Gi",
            queue="workflow",
        )

    @patch("workflow.views.CeleryWorkerViewSet.authorizer_service.get_workers")
    def test_create_method(self, mock_get_workers):
        mock_get_workers.return_value = [self.worker]
        url = f"{self.url_prefix}/"
        response = self.client.post(url, data=self.worker)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_method_raises_permission_denied(self):
        url = f"{self.url_prefix}/{self.worker['id']}/"
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("workflow.views.CeleryWorkerViewSet.authorizer_service.create_worker")
    def test_create_worker_action(self, mock_create_worker):
        url = f"{self.url_prefix}/{self.worker['id']}/create-worker/"
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})
        mock_create_worker.assert_called_once_with(self.worker['id'], self.realm_code)

    @patch("workflow.views.CeleryWorkerViewSet.authorizer_service.start_worker")
    def test_start_action(self, mock_start_worker):
        url = f"{self.url_prefix}/{self.worker['id']}/start/"
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})
        mock_start_worker.assert_called_once_with(self.worker['id'], self.realm_code)

    @patch("workflow.views.CeleryWorkerViewSet.authorizer_service.stop_worker")
    def test_stop_action(self, mock_stop_worker):
        url = f"{self.url_prefix}/{self.worker['id']}/stop/"
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})
        mock_stop_worker.assert_called_once_with(self.worker['id'], self.realm_code)

    @patch("workflow.views.CeleryWorkerViewSet.authorizer_service.restart_worker")
    def test_restart_action(self, mock_restart_worker):
        url = f"{self.url_prefix}/{self.worker['id']}/restart/"
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})
        mock_restart_worker.assert_called_once_with(self.worker['id'], self.realm_code)

    @patch("workflow.views.CeleryWorkerViewSet.authorizer_service.get_worker_status")
    def test_status_action(self, mock_get_worker_status):
        mock_get_worker_status.return_value = {"status": "running"}
        url = f"{self.url_prefix}/{self.worker['id']}/status/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})
        mock_get_worker_status.assert_called_once_with(self.worker['id'], self.realm_code)

    @patch("workflow.views.CeleryWorkerViewSet.authorizer_service.delete_worker")
    def test_destroy_method(self, mock_delete_worker):
        url = f"{self.url_prefix}/{self.worker['id']}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_delete_worker.assert_called_once_with(ANY, self.realm_code)
        self.assertEqual(mock_delete_worker.call_args_list[0].args[0], self.worker['id'])

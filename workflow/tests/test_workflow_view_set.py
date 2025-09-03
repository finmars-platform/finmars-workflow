from datetime import date
from rest_framework.test import APIClient
from workflow.models import Workflow, User, Space
from workflow.tests.factories import WorkflowTemplateFactory

from .base import BaseTestCase


class WorkflowViewSetFilterTestCase(BaseTestCase):
    def setUp(self):
        self.client = APIClient()
        self.realm_code = f"realm{self.random_string(5)}"
        self.space_code = f"space{self.random_string(5)}"
        self.url_prefix = f"/{self.realm_code}/{self.space_code}/workflow/api/workflow/"
        self.space = Space.objects.create(
            realm_code=self.realm_code, space_code=self.space_code
        )
        self.user = User.objects.create(
            username=self.random_string(5),
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(self.user)

        self.workflow1 = Workflow.objects.create(
            space=self.space,
            owner=self.user,
            name="Workflow 1",
            user_code="workflow1",
            status="init",
            payload_data='{"key": "test1"}',
        )
        self.workflow1.created_at = date(2024, 6, 1)
        self.workflow1.save()

        self.workflow2 = Workflow.objects.create(
            space=self.space,
            owner=self.user,
            name="Workflow 2",
            user_code="workflow2",
            status="pending",
            payload_data='{"key": "test2"}',
        )
        self.workflow2.created_at = date(2024, 7, 1)
        self.workflow2.save()

        workflow_template = WorkflowTemplateFactory(space=self.space, owner=self.user)
        self.workflow3 = Workflow.objects.create(
            space=self.space,
            owner=self.user,
            name="Workflow 3",
            user_code="workflow3",
            status="pending",
            payload_data='{"key": "test3"}',
            workflow_template=workflow_template,
        )
        self.workflow3.created_at = date(2024, 8, 1)
        self.workflow3.save()

    def test_filter_queryset_payload(self):
        response = self.client.get(self.url_prefix, {"payload": "test1"})
        ids = [w["id"] for w in response.data["results"]]
        self.assertIn(self.workflow1.id, ids)
        self.assertNotIn(self.workflow2.id, ids)
        self.assertTrue(
            all([w for w in response.data["results"] if "another" in w["payload"]])
        )

    def test_filter_queryset_payload_partial_not_found(self):
        response = self.client.get(self.url_prefix, {"payload": "test"})
        ids = [w["id"] for w in response.data["results"]]
        self.assertNotIn(self.workflow2.id, ids)
        self.assertNotIn(self.workflow1.id, ids)

    def test_filter_queryset_date_range(self):
        response = self.client.get(
            self.url_prefix,
            {"created_at_after": "2024-01-01", "created_at_before": "2024-06-30"},
        )
        ids = [w["id"] for w in response.data["results"]]
        self.assertIn(self.workflow1.id, ids)
        self.assertNotIn(self.workflow2.id, ids)

    def test_light_filter_queryset_search(self):
        response = self.client.get(f"{self.url_prefix}light/", {"query": "workflow2"})
        self.assertEqual(response.data["count"], 1)
        ids = [w["id"] for w in response.data["results"]]
        self.assertIn(self.workflow2.id, ids)
        self.assertNotIn(self.workflow1.id, ids)

    def test_workflow_verions_1(self):
        response = self.client.get(f"{self.url_prefix}{self.workflow2.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["workflow_version"], 1)

    def test_workflow_verions_2(self):
        response = self.client.get(f"{self.url_prefix}{self.workflow3.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["workflow_version"], 2)

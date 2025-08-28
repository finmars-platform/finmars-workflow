from datetime import timedelta

from rest_framework.test import APIClient

from workflow.tests.factories import SpaceFactory, UserFactory, WorkflowTemplateFactory

from .base import BaseTestCase


class WorkflowViewSetFilterTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.space = SpaceFactory()
        cls.url = f"/{cls.space.realm_code}/{cls.space.space_code}/workflow/api/workflow-template/"

        cls.user = UserFactory(is_staff=True, is_superuser=True)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.workflow_template1 = WorkflowTemplateFactory(space=self.space, owner=self.user)
        self.workflow_template2 = WorkflowTemplateFactory(space=self.space, owner=self.user)

    def get_ids(self, response):
        return [w["id"] for w in response.data["results"]]

    def test_get_list(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_filter_queryset_date_range(self):
        created_at_after = (self.workflow_template1.created_at - timedelta(days=1)).strftime("%Y-%m-%d")
        crated_at_before = (self.workflow_template1.created_at + timedelta(days=1)).strftime("%Y-%m-%d")
        self.workflow_template2.created_at -= timedelta(days=3)
        self.workflow_template2.save()

        response = self.client.get(
            self.url,
            {
                "created_at_after": created_at_after,
                "created_at_before": crated_at_before,
            },
        )

        self.assertEqual(response.status_code, 200)

        ids = self.get_ids(response)
        self.assertIn(self.workflow_template1.id, ids)
        self.assertNotIn(self.workflow_template2.id, ids)

    def test_filter_query_user_code(self):
        response = self.client.get(self.url, {"user_code": self.workflow_template1.user_code})

        self.assertEqual(response.status_code, 200)

        ids = self.get_ids(response)
        self.assertIn(self.workflow_template1.id, ids)
        self.assertNotIn(self.workflow_template2.id, ids)

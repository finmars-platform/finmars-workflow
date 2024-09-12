from datetime import date

from workflow.models import Space, Workflow

from .base import BaseTestCase


class WorkflowViewSetFilterTestCase(BaseTestCase):
    def setUp(self):
        self.init_test_case()

        self.url_prefix = f"/{self.realm_code}/{self.space_code}/workflow/api/workflow/"

        self.space = Space.objects.create(
            realm_code=self.realm_code, space_code=self.space_code
        )

        self.workflow1 = Workflow.objects.create(
            space=self.space,
            owner=self.user,
            name="Workflow 1",
            user_code="workflow1",
            status="init",
            payload_data='{"key": "test1"}',
        )
        self.workflow1.created = date(2024, 6, 1)
        self.workflow1.save()

        self.workflow2 = Workflow.objects.create(
            space=self.space,
            owner=self.user,
            name="Workflow 2",
            user_code="workflow2",
            status="pending",
            payload_data='{"key": "test2"}',
        )
        self.workflow2.created = date(2024, 7, 1)
        self.workflow2.save()

    def test_filter_queryset_payload(self):
        response = self.client.get(self.url_prefix, {"payload": "test1"})
        ids = [w["id"] for w in response.data["results"]]
        self.assertIn(self.workflow1.id, ids)
        self.assertNotIn(self.workflow2.id, ids)
        self.assertTrue(
            all(w for w in response.data["results"] if "another" in w["payload"])
        )

    def test_filter_queryset_payload_partial_not_found(self):
        response = self.client.get(self.url_prefix, {"payload": "test"})
        ids = [w["id"] for w in response.data["results"]]
        self.assertNotIn(self.workflow2.id, ids)
        self.assertNotIn(self.workflow1.id, ids)

    def test_filter_queryset_date_range(self):
        response = self.client.get(
            self.url_prefix,
            {"created_after": "2024-01-01", "created_before": "2024-06-30"},
        )
        ids = [w["id"] for w in response.data["results"]]
        self.assertIn(self.workflow1.id, ids)
        self.assertNotIn(self.workflow2.id, ids)

from rest_framework import status
from rest_framework.test import APIClient
from workflow.models import Schedule, User, Space
from workflow.system import get_system_workflow_manager

from .base import BaseTestCase


class ScheduleViewSetTestCase(BaseTestCase):
    def setUp(self):
        self.client = APIClient()
        self.realm_code = f"realm{self.random_string(5)}"
        self.space_code = f"space{self.random_string(5)}"
        self.url_prefix = f"/{self.realm_code}/{self.space_code}/workflow/api/schedule/"
        self.space = Space.objects.create(realm_code=self.realm_code, space_code=self.space_code)
        self.user = User.objects.create(
            username=self.random_string(5),
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(self.user)

        manager = get_system_workflow_manager()
        manager.workflows = {
            f"{self.space.space_code}.new_workflow": 'test',
            f"{self.space_code}.updated_workflow": 'test'
        }

        self.schedule = Schedule.objects.create(
            user_code='test_workflow',
            space=self.space,
            owner=self.user,
            crontab_line='0 * * * *',
            payload={"test": "data"},
            is_manager=False
        )

    def test_list_schedules(self):
        response = self.client.get(self.url_prefix)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_schedule(self):
        response = self.client.get(self.url_prefix + f"{self.schedule.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user_code'], 'test_workflow')

    def test_create_schedule(self):
        data = {
            'user_code': 'new_workflow',
            'crontab_line': '0 * * * *',
            'payload': {"new": "data"}
        }
        response = self.client.post(self.url_prefix, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Schedule.objects.count(), 2)

    def test_update_schedule(self):
        data = {
            'user_code': 'updated_workflow',
            'crontab_line': '30 * * * *',
            'payload': {"updated": "data"}
        }
        response = self.client.patch(self.url_prefix + f"{self.schedule.pk}/", data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.user_code, data['user_code'])
        self.assertEqual(self.schedule.crontab_line, data['crontab_line'])

    def test_delete_schedule(self):
        response = self.client.delete(self.url_prefix + f"{self.schedule.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Schedule.objects.count(), 0)

    def test_invalid_crontab_line(self):
        data = {
            'user_code': 'new_workflow',
            'space': self.space.id,
            'crontab_line': 'invalid crontab',
            'payload': {"new": "data"}
        }
        response = self.client.post(self.url_prefix, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

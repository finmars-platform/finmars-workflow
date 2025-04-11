from datetime import datetime, timedelta
import json
import requests

from celery.utils.log import get_task_logger
from django.conf import settings

from workflow.finmars import get_refresh_token, get_space
from workflow_app import celery_app

logger = get_task_logger(__name__)

@celery_app.task(bind=True)
def call_export_backend_historical_records(self, *args, **kwargs):
    logger.info("Calling export backend historical records")

    days = kwargs.get("days", 90)

    refresh = get_refresh_token()
    space = get_space()

    headers = {"Content-type": "application/json", "Accept": "application/json",
               "Authorization": f"Bearer {refresh.access_token}"}

    data = {"date_to": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")}

    if space.realm_code and space.realm_code != "realm00000":
        url = "https://" + settings.DOMAIN_NAME + "/" + space.realm_code + "/" + space.space_code + "/api/v1/history/historical-record/export/"
    else:
        url = "https://" + settings.DOMAIN_NAME + "/" + space.space_code + "/api/v1/history/historical-record/export/"

    response = requests.post(url=url, data=json.dumps(data), headers=headers, verify=settings.VERIFY_SSL)

    if response.status_code != 200:
        logger.error(response.text)
        raise Exception(response.text)
    
    logger.info(f"Export backend historical records response: {response.text}")

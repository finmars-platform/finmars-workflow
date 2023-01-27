import os
import traceback

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS
from django.db.models.signals import post_migrate

import logging

from workflow_app import settings

_l = logging.getLogger('workflow')

class WorkflowConfig(AppConfig):
    name = 'workflow'



import os
from pathlib import Path

from environs import Env
import warnings

def ENV_BOOL(env_name, default):

    val = os.environ.get(env_name, default)

    if not val:
        return default

    if val == 'True' or val == True:
        return True

    if val == 'False' or val == False:
        return False

    warnings.warn('Variable %s is not boolean. It is %s' % (env_name, val))

def ENV_STR(env_name, default):

    val = os.environ.get(env_name, default)

    if not val:
        return default

    return val

def ENV_INT(env_name, default):

    val = os.environ.get(env_name, default)

    if not val:
        return default

    return int(val)


HIDDEN_CONFIG = [
    "DIRECTOR_ENABLE_HISTORY_MODE",
    "DIRECTOR_REFRESH_INTERVAL",
    "DIRECTOR_API_URL",
    "DIRECTOR_FLOWER_URL",
    "DIRECTOR_DATABASE_URI",
    "DIRECTOR_DATABASE_POOL_RECYCLE",
    "DIRECTOR_BROKER_URI",
    "DIRECTOR_RESULT_BACKEND_URI",
    "DIRECTOR_SENTRY_DSN",
]


print("==== Director init Config ====")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRECTOR_LOCAL_DIR = BASE_DIR + '/app-data'

BASE_API_URL = ENV_STR('BASE_API_URL', 'space00000')

ENABLE_HISTORY_MODE = ENV_BOOL("DIRECTOR_ENABLE_HISTORY_MODE", False)
ENABLE_CDN = ENV_BOOL("DIRECTOR_ENABLE_CDN", True)
API_URL = ENV_STR("DIRECTOR_API_URL", "http://0.0.0.0:8001/api")
print('API_URL %s' % API_URL)
FLOWER_URL = ENV_STR("DIRECTOR_FLOWER_URL", "http://127.0.0.1:5555")
WORKFLOWS_PER_PAGE = ENV_INT("DIRECTOR_WORKFLOWS_PER_PAGE", 1000)
REFRESH_INTERVAL = ENV_INT("DIRECTOR_REFRESH_INTERVAL", 30000)
REPO_LINK = ENV_STR(
    "DIRECTOR_REPO_LINK", "https://github.com/ovh/celery-director"
)
DOCUMENTATION_LINK = ENV_STR(
    "DIRECTOR_DOCUMENTATION_LINK", "https://ovh.github.io/celery-director"
)

# Authentication
AUTH_ENABLED = ENV_BOOL("DIRECTOR_AUTH_ENABLED", False)

# SQLAlchemy configuration
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = ENV_STR("DIRECTOR_DATABASE_URI", "")
print('SQLALCHEMY_DATABASE_URI %s' % SQLALCHEMY_DATABASE_URI)
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_recycle": ENV_INT("DIRECTOR_DATABASE_POOL_RECYCLE", -1),
}

RABBITMQ_HOST = ENV_STR('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = ENV_INT('RABBITMQ_PORT', 5672)
RABBITMQ_USER = ENV_STR('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = ENV_STR('RABBITMQ_PASSWORD', 'guest')
RABBITMQ_VHOST = ENV_STR('RABBITMQ_VHOST', '')

# Celery configuration
CELERY_CONF = {
    "task_always_eager": False,
    "broker_url": 'amqp://%s:%s@%s:%s/%s' % (RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_VHOST),
    "result_backend": 'db+' + ENV_STR("DIRECTOR_DATABASE_URI", ""),
    "broker_transport_options": {"master_name": "director"},
}

# Sentry configuration
SENTRY_DSN = ENV_STR("DIRECTOR_SENTRY_DSN", "")

# Default retention value (number of workflows to keep in the database)
DEFAULT_RETENTION_OFFSET = ENV_INT("DIRECTOR_DEFAULT_RETENTION_OFFSET", -1)

# Enable Vue debug loading vue.js instead of vue.min.js
VUE_DEBUG = ENV_BOOL("DIRECTOR_VUE_DEBUG", False)


# ============
# = Storages =
# ============

USE_FILESYSTEM_STORAGE = ENV_BOOL('USE_FILESYSTEM_STORAGE', False)
SFTP_STORAGE_HOST = ENV_STR('SFTP_STORAGE_HOST', None)
SFTP_STORAGE_ROOT = os.environ.get('SFTP_ROOT', '/finmars/')
SFTP_PKEY_PATH = os.environ.get('SFTP_PKEY_PATH', None)

SFTP_STORAGE_PARAMS = {
    'username': os.environ.get('SFTP_USERNAME', None),
    'password': os.environ.get('SFTP_PASSWORD', None),
    'port': ENV_INT('SFTP_PORT', 22),
    'allow_agent': False,
    'look_for_keys': False,
}
if SFTP_PKEY_PATH:
    SFTP_STORAGE_PARAMS['key_filename'] = SFTP_PKEY_PATH

SFTP_STORAGE_INTERACTIVE = False
SFTP_KNOWN_HOST_FILE = os.path.join(BASE_DIR, '.ssh/known_hosts')

AWS_CLOUDFRONT_KEY_ID = None
AWS_S3_ACCESS_KEY_ID = os.environ.get('AWS_S3_ACCESS_KEY_ID', None)
AWS_S3_SECRET_ACCESS_KEY = os.environ.get('AWS_S3_SECRET_ACCESS_KEY', None)
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', None)
AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', None)
AWS_S3_VERIFY = os.environ.get('AWS_S3_VERIFY', None)
if os.environ.get('AWS_S3_VERIFY') == 'False':
    AWS_S3_VERIFY = False

AZURE_ACCOUNT_KEY = os.environ.get('AZURE_ACCOUNT_KEY', None)
AZURE_ACCOUNT_NAME = os.environ.get('AZURE_ACCOUNT_NAME', None)
AZURE_CONTAINER = os.environ.get('AZURE_CONTAINER', None)
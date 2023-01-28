"""
Django settings for workflow project.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

import os
from workflow_app.utils import ENV_BOOL, ENV_STR, ENV_INT, print_finmars

print_finmars()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DJANGO_LOG_LEVEL = ENV_STR('DJANGO_LOG_LEVEL', 'INFO')
BASE_API_URL = ENV_STR('BASE_API_URL', 'space00000')
AUTHORIZER_URL = ENV_STR('AUTHORIZER_URL', None)
FLOWER_URL = ENV_STR('FLOWER_URL', BASE_API_URL + '/flower')
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = ENV_BOOL('DEBUG', False)
USE_FILESYSTEM_STORAGE = ENV_BOOL('USE_FILESYSTEM_STORAGE', False)
MEDIA_ROOT = os.path.join(BASE_DIR, 'app-data')

# Very Important MasterUserConfigs encrypted by this key
# Also Session (if enabled) are using it
SECRET_KEY = ENV_STR('SECRET_KEY', None)
PROVISION_MANAGER = ENV_STR('PROVISION_MANAGER', 'rancher')

SERVER_TYPE = ENV_STR('SERVER_TYPE', 'local') # local, development, production
HOST_LOCATION = ENV_STR('HOST_LOCATION', 'local')  # local, azure, aws, private cloud or custom, only for log purpose
HOST_URL = ENV_STR('HOST_URL', 'http://0.0.0.0:8000')
ALLOWED_HOST = ENV_STR('ALLOWED_HOST', '*')
DOMAIN_NAME = ENV_STR('DOMAIN_NAME', 'finmars.com')

REGISTER_ACCESS_KEY = ENV_STR('REGISTER_ACCESS_KEY', None) # deprecated, for newly created users to auto-activate
INSTALLATION_TYPE = ENV_STR('INSTALLATION_TYPE', "cloud") # cloud, hnwi_client, private_cloud

# possible deprecated, 0 - local 1 eu-central 2 - zurich, should be generated in licnse server
BASE_API_URL_PREFIX = ENV_STR('BASE_API_URL_PREFIX', '0')
# This property needs if hosted in private network with self-signed certs
VERIFY_SSL = ENV_BOOL('VERIFY_SSL', True)

# =======================
# = License Server Host =
# =======================
LICENSE_SERVER_HOST = ENV_STR('LICENSE_SERVER_HOST', 'https://license.finmars.com')

# ==========================
# = Application definition =
# ==========================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_filters',
    'corsheaders',

    'healthcheck',

    'workflow',
    'rest_framework',
    # 'rest_framework.authtoken'

    'finmars_standardized_errors',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'corsheaders.middleware.CorsMiddleware',

    'finmars_standardized_errors.middleware.ExceptionMiddleware'
]

ROOT_URLCONF = 'workflow_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'workflow', 'templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'workflow.context_processors.workflow',
            ],
        },
    },
]

WSGI_APPLICATION = 'workflow_app.wsgi.application'

# https://docs.djangoproject.com/en/4.1/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [ALLOWED_HOST]

# ============
# = Database =
# ============
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': ENV_STR('DB_NAME', None),
        'USER': ENV_STR('DB_USER', None),
        'PASSWORD': ENV_STR('DB_PASSWORD', None),
        'HOST': ENV_STR('DB_HOST', None),
        'PORT': ENV_INT('DB_PORT', 5432)
    }
}

AUTH_USER_MODEL = 'workflow.User'

# ==================================
# = Default primary key field type =
# ==================================
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# =======================
# = Password validation =
# =======================
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

PASSWORD_HASHERS = [
    'workflow.hashers.PBKDF2SHA512PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ========================
# = Static Configuration =
# ========================

STATIC_URL = '/' + BASE_API_URL + '/workflow/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "static")


STATICFILES_DIR = (
    os.path.join(BASE_DIR, 'static'),
)

# ========================
# = Internationalization =
# ========================
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    # ('es', 'Spanish'),
    # ('de', 'Deutsch'),
    # ('ru', 'Russian'),
]

# =================
# = CSRF SETTINGS =
# =================
# TODO Refactor this block

ENV_CSRF_TRUSTED_ORIGINS = ENV_STR('ENV_CSRF_TRUSTED_ORIGINS', None)

if SERVER_TYPE == "production":
    CORS_URLS_REGEX = r'^/workflow/.*$'
    # CORS_REPLACE_HTTPS_REFERER = True
    CORS_ALLOW_CREDENTIALS = True
    CORS_PREFLIGHT_MAX_AGE = 300
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_REDIRECT_EXEMPT = ['healthcheck']
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = 'Strict'

if SERVER_TYPE == "development":
    CORS_ORIGIN_ALLOW_ALL = True
    CORS_URLS_REGEX = r'^/workflow/.*$'
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    CORS_ALLOW_CREDENTIALS = True

if SERVER_TYPE == "local":
    CORS_URLS_REGEX = r'^/workflow/.*$'
    CORS_ALLOW_CREDENTIALS = True
    CORS_ORIGIN_ALLOW_ALL = True

# ==================
# = REST_FRAMEWORK =
# ==================

REST_FRAMEWORK = {
    'PAGE_SIZE': 40,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # 'rest_framework.authentication.SessionAuthentication',
        # 'rest_framework.authentication.BasicAuthentication',
        # 'rest_framework.authentication.TokenAuthentication',
        "workflow.authentication.KeycloakAuthentication",
        'rest_framework_simplejwt.authentication.JWTAuthentication',

    ),
    # 'EXCEPTION_HANDLER': 'authorizer.utils.finmars_exception_handler',
    'EXCEPTION_HANDLER': 'finmars_standardized_errors.handler.exception_handler',
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    # 'DEFAULT_PERMISSION_CLASSES': (
    #     'rest_framework.permissions.IsAuthenticated',
    # ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    # 'DEFAULT_PARSER_CLASSES': (
    # 'rest_framework.parsers.JSONParser',
    # 'rest_framework.parsers.FormParser',
    # 'rest_framework.parsers.MultiPartParser',
    # ),
    'DEFAULT_THROTTLE_RATES': {
        # 'anon': '5/second',
        # 'user': '50/second',
        'anon': '20/min',
        'user': '500/min',
    },

    # 'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S %Z',
    # 'DATETIME_INPUT_FORMATS': (ISO_8601, '%c', '%Y-%m-%d %H:%M:%S %Z'),
}

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] += (
    'rest_framework.renderers.BrowsableAPIRenderer',
    'rest_framework.renderers.AdminRenderer',
)

# ===========
# = LOGGING =
# ===========

SEND_LOGS_TO_FINMARS = ENV_BOOL('SEND_LOGS_TO_FINMARS', False)
FINMARS_LOGSTASH_HOST = ENV_STR('FINMARS_LOGSTASH_HOST', '3.123.159.169')
FINMARS_LOGSTASH_PORT = ENV_INT('FINMARS_LOGSTASH_PORT', 5044)

LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '[' + HOST_LOCATION + '] [workflow] [%(levelname)s] [%(asctime)s] [%(processName)s] [%(name)s] [%(module)s:%(lineno)d] - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': DJANGO_LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': DJANGO_LOG_LEVEL,
            'class': 'logging.FileHandler',
            'filename': '/var/log/finmars/workflow/django.log',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django.request': {
            "level": "ERROR",
            "handlers": ["console", "file"]
        },
        "django": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True
        },
        "workflow": {
            "level": DJANGO_LOG_LEVEL,
            "handlers": ["console", "file"],
            "propagate": True
        }
    }
}

if SEND_LOGS_TO_FINMARS:

    print("Logs will be sending to Finmars")

    LOGGING['handlers']['logstash'] = {
        'level': DJANGO_LOG_LEVEL,
        'class': 'logstash.TCPLogstashHandler',
        'host': FINMARS_LOGSTASH_HOST,
        'port': FINMARS_LOGSTASH_PORT,  # Default value: 5959
        'message_type': 'finmars-backend',  # 'type' field in logstash message. Default value: 'logstash'.
        'fqdn': False,  # Fully qualified domain name. Default value: false.
        'ssl_verify': False,  # Fully qualified domain name. Default value: false.
        # 'tags': ['tag1', 'tag2'],  # list of tags. Default: None.
    }

    LOGGING['loggers']['django.request']['handlers'].append('logstash')
    LOGGING['loggers']['django']['handlers'].append('logstash')
    LOGGING['loggers']['workflow']['handlers'].append('logstash')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    },
    'throttling': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'http_session': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}


# =================
# = SMTP Settings =
# =================

EMAIL_HOST = ENV_STR('EMAIL_HOST', 'email-smtp.eu-west-1.amazonaws.com')
EMAIL_PORT = ENV_INT('EMAIL_PORT', 587)
EMAIL_HOST_USER = ENV_STR('EMAIL_HOST_USER', None)
EMAIL_HOST_PASSWORD = ENV_STR('EMAIL_HOST_PASSWORD', None)
EMAIL_USE_TLS = ENV_BOOL('EMAIL_USE_TLS', True)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# ==========
# = CELERY =
# ==========

RABBITMQ_HOST = ENV_STR('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = ENV_INT('RABBITMQ_PORT', 5672)
RABBITMQ_USER = ENV_STR('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = ENV_STR('RABBITMQ_PASSWORD', 'guest')
RABBITMQ_VHOST = ENV_STR('RABBITMQ_VHOST', '')

CELERY_BROKER_URL = 'amqp://%s:%s@%s:%s/%s' % (RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_VHOST)

CELERY_RESULT_BACKEND = 'db+postgresql+psycopg2://%s:%s@%s:%s/%s' %  (ENV_STR('DB_USER', None), ENV_STR('DB_PASSWORD', None), ENV_STR('DB_HOST', None), ENV_INT('DB_PORT', 5432), ENV_STR('DB_NAME', None))
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = 'UTC'

DJANGO_CELERY_RESULTS_TASK_ID_MAX_LENGTH=191

# ==============
# = WEBSOCKETS =
# ==============

USE_WEBSOCKETS = ENV_BOOL('USE_WEBSOCKETS', False)
WEBSOCKET_HOST = ENV_STR('WEBSOCKET_HOST', 'ws://0.0.0.0:6969')
WEBSOCKET_APP_TOKEN = ENV_STR('WEBSOCKET_APP_TOKEN', None)

# ===================
# = Django Storages =
# ===================

SFTP_STORAGE_HOST = ENV_STR('SFTP_STORAGE_HOST', None)
SFTP_STORAGE_ROOT = ENV_STR('SFTP_STORAGE_ROOT', '/finmars/')
SFTP_PKEY_PATH = ENV_STR('SFTP_PKEY_PATH', None)

SFTP_STORAGE_PARAMS = {
    'username': ENV_STR('SFTP_USERNAME', None),
    'password': ENV_STR('SFTP_PASSWORD', None),
    'port': ENV_INT('SFTP_PORT', 22),
    'allow_agent': False,
    'look_for_keys': False,
}
if SFTP_PKEY_PATH:
    SFTP_STORAGE_PARAMS['key_filename'] = SFTP_PKEY_PATH

SFTP_STORAGE_INTERACTIVE = False
SFTP_KNOWN_HOST_FILE = os.path.join(BASE_DIR, '.ssh/known_hosts')

AWS_S3_ACCESS_KEY_ID = ENV_STR('AWS_S3_ACCESS_KEY_ID', None)
AWS_S3_SECRET_ACCESS_KEY = ENV_STR('AWS_S3_SECRET_ACCESS_KEY', None)
AWS_STORAGE_BUCKET_NAME = ENV_STR('AWS_STORAGE_BUCKET_NAME', None)
AWS_S3_ENDPOINT_URL = ENV_STR('AWS_S3_ENDPOINT_URL', None)

AZURE_ACCOUNT_KEY = ENV_STR('AZURE_ACCOUNT_KEY', None)
AZURE_ACCOUNT_NAME = ENV_STR('AZURE_ACCOUNT_NAME', None)
AZURE_CONTAINER = ENV_STR('AZURE_CONTAINER', None)

# ========================
# = KEYCLOAK INTEGRATION =
# ========================

KEYCLOAK_SERVER_URL = os.environ.get('KEYCLOAK_SERVER_URL', 'https://eu-central.finmars.com')
KEYCLOAK_REALM = os.environ.get('KEYCLOAK_REALM', 'finmars')
KEYCLOAK_CLIENT_ID = os.environ.get('KEYCLOAK_CLIENT_ID', 'finmars-workflow')
KEYCLOAK_CLIENT_SECRET_KEY = os.environ.get('KEYCLOAK_CLIENT_SECRET_KEY', None)  # not required anymore, api works in Bearer-only mod


X_FRAME_OPTIONS = 'ALLOWALL'

XS_SHARING_ALLOWED_METHODS = ['POST','GET','OPTIONS', 'PUT', 'DELETE']

SIMPLE_JWT = {"SIGNING_KEY": os.getenv("SIGNING_KEY", SECRET_KEY), 'USER_ID_FIELD': 'username'}
import os


chdir = "/var/app/"
project_name = os.getenv("PROJECT_NAME", "workflow_app")

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8080")

workers = int(os.getenv("GUNICORN_WORKERS", "1"))
threads = int(os.getenv("GUNICORN_THREADS", os.cpu_count()))

timeout = int(os.getenv("GUNICORN_TIMEOUT", "180"))

accesslog = "/var/log/finmars/workflow/gunicorn.access.log"
errorlog = "/var/log/finmars/workflow/gunicorn.error.log"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

reload = bool(os.getenv("LOCAL"))

INSTANCE_TYPE = os.getenv("INSTANCE_TYPE", "web")

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', None)

FLOWER_URL_PREFIX = os.getenv('FLOWER_URL_PREFIX', '')

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = os.getenv('RABBITMQ_PORT', 5672)
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')
RABBITMQ_VHOST = os.getenv('RABBITMQ_VHOST', '')

CELERY_BROKER_URL = 'amqp://%s:%s@%s:%s/%s' % (
    RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_VHOST)

def on_starting(server):
    if INSTANCE_TYPE == "web":
        print("I'm web_instance")
        # os.system("python /var/app/manage.py copy_css_libs")
        # os.system("python /var/app/manage.py copy_js_libs")
        os.system("python /var/app/manage.py collectstatic -c --noinput")
    else:
        print("Gunicorn should not start for INSTANCE_TYPE:", INSTANCE_TYPE)
        server.log.info("Exiting because this pod is not a web instance")
        exit(0)

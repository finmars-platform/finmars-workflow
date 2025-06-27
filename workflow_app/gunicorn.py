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
celery_queue = os.getenv("QUEUES", "workflow")
celery_worker = os.getenv("WORKER_NAME", "worker1")


ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', None)

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
        os.system("python /var/app/manage.py copy_css_libs")
        os.system("python /var/app/manage.py copy_js_libs")
        os.system("python /var/app/manage.py collectstatic -c --noinput")
    elif INSTANCE_TYPE == "worker":
        print("I'm celery_instance")
        cmd = (
            f"celery --app {project_name} worker --concurrency=1 --loglevel=INFO "
            f"--soft-time-limit=3000 -n {celery_worker} -Q {celery_queue} --max-tasks-per-child=1"
        )
        server.log.info(f"Starting: {cmd}")
        os.system(cmd)
    elif INSTANCE_TYPE == "beat":
        print("I'm celery_beat_instance")
        cmd = (
            f"celery --app {project_name} beat -l INFO "
            "--scheduler workflow.schedulers:DatabaseScheduler "
            "--pidfile=/tmp/celerybeat.pid"
        )
        server.log.info(f"Starting: {cmd}")
        os.system(cmd)
    elif INSTANCE_TYPE == "flower":
        print("I'm flower!")

        if not ADMIN_PASSWORD:
            print("I'm flower! Admin Password is not set, exit")
            exit(0)

        cmd = (
            f"celery --app {project_name}  "
            f"--broker={CELERY_BROKER_URL} "
            f"flower --basic-auth={ADMIN_USERNAME}:{ADMIN_PASSWORD} "
        )
        server.log.info(f"Starting: {cmd}")
        os.system(cmd)
    elif INSTANCE_TYPE == "job":
        print("I'm job_instance")
        server.log.info("Starting job instance")
        os.system("python /var/app/manage.py migrate_all_schemes")
        exit(0)

    else:
        print("I'm unknown_instance")
        server.log.info("Unknown instance type")
        exit(1)

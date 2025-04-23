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
celery_queue = os.getenv("QUEUES", "backend-general-queue,backend-background-queue")
celery_worker = os.getenv("WORKER_NAME", "worker1")

def on_starting(server):
    if INSTANCE_TYPE == "web":
        print("I'm web_instance")
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
    elif INSTANCE_TYPE == "job":
        print("I'm job_instance")
        server.log.info("Starting job instance")
        os.system("python /var/app/manage.py migrate_all_schemes")
        exit(0)
    else:
        print("I'm unknown_instance")
        server.log.info("Unknown instance type")
        exit(1)

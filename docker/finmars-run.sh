#!/bin/sh

USE_CELERY="${USE_CELERY:-False}"
USE_FLOWER="${$USE_FLOWER:-False}"
BASE_API_URL="${$BASE_API_URL:-False}"
RABBITMQ_HOST="${$RABBITMQ_HOST:-False}"
FAKE_MIGRATE="${FAKE_MIGRATE:-False}"

echo "Finmars initialization"


echo "set chmod 777 /var/log/finmars/workflow"

chmod 777 /var/log/finmars/workflow

echo "Create django log file /var/log/finmars/workflow/django.log"

touch /var/log/finmars/workflow/django.log

echo "set chmod 777 /var/log/finmars/workflow/django.log"

chmod 777 /var/log/finmars/workflow/django.log

mkdir /var/app/app-data
chmod 777 /var/app/app-data


# Default value is "workflow"
: "${INSTANCE_TYPE:=workflow}"

if [ "$INSTANCE_TYPE" = "workflow" ]; then
  supervisord

  echo "Run CeleryBeat"
  supervisorctl start celerybeat

  echo "Run Flower"
  supervisorctl start flower

  echo "Create admin user"

  python /var/app/manage.py generate_super_user

  echo "Run server"
  gunicorn --config /var/app/workflow_app/gunicorn-prod.py workflow_app.wsgi
  #python director.py webserver

  echo "Initialized"
elif [ "$INSTANCE_TYPE" = "worker" ]; then

  # Environment variables for the worker
  : "${WORKER_NAME:=worker1}"
  : "${QUEUES:=backend-general-queue,backend-background-queue}"

  export DJANGO_SETTINGS_MODULE=workflow_app.settings
  export C_FORCE_ROOT='true'

  echo "Cancel existing tasks"
  python /var/app/manage.py cancel_existing_tasks

  echo "Start celery"
  # cd /var/app && nohup celery --app workflow_app --broker=amqp://guest:guest@$RABBITMQ_HOST:5672// flower --concurrency=2 --auto_refresh=False --broker_api=http://guest:guest@$RABBITMQ_HOST:15672/api/  --url-prefix=$BASE_API_URL/workflow/flower --port=5566 &
  cd /var/app && celery --app workflow_app worker --loglevel=INFO -n "$WORKER_NAME" -Q "$QUEUES" --max-tasks-per-child=1 --prefetch-multiplier=1

else
  echo "Missing or unsupported value for INSTANCE_TYPE environment variable. Exiting."
  exit 1
fi

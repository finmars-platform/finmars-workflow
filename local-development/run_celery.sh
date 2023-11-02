#!/usr/bin/env bash
. ../venv/bin/activate
export DJANGO_SETTINGS_MODULE=workflow_app.settings
DB_NAME=workflow \
DB_USER=postgres \
DB_PASSWORD=postgres \
DB_HOST=localhost \
DB_PORT=5441 \
BASE_API_URL=space00000 \
AWS_STORAGE_BUCKET_NAME=finmars-client00000local \
AWS_S3_ACCESS_KEY_ID=AKIAZFI7MO4TROTNDZWN \
AWS_S3_SECRET_ACCESS_KEY=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 \
SECRET_KEY=mv83o5mq \
celery --app=workflow_app worker --autoscale=4,2  --loglevel=INFO -Q workflow -n workflow

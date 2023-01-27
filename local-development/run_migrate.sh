#!/usr/bin/env bash
. ../venv/bin/activate
DB_NAME=workflow \
DB_USER=postgres \
DB_PASSWORD=postgres \
DB_HOST=localhost \
DB_PORT=5441 \
AUTHORIZER_URL=http://127.0.0.1:8083/authorizer \
python manage.py migrate
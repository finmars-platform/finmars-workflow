#!/usr/bin/env bash
. ../venv/bin/activate
DB_NAME=workflow \
DB_USER=postgres \
DB_PASSWORD=postgres \
DB_HOST=localhost \
DB_PORT=5441 \
python manage.py migrate
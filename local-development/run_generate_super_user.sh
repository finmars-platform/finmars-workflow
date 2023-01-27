#!/usr/bin/env bash
. ../venv/bin/activate
DB_NAME=workflow \
DB_USER=postgres \
DB_PASSWORD=postgres \
DB_HOST=localhost \
DB_PORT=5441 \
ADMIN_USERNAME=workflow_admin \
ADMIN_PASSWORD=d798nf0rgpp6g8qp \
python manage.py generate_super_user
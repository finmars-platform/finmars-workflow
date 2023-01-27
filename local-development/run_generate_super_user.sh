#!/usr/bin/env bash
. ../venv/bin/activate
DB_NAME=workflow \
DB_USER=postgres \
DB_PASSWORD=postgres \
DB_HOST=localhost \
DB_PORT=5441 \
ADMIN_USERNAME=workflow_admin \
ADMIN_PASSWORD=d798nf0rgpp6g8qp \
AWS_STORAGE_BUCKET_NAME=finmars-client00000local \
AWS_S3_ACCESS_KEY_ID=AKIAZFI7MO4TROTNDZWN \
AWS_S3_SECRET_ACCESS_KEY=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 \
python manage.py generate_super_user
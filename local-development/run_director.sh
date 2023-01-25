#!/usr/bin/env bash
export DJANGO_SETTINGS_MODULE=director.settings
AWS_STORAGE_BUCKET_NAME=finmars-client00000local \
AWS_S3_ACCESS_KEY_ID=AKIAZFI7MO4TROTNDZWN \
AWS_S3_SECRET_ACCESS_KEY=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 \
DIRECTOR_DATABASE_URI="sqlite:////Users/szhitenev/projects/finmars/repositories/workflow/app-data/director.db" \
python director.py webserver

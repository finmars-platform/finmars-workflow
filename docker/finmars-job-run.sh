#!/bin/sh

echo "Migrating"
python /var/app/manage.py migrate_all_schemes

# echo "Sync remote storage to local storage"
# python /var/app/manage.py sync_remote_storage_to_local_storage_all_spaces

echo "Build documentation"
cd /var/app/docs && mkdocs build --site-dir ../workflow/static/documentation

echo "Copy js/css files"
cd /var/app && python /var/app/manage.py copy_css_libs
cd /var/app && python /var/app/manage.py copy_js_libs

echo "Collect static"
python /var/app/manage.py collectstatic -c --noinput


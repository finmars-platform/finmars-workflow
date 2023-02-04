Run server

`python director.py webserver`

Run Migrations

`python director.py db upgrade`

Run celery

`python director.py celery worker`

How to build documentation

`mkdocs build --site-dir ../workflow/static/documentation`

Documentation serve

`mkdocs serve -a 0.0.0.0:8001`
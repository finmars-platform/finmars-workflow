
Create Virtual Environment (VENV)

`python3.9 -m venv venv`

Activate VENV

`source venv/bin/activate`

Install Dependencies

 `pip install -r requirements.txt`

`npm i`

Create file for logs

`mkdir -p /var/log/finmars/workflow`

`chmod 777 /var/log/finmars/workflow`

`touch /var/log/finmars/workflow/django.log`

`chmod 777 /var/log/finmars/workflow/django.log`

Start Postgres Database and Redis in docker

`docker-compose -f docker-compose-dev.yml up`

**Activate VENV**

`./local-development/run_migrate.sh`

Start Celery Server

`./local-development/run_celery.sh`

Run scripts

`./local-development/run_copy_js_libs.sh`

`./local-development/run_copy_css_libs.sh`

Start Django Server

`./local-development/run_server.sh`


Attention!

The frontend must be deployed locally (vue-portal & portal) and they must have host 0.0.0.0

FROM python:3.10-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends \
    vim htop wget supervisor nfs-common npm && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /var/app

RUN mkdir -p \
    /var/app/app-data/import/configs/ \
    /var/app/app-data/import/files/ \
    /var/app/finmars_data \
    /var/app/app-data/media/ \
    /var/log/finmars/workflow/ \
    /var/log/celery/ && \
    chmod 777 /var/app/finmars_data

COPY package.json .
RUN npm install

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY finmars_standardized_errors ./finmars_standardized_errors
COPY healthcheck ./healthcheck
COPY logstash ./logstash
COPY workflow_app ./workflow_app
COPY workflow ./workflow
COPY manage.py ./

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

EXPOSE 8080

CMD ["gunicorn", "workflow_app.wsgi", "--config", "workflow_app/gunicorn.py"]

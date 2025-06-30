FROM python:3.13.5-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpq-dev \
    libssl-dev \
    npm \
    # (and cargo rustc if you see a Rust error) \
    && rm -rf /var/lib/apt/lists/*

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
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY docs ./docs
COPY finmars_standardized_errors ./finmars_standardized_errors
COPY healthcheck ./healthcheck
COPY logstash ./logstash
COPY node_modules ./node_modules
COPY workflow_app ./workflow_app
COPY workflow ./workflow
COPY manage.py ./

RUN mkdir ./workflow/static/documentation
RUN mkdocs build --config-file docs/mkdocs.yml --site-dir /var/app/workflow/static/documentation

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

EXPOSE 8080

# Node and npm use a non-root user provided by the base Node image
# Creating a new user "finmars" for running the application
RUN adduser \
    --disabled-password \
    --gecos "" \
    finmars


# Change to non-root privilege
USER finmars

EXPOSE 8080

CMD ["gunicorn", "workflow_app.wsgi", "--config", "workflow_app/gunicorn.py"]

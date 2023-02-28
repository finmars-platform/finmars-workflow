FROM python:3.10-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends \
    vim htop wget \
    supervisor nfs-common

RUN rm -rf /var/app
COPY requirements.txt /var/app/requirements.txt
RUN pip install -r /var/app/requirements.txt

COPY docker/finmars-run.sh /var/app/docker/finmars-run.sh
#COPY data/ /var/app/data/
COPY workflow/ /var/app/workflow/
COPY workflow_app/ /var/app/workflow_app/
COPY docs/ /var/app/docs/
COPY healthcheck/ /var/app/healthcheck/
COPY finmars_standardized_errors/ /var/app/finmars_standardized_errors/
COPY logstash/ /var/app/logstash/
COPY manage.py /var/app/manage.py

RUN mkdir -p /var/app/app-data/
RUN mkdir -p /var/app/app-data/media/
RUN mkdir -p /var/app/app-data/import/configs/
RUN mkdir -p /var/app/app-data/import/files/
RUN mkdir -p /var/log/finmars
RUN mkdir -p /var/log/finmars/workflow/
#RUN chown -R www-data:www-data /var/log/finmars/
#RUN chown -R www-data:www-data /var/app
#RUN chown -R www-data:www-data /var/app-data

COPY docker/supervisor/celery.conf /etc/supervisor/conf.d/celery.conf
COPY docker/supervisor/celerybeat.conf /etc/supervisor/conf.d/celerybeat.conf

COPY docker/uwsgi-www.ini /etc/uwsgi/apps-enabled/workflow.ini


RUN chmod +x /var/app/docker/finmars-run.sh

# create celery user
RUN mkdir -p /var/log/celery/
#RUN useradd -N -M --system -s /bin/bash celery  && \
## celery perms
#    groupadd grp_celery && usermod -a -G grp_celery celery && mkdir -p /var/run/celery/ /var/log/celery/  && \
#    chown -R celery:grp_celery /var/run/celery/ /var/log/celery/

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

EXPOSE 8080

CMD ["/bin/bash", "/var/app/docker/finmars-run.sh"]
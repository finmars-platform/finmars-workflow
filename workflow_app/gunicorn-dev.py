"""Gunicorn *development* config file"""

# The granularity of Error log outputs
loglevel = "info"
# The number of worker processes for handling requests
workers = 4
threads = 4
# The socket to bind
bind = "0.0.0.0:8084"
# Restart workers when code changes (development only!)
reload = True
# PID file so you can easily fetch process ID
# pidfile = "/var/run/gunicorn/dev.pid"
# Daemonize the Gunicorn process (detach & enter background)
# daemon = True
# accesslog = "/var/log/finmars/workflow/gunicorn.access.log"
# errorlog = "/var/log/finmars/workflow/gunicorn.error.log"

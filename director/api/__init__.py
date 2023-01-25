from flask import jsonify, Blueprint
from flask_json_schema import JsonValidationError
import pexpect

from director.utils import validate, format_schema_errors
from director.auth import auth

# Main application
api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.errorhandler(JsonValidationError)
def schema_exception_handler(e):
    return jsonify(format_schema_errors(e)), 400


@api_bp.route("/ping")
def ping():
    return jsonify({"message": "pong"})


@api_bp.route("/refresh-storage")
@auth.login_required
def refresh_storage():

    from director import cel_workflows

    cel_workflows.init_app()

    try:
        pexpect.spawn("supervisorctl start celery", timeout=240)
        pexpect.spawn("supervisorctl start celerybeat", timeout=240)
    except Exception as e:
        print("Could not restart celery")

    return jsonify({'status': 'ok'})
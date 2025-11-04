import logging

from django.conf import settings
from django.db import connection

from workflow.utils import schema_exists

logger = logging.getLogger(__name__)


# Very Important Middleware
# It sets the PostgreSQL search path to the tenant's schema
# Do not modify this code
# 2024-03-24 szhitenev
class RealmAndSpaceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Example URL pattern: /realm0abcd/space0xyzv/

        request.realm_code = None
        request.space_code = None

        path_parts = request.path_info.split("/")

        if "realm" in path_parts[1]:
            request.realm_code = path_parts[1]
            request.space_code = path_parts[2]

            if not schema_exists(request.space_code):
                # Uncomment in 1.9.0 when there is no more legacy Spaces
                # Handle the error (e.g., log it, return a 400 Bad Request, etc.)
                # For demonstration, returning a simple HttpResponseBadRequest
                # return HttpResponseBadRequest("Invalid space code.")

                with connection.cursor() as cursor:
                    cursor.execute("SET search_path TO public;")

            else:
                # Setting the PostgreSQL search path to the tenant's schema
                with connection.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {request.space_code};")

        else:
            # If we do not have realm_code, we suppose its legacy Space which do not need scheme changing
            request.space_code = path_parts[1]

            # Remain in public scheme
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO public;")

        response = self.get_response(request)

        if not response.streaming and "/admin/" in request.path_info:
            response.content = response.content.replace(b"spacexxxxx", request.space_code.encode())
            if "location" in response:
                response["location"] = response["location"].replace("spacexxxxx", request.space_code)

        # Optionally, reset the search path to default after the request is processed
        # This can be important in preventing "leakage" of the schema setting across requests
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO public;")

        return response


class SentryContextMiddleware:
    """
    Middleware that adds realm_code, space_code and domain to Sentry scope.
    Must be placed after RealmAndSpaceMiddleware in MIDDLEWARE list.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set Sentry context from request attributes
        # These attributes are set by RealmAndSpaceMiddleware
        try:
            import sentry_sdk

            with sentry_sdk.configure_scope() as scope:
                # Add realm_code
                realm_code = getattr(request, "realm_code", None)
                if realm_code:
                    scope.set_tag("realm_code", realm_code)
                    scope.set_context("realm", {"code": realm_code})

                # Add space_code
                space_code = getattr(request, "space_code", None)
                if space_code:
                    scope.set_tag("space_code", space_code)
                    scope.set_context("space", {"code": space_code})

                # Add domain
                domain = settings.DOMAIN_NAME
                if domain:
                    scope.set_tag("domain", domain)
                    scope.set_context("domain", {"name": domain})

        except Exception as e:
            logger.debug(f"Failed to set Sentry context: {e}")

        response = self.get_response(request)
        return response

from django.db import connection

def schema_exists(schema_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = %s;
        """, [schema_name])
        return cursor.fetchone() is not None

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

        path_parts = request.path_info.split('/')

        if 'realm' in path_parts[1]:

            request.realm_code = path_parts[1]
            request.space_code = path_parts[2]

            if not schema_exists(request.space_code):

                # Uncomment in 1.9.0 when there is no more legacy Spaces
                # Handle the error (e.g., log it, return a 400 Bad Request, etc.)
                # For demonstration, returning a simple HttpResponseBadRequest
                # return HttpResponseBadRequest("Invalid space code.")

                with connection.cursor() as cursor:
                    cursor.execute(f"SET search_path TO public;")

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

        # Optionally, reset the search path to default after the request is processed
        # This can be important in preventing "leakage" of the schema setting across requests
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO public;")

        return response
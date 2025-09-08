from django.conf import settings
from django.shortcuts import render
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view


class TenantSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        swagger = super().get_schema(request, public)

        # Iterate over paths and replace placeholder parameters with default values
        for path in list(swagger.paths.keys()):  # noqa: F402
            new_path = path.replace("{realm_code}", request.realm_code).replace("{space_code}", request.space_code)
            swagger.paths[new_path] = swagger.paths[path]
            del swagger.paths[path]

        return swagger

    def get_tags(self, operation_keys=None):
        tags = super().get_tags(operation_keys)

        print(f"tags {tags}")
        # Custom logic to modify tags if necessary
        return tags


def scheme_get_method_decorator(func):
    def wrapper(self, request, version="", format=None, *args, **kwargs):
        return func(self, request, version="", format=None)

    return wrapper


def generate_schema(local_urlpatterns):
    schema_view = get_schema_view(
        openapi.Info(
            title="Finmars Workflow API",
            default_version="v1",
            description="Finmars Documentation",
            terms_of_service="https://www.finmars.com/policies/terms/",
            contact=openapi.Contact(email="admin@finmars.com"),
            license=openapi.License(name="BSD License"),
            x_logo={
                "url": "https://finmars.com/wp-content/uploads/2023/04/logo.png",
                "backgroundColor": "#000",
                "href": "/" + settings.REALM_CODE + "/docs/api/v1/",
            },
        ),
        patterns=local_urlpatterns,
        public=True,
        # permission_classes=[permissions.AllowAny],
        generator_class=TenantSchemaGenerator,
    )

    schema_view.get = scheme_get_method_decorator(schema_view.get)

    return schema_view


def get_api_documentation(*args, **kwargs):
    from .urls import router

    local_urlpatterns = [
        path("<slug:realm_code>/<slug:space_code>/workflow/api/", include(router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def render_main_page(request, *args, **kwargs):
    context = {"realm_code": request.realm_code, "space_code": request.space_code}

    return render(request, "finmars_redoc.html", context)


def get_redoc_urlpatterns():
    api_schema_view = get_api_documentation()

    urlpatterns = [
        path("<slug:realm_code>/<slug:space_code>/workflow/docs/", render_main_page, name="main"),
        path(
            "<slug:realm_code>/<slug:space_code>/workflow/docs/api/",
            api_schema_view.with_ui("redoc", cache_timeout=0),
            name="api",
        ),
    ]

    return urlpatterns

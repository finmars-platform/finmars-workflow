"""app URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import re_path, include
from django.views.generic import TemplateView
from rest_framework import routers
from django.conf import settings
from workflow_app.openapi import get_redoc_urlpatterns

from workflow.views import (
    WorkflowViewSet,
    TaskViewSet,
    PingViewSet,
    DefinitionViewSet,
    RefreshStorageViewSet,
    LogFileViewSet,
    CodeExecutionViewSet,
    RealmMigrateSchemeView,
    FileExecutionViewSet,
    ScheduleViewSet,
)

router = routers.DefaultRouter()

router.register(r"workflow", WorkflowViewSet, "workflow")
router.register(r"task", TaskViewSet, "task")
router.register(r"ping", PingViewSet, "ping")
router.register(r"refresh-storage", RefreshStorageViewSet, "refresh-storage")
router.register(r"definition", DefinitionViewSet, "ping")
router.register(r"schedule", ScheduleViewSet, "schedule")
router.register(r"log", LogFileViewSet, "log")
router.register(r"execute-code", CodeExecutionViewSet, basename="execute-code")
router.register(r"execute-file", FileExecutionViewSet, basename="execute-file")
router.register(r"authorizer/migrate", RealmMigrateSchemeView, "migrate")

urlpatterns = [
    # Old Approach (delete in 1.9.0)
    re_path(r"^(?P<space_code>[^/]+)/workflow/api/", include(router.urls)),
    # re_path(r'^(?P<space_code>[^/]+)/workflow/admin/docs/', include('django.contrib.admindocs.urls')),
    # re_path(r'^(?P<space_code>[^/]+)/workflow/admin/', admin.site.urls),
    re_path(
        r"^(?P<space_code>[^/]+)/workflow/$",
        TemplateView.as_view(template_name="index.html"),
    ),
    # New Approach
    re_path(
        r"^(?P<realm_code>[^/]+)/(?P<space_code>[^/]+)/workflow/api/",
        include(router.urls),
    ),
    # re_path(r'^(?P<realm_code>[^/]+)/(?P<space_code>[^/]+)/workflow/admin/docs/',
    #        include('django.contrib.admindocs.urls')),
    re_path(
        rf"^{settings.REALM_CODE}/(?:space\w{{5}})/workflow/admin/", admin.site.urls
    ),
    re_path(
        r"^(?P<realm_code>[^/]+)/(?P<space_code>[^/]+)/workflow/$",
        TemplateView.as_view(template_name="index.html"),
    ),
]

if "drf_yasg" in settings.INSTALLED_APPS:
    urlpatterns = urlpatterns + get_redoc_urlpatterns()

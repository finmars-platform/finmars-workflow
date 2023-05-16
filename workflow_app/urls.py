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

from workflow.views import WorkflowViewSet, TaskViewSet, PingViewSet, DefinitionViewSet, RefreshStorageViewSet, \
    LogFileViewSet
from workflow_app import settings

router = routers.DefaultRouter()

router.register(r'workflow', WorkflowViewSet, 'workflow')
router.register(r'task', TaskViewSet, "task")
router.register(r'ping', PingViewSet, "ping")
router.register(r'refresh-storage', RefreshStorageViewSet, "refresh-storage")
router.register(r'definition', DefinitionViewSet, "ping")
router.register(r'log', LogFileViewSet, "log")

urlpatterns = [

    re_path(r'^' + settings.BASE_API_URL + '/workflow/api/', include(router.urls)),
    re_path(r'^' + settings.BASE_API_URL + '/workflow/admin/docs/', include('django.contrib.admindocs.urls')),
    re_path(r'^' + settings.BASE_API_URL + '/workflow/admin/', admin.site.urls),

    re_path(r'^' + settings.BASE_API_URL + '/workflow/$', TemplateView.as_view(template_name='index.html'))

]

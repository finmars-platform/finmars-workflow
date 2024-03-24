from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from workflow.models import User, Task, Workflow, Space
from workflow_app import settings

admin.site.site_header = 'Workflow Admin'
admin.site.site_title = 'Workflow Admin'


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['id', 'username', 'email']
    search_fields = ['id', 'username', 'email']

    fieldsets = UserAdmin.fieldsets + (
        ('Extra Fields', {'fields': ('two_factor_verification', 'is_verified', 'json_data')}),
    )

    actions_on_bottom = True


admin.site.register(User, CustomUserAdmin)


class SpaceAdmin(admin.ModelAdmin):
    model = Space
    list_display = ['id', 'name', 'realm_code', 'space_code']
    search_fields = ['id', 'name', 'realm_code', 'space_code']

    actions_on_bottom = True


admin.site.register(Space, SpaceAdmin)


class TaskAdmin(admin.ModelAdmin):
    model = Task
    list_display = ['id', 'workflow', 'celery_task_id', 'verbose_name']
    search_fields = ['id', 'workflow', 'celery_task_id', 'verbose_name']

    actions_on_bottom = True


admin.site.register(Task, TaskAdmin)


class WorkflowAdmin(admin.ModelAdmin):
    model = Workflow
    list_display = ['id', 'name', 'user_code', 'status']
    search_fields = ['id', 'name', 'user_code', 'status']

    actions_on_bottom = True


admin.site.register(Workflow, WorkflowAdmin)
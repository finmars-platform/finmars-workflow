from django.db import migrations


def create_crontab_task(apps, schema_editor):
    CrontabSchedule = apps.get_model('django_celery_beat', 'CrontabSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    # Run every day at 12:30 AM
    schedule, created = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='5',
        day_of_week='*',
        day_of_month='*',
        month_of_year='*',
    )

    PeriodicTask.objects.update_or_create(
        name='Call backend historical records everyday',
        defaults={
            'crontab': schedule,
            'task': 'workflow.tasks.export_backend_historical_records.call_export_backend_historical_records',
        }
    )

def remove_crontab_task(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(name='Call backend historical records everyday').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0021_alter_workflowtemplate_options_and_more'),
        ('django_celery_beat', '0018_improve_crontab_helptext'),

    ]

    operations = [
        migrations.RunPython(create_crontab_task, reverse_code=remove_crontab_task),
    ]

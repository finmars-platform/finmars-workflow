from django.db import migrations, models


def remove_duplicates(apps, schema_editor):
    WorkflowTemplate = apps.get_model("workflow", "WorkflowTemplate")

    duplicates = (
        WorkflowTemplate.objects
        .values('user_code', 'space_id')  # Group by unique-together fields
        .annotate(count=models.Count('id'))  # Count duplicates
        .filter(count__gt=1)  # Find only groups with duplicates
    )

    for duplicate in duplicates:
        user_code = duplicate['user_code']
        space_id = duplicate['space_id']
        
        rows = (
            WorkflowTemplate.objects.filter(user_code=user_code, space_id=space_id)
            .order_by('-created_at')
        )
        for row in rows[1:]:
            row.delete() 


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0019_alter_task_status'),
    ]

    operations = [
        migrations.RunPython(remove_duplicates),
    ]

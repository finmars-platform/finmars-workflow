# Generated by Django 4.0.6 on 2024-10-07 10:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0007_workflowtemplate'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflow',
            name='workflow_template',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='workflows', to='workflow.workflowtemplate', verbose_name='template'),
        ),
    ]

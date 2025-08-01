# Generated by Django 4.0.6 on 2024-10-07 11:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0009_workflow_node_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='node_id',
            field=models.CharField(blank=True, help_text='Node ID from the workflow JSON structure', max_length=255, null=True),
        ),
    ]

# Generated by Django 4.0.3 on 2023-07-07 07:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('support', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tickect',
            name='raised_by',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AlterField(
            model_name='tickect',
            name='resolved_by',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
    ]

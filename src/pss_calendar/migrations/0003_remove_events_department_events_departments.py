# Generated by Django 4.0.3 on 2023-08-07 02:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company_profile', '0003_alter_designations_sub_department'),
        ('pss_calendar', '0002_events_visibility'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='events',
            name='department',
        ),
        migrations.AddField(
            model_name='events',
            name='departments',
            field=models.ManyToManyField(default=[], related_name='event_departments', to='company_profile.departments'),
        ),
    ]

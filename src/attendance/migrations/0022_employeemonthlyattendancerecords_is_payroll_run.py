# Generated by Django 4.0.3 on 2023-09-19 11:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0021_attendancerulesettings_calendar_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeemonthlyattendancerecords',
            name='is_payroll_run',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]

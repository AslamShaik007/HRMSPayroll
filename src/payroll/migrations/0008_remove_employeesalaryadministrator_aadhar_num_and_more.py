# Generated by Django 4.0.3 on 2023-07-07 11:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0007_activitylog_updated_employee'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employeesalaryadministrator',
            name='aadhar_num',
        ),
        migrations.RemoveField(
            model_name='employeesalaryadministrator',
            name='pan_num',
        ),
    ]

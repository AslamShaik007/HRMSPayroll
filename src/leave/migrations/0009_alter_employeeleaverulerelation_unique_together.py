# Generated by Django 4.0.3 on 2023-09-19 04:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0013_employeedocuments_document_description_and_more'),
        ('leave', '0008_leaverulesettings_session_year'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='employeeleaverulerelation',
            unique_together={('employee', 'leave_rule', 'is_deleted', 'session_year')},
        ),
    ]

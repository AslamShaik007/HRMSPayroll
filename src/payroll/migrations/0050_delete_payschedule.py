# Generated by Django 4.0.3 on 2023-11-10 10:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0049_delete_activitylog'),
    ]

    operations = [
        migrations.DeleteModel(
            name='PaySchedule',
        ),
    ]

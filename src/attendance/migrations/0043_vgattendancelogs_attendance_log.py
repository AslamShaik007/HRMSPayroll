# Generated by Django 4.2 on 2024-02-05 14:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0042_employeecheckinoutdetails_checkin_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='vgattendancelogs',
            name='attendance_log',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
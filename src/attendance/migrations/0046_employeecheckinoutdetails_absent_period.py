# Generated by Django 4.0.3 on 2024-04-15 13:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0045_employeemonthlyattendancerecords_is_cron_run'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeecheckinoutdetails',
            name='absent_period',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]
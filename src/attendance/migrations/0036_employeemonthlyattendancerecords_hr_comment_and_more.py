# Generated by Django 4.0.3 on 2023-12-12 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0035_keyloggerattendancelogs_break_end_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeemonthlyattendancerecords',
            name='hr_comment',
            field=models.TextField(blank=True, default='', null=True),
        ),
        migrations.AddField(
            model_name='employeemonthlyattendancerecords',
            name='manager_comment',
            field=models.TextField(blank=True, default='', null=True),
        ),
    ]

# Generated by Django 4.2 on 2023-11-27 06:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0034_keyloggerattendancelogs_system_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='keyloggerattendancelogs',
            name='break_end',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='keyloggerattendancelogs',
            name='break_start',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

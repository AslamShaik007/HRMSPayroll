# Generated by Django 4.2 on 2024-01-09 12:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0040_alter_keyloggerattendancelogs_system_location'),
    ]

    operations = [
        migrations.AlterField(
            model_name='keyloggerattendancelogs',
            name='break_cause',
            field=models.TextField(blank=True, null=True),
        ),
    ]

# Generated by Django 4.2 on 2024-02-25 09:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0035_employeereportingmanager_is_multitenant_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeereportingmanager',
            name='multitenant_manager_email',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]
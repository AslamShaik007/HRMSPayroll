# Generated by Django 4.2 on 2024-02-15 09:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('HRMSApp', '0022_merge_20240203_1024'),
    ]

    operations = [
        migrations.AddField(
            model_name='companycustomizedconfigurations',
            name='max_days_to_utilize_compoff',
            field=models.IntegerField(blank=True, default=60, null=True),
        ),
        migrations.AddField(
            model_name='companycustomizedconfigurations',
            name='max_days_to_utilize_compoff_description',
            field=models.TextField(blank=True, null=True),
        ),
    ]
# Generated by Django 4.2 on 2024-03-08 07:06

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('HRMSApp', '0027_companydetails_company_uid'),
    ]

    operations = [
        migrations.AddField(
            model_name='companydetails',
            name='child_company_uids',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), blank=True, null=True, size=None),
        ),
    ]

# Generated by Django 4.0.3 on 2023-09-12 05:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('HRMSApp', '0009_companydetails_is_brand_name_updated'),
    ]

    operations = [
        migrations.AlterField(
            model_name='companydetails',
            name='is_brand_name_updated',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
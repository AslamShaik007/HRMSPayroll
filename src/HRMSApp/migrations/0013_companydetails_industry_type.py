# Generated by Django 4.2 on 2023-11-27 10:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('HRMSApp', '0012_alter_roles_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='companydetails',
            name='industry_type',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]

# Generated by Django 4.0.3 on 2024-02-01 09:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0032_employeeexperiencedetails_company_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='is_rehire',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
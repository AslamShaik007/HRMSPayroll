# Generated by Django 4.0.3 on 2024-01-09 16:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('HRMSApp', '0015_alter_companydetails_industry_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='companydetails',
            name='payslip_hr_email',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='companydetails',
            name='payslip_hr_phone',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]

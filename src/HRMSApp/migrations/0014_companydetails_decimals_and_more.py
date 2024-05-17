# Generated by Django 4.2 on 2023-12-01 13:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('HRMSApp', '0013_companydetails_industry_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='companydetails',
            name='decimals',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='companydetails',
            name='payslip_signature',
            field=models.FileField(blank=True, null=True, upload_to='company_images/'),
        ),
        migrations.AddField(
            model_name='companydetails',
            name='round_offs',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='companydetails',
            name='signature_status',
            field=models.IntegerField(choices=[(1, 'Show'), (2, 'Hide')], default=2, help_text='1 will treated as Show. 2 will treate as Hide.'),
        ),
    ]

# Generated by Django 4.2 on 2024-03-01 09:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('HRMSApp', '0025_roles_is_multitenant_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='MultiTenantCompanies',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mul_key', models.CharField(max_length=256)),
                ('subdomain', models.CharField(max_length=256)),
                ('is_multitenant', models.BooleanField(default=False)),
                ('is_primary', models.BooleanField(default=False)),
                ('companyname', models.CharField(max_length=256)),
            ],
            options={
                'db_table': 'companies',
                'managed': False,
            },
        ),
        migrations.AddField(
            model_name='companydetails',
            name='company_id',
            field=models.CharField(blank=True, max_length=200, null=True, unique=True),
        ),
    ]
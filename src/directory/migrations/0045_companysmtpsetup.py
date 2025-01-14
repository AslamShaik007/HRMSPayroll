# Generated by Django 4.2 on 2024-04-24 06:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('HRMSApp', '0029_alter_companydetails_child_company_uids'),
        ('directory', '0044_employeeworkdocuments'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanySMTPSetup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_host', models.CharField(max_length=100)),
                ('email_port', models.IntegerField()),
                ('email_host_user', models.CharField(max_length=100)),
                ('email_host_password', models.CharField(max_length=100)),
                ('from_email', models.EmailField(max_length=254)),
                ('is_default', models.BooleanField(default=False)),
                ('company', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='company_smpt_setup', to='HRMSApp.companydetails')),
            ],
        ),
    ]

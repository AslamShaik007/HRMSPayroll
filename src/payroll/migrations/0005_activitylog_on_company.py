# Generated by Django 4.0.3 on 2023-06-30 11:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('HRMSApp', '0002_futuremodule_content_type'),
        ('payroll', '0004_alter_activitylog_on_datetime'),
    ]

    operations = [
        migrations.AddField(
            model_name='activitylog',
            name='on_company',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='HRMSApp.companydetails'),
        ),
    ]

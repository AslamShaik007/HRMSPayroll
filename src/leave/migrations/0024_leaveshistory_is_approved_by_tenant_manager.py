# Generated by Django 4.2 on 2024-03-05 17:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leave', '0023_leaveshistory_multitenant_manager_email_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaveshistory',
            name='is_approved_by_tenant_manager',
            field=models.BooleanField(default=False),
        ),
    ]

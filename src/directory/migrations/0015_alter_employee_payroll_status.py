# Generated by Django 4.0.3 on 2023-09-20 08:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0014_alter_employee_payroll_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='payroll_status',
            field=models.BooleanField(default=True),
        ),
    ]

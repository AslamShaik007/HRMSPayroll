# Generated by Django 4.0.3 on 2023-09-21 10:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0015_alter_employee_payroll_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeesalarydetails',
            name='fund_transfer_type',
            field=models.CharField(blank=True, choices=[('FT', 'FT'), ('NEFT', 'NEFT')], max_length=20, null=True),
        ),
    ]

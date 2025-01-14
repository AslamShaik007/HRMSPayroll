# Generated by Django 4.0.3 on 2023-10-30 08:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0046_alter_statestaxconfig_state'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employeetds',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='employeetds',
            name='employee_hec',
        ),
        migrations.RemoveField(
            model_name='employeetds',
            name='employee_regime',
        ),
        migrations.RemoveField(
            model_name='employeetds',
            name='employee_salary_details',
        ),
        migrations.RemoveField(
            model_name='employeetds',
            name='updated_by',
        ),
        migrations.AlterField(
            model_name='epfsetup',
            name='is_employer_contribution_in_ctc',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='esi',
            name='is_employer_contribution_in_ctc',
            field=models.BooleanField(default=True),
        ),
        migrations.DeleteModel(
            name='EmployeeSalaryInfo',
        ),
        migrations.DeleteModel(
            name='EmployeeTds',
        ),
    ]

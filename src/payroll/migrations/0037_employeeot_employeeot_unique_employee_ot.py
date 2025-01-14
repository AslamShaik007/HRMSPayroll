# Generated by Django 4.2 on 2023-10-04 09:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0021_alter_employeesalarydetails_options'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payroll', '0036_remove_employeelops_comp_offs_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmployeeOT',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('ot_month_year', models.DateField(db_index=True)),
                ('total_ot_count', models.FloatField(default=0)),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='emp_ot', to='directory.employee')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
        ),
        migrations.AddConstraint(
            model_name='employeeot',
            constraint=models.UniqueConstraint(fields=('employee', 'ot_month_year'), name='unique_employee_ot'),
        ),
    ]

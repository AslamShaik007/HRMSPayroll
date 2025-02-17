# Generated by Django 4.2 on 2024-03-05 16:17

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('directory', '0037_merge_20240302_1518'),
        ('payroll', '0059_alter_payslipfields_fields_list'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmployeePayrollOnHold',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('hold_created_at', models.DateField()),
                ('hold_updated_at', models.DateField()),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('employee', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='hold_employee', to='directory.employee')),
                ('hold_created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_hold_emp', to='directory.employee')),
                ('hold_updated_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='updated_hold_emp', to='directory.employee')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]

# Generated by Django 4.2 on 2023-11-15 05:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('directory', '0030_merge_20231113_1942'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmployeeExperienceDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('company_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='Company Name')),
                ('designation', models.CharField(blank=True, max_length=100, null=True, verbose_name='Previous Designation')),
                ('from_date', models.DateField(null=True, verbose_name='From Date')),
                ('to_date', models.DateField(null=True, verbose_name='To Date')),
                ('experience', models.DecimalField(blank=True, decimal_places=1, default=0, max_digits=3, null=True)),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='employee_experience', to='directory.employee')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Experienced Years',
                'verbose_name_plural': 'Experienced Years',
            },
        ),
    ]
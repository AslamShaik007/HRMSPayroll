# Generated by Django 4.0.3 on 2023-08-29 11:20

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('attendance', '0014_assignedattendancerules_session_year'),
    ]

    operations = [
        migrations.CreateModel(
            name='VgAttendanceLogs',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('employee_code', models.CharField(blank=True, max_length=100, null=True)),
                ('log_datetime', models.DateTimeField(blank=True, null=True)),
                ('log_date', models.DateTimeField(blank=True, null=True)),
                ('log_time', models.DateTimeField(blank=True, null=True)),
                ('direction', models.CharField(blank=True, choices=[('in', 'in'), ('out', 'out')], max_length=50, null=True)),
                ('work_code', models.CharField(blank=True, max_length=100, null=True)),
                ('device_short_name', models.CharField(blank=True, max_length=100, null=True)),
                ('serial_number', models.CharField(blank=True, max_length=100, null=True)),
                ('verification_mode', models.CharField(blank=True, max_length=100, null=True)),
                ('reserved_field_1', models.CharField(blank=True, max_length=100, null=True)),
                ('reserved_field_2', models.CharField(blank=True, max_length=100, null=True)),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
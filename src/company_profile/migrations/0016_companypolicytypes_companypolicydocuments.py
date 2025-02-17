# Generated by Django 4.0.3 on 2024-02-12 08:52

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('HRMSApp', '0022_merge_20240203_1024'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('company_profile', '0015_announcements_announcement_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyPolicyTypes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('policy_name', models.CharField(blank=True, max_length=32, null=True)),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Company Policy Types',
                'verbose_name_plural': 'Company Policy Types',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='CompanyPolicyDocuments',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('title', models.CharField(blank=True, max_length=40, null=True)),
                ('description', models.TextField(blank=True, max_length=1000, null=True)),
                ('visibility', models.CharField(choices=[('VISIBLE_TO_ALL', 'Visible To All'), ('LIMITED_VISIBILITY', 'Limited Visibility')], default='VISIBLE_TO_ALL', max_length=20)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('INACTIVE', 'InActive'), ('ARCHIVE', 'Archive')], default='InActive', max_length=20)),
                ('policy_file', models.FileField(blank=True, null=True, upload_to='policy_documents/')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='company_policy', to='HRMSApp.companydetails')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('policy_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='company_profile.companypolicytypes')),
                ('roles', models.ManyToManyField(default=[], related_name='company_policy_roles', to='HRMSApp.roles')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Company Policy Documents',
                'verbose_name_plural': 'Company Policy Documents',
                'ordering': ['created_at'],
            },
        ),
    ]

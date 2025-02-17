# Generated by Django 4.0.3 on 2023-06-22 09:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('HRMSApp', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BankAccountTypes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('account_type', models.PositiveSmallIntegerField(choices=[(10, 'Current Account'), (20, 'Savings Account'), (30, 'Salary Account'), (40, 'Fixed Deposit Account'), (50, 'Recurring Deposit Account'), (60, 'Non-Resident Indian Account'), (61, 'Non-Resident Ordinary Account'), (62, 'Non-Resident External Account'), (70, 'Foreign Currency Non-Resident Account')], verbose_name='Account Types')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Bank Account Type',
                'verbose_name_plural': 'Bank Account Types',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Departments',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('name', models.CharField(max_length=100)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='HRMSApp.companydetails')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Department',
                'verbose_name_plural': 'Departments',
                'unique_together': {('is_deleted', 'name', 'company')},
            },
        ),
        migrations.CreateModel(
            name='EntityTypes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('entity_type', models.PositiveSmallIntegerField(choices=[(10, 'Private Limited Company'), (20, 'Public Limited Company'), (30, 'Limited Liability Partnership'), (40, 'Partnership'), (50, 'Sole Proprietorship'), (60, 'Nonprofit Organisation'), (70, 'Society'), (80, 'Trust'), (90, 'Others')], verbose_name='Entity Types')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Entity Type',
                'verbose_name_plural': 'Entity Types',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StatutoryDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('tan_number', models.CharField(blank=True, default=None, max_length=100, null=True)),
                ('date_of_incorp', models.DateField(blank=True, max_length=100, null=True)),
                ('pan_number', models.CharField(blank=True, default=None, max_length=100, null=True)),
                ('pan_image_path', models.FileField(blank=True, default=None, null=True, upload_to='company_pan_images/')),
                ('cin_number', models.CharField(blank=True, default=None, max_length=100, null=True)),
                ('cin_image_path', models.FileField(blank=True, default=None, null=True, upload_to='corporate_identity_number_images/')),
                ('gst_number', models.CharField(blank=True, default=None, max_length=100, null=True)),
                ('gst_image_path', models.FileField(blank=True, default=None, null=True, upload_to='company_gst_images/')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='HRMSApp.companydetails')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('entity_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='company_profile.entitytypes')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'StatutoryDetail',
                'verbose_name_plural': 'Policies',
            },
        ),
        migrations.CreateModel(
            name='SecretaryDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('secretary_name', models.CharField(max_length=100)),
                ('secretary_email', models.CharField(max_length=100)),
                ('secretary_phone', models.CharField(max_length=100)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='HRMSApp.companydetails')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'SecretaryDetails',
                'verbose_name_plural': 'SecretaryDetails',
            },
        ),
        migrations.CreateModel(
            name='Policies',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('policy_title', models.CharField(max_length=100)),
                ('policy_description', models.CharField(max_length=100)),
                ('file_path', models.FileField(upload_to='company_policy_files/')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='HRMSApp.companydetails')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'policies',
                'verbose_name_plural': 'policies',
            },
        ),
        migrations.CreateModel(
            name='CustomAddressDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('address_title', models.CharField(help_text='Type of Address', max_length=20)),
                ('address_line1', models.CharField(max_length=100)),
                ('address_line2', models.CharField(max_length=100)),
                ('country', models.CharField(max_length=100, null=True)),
                ('state', models.CharField(max_length=100, null=True)),
                ('city', models.CharField(max_length=50)),
                ('pincode', models.CharField(max_length=10)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='HRMSApp.companydetails')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CompanyDirectorDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('director_name', models.CharField(max_length=100)),
                ('director_mail_id', models.CharField(max_length=100)),
                ('din_number', models.CharField(max_length=100)),
                ('director_phone', models.CharField(max_length=100)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='HRMSApp.companydetails')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'DirectorDetails',
                'verbose_name_plural': 'DirectorDetails',
            },
        ),
        migrations.CreateModel(
            name='BankDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('account_title', models.CharField(max_length=200)),
                ('bank_name', models.CharField(max_length=100)),
                ('city', models.CharField(max_length=50)),
                ('branch_name', models.CharField(max_length=100)),
                ('ifsc_code', models.CharField(max_length=50)),
                ('account_number', models.CharField(max_length=50, unique=True)),
                ('bic', models.CharField(blank=True, help_text='Required, Max of 100 Characters', max_length=50, verbose_name='BIC/SWIFT')),
                ('is_default', models.BooleanField(default=True, help_text='Mark it if its the default Bank Account.', verbose_name='Is Default')),
                ('account_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='company_profile.bankaccounttypes')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='HRMSApp.companydetails')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'BankDetails',
                'verbose_name_plural': 'BankDetails',
            },
        ),
        migrations.CreateModel(
            name='AuditorTypes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('auditor_type', models.PositiveSmallIntegerField(choices=[(10, 'Internal'), (20, 'Statutory')], verbose_name='Auditor Types')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Auditor Type',
                'verbose_name_plural': 'Auditor Types',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AuditorDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('auditor_name', models.CharField(max_length=100)),
                ('auditor_email', models.CharField(max_length=100)),
                ('auditor_phone', models.CharField(max_length=100)),
                ('auditor_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='company_profile.auditortypes')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='HRMSApp.companydetails')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'AuditorDetails',
                'verbose_name_plural': 'AuditorDetails',
            },
        ),
        migrations.CreateModel(
            name='Announcements',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('annoucement', models.CharField(max_length=500)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='HRMSApp.companydetails')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Announcement',
                'verbose_name_plural': 'Announcements',
            },
        ),
        migrations.CreateModel(
            name='SubDepartments',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sub_departments', to='company_profile.departments')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Sub Departments',
                'verbose_name_plural': 'Sub Departments',
                'unique_together': {('name', 'department', 'is_deleted')},
            },
        ),
        migrations.CreateModel(
            name='Designations',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('name', models.CharField(max_length=100)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='HRMSApp.companydetails')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'unique_together': {('company', 'name', 'is_deleted')},
            },
        ),
        migrations.CreateModel(
            name='CompanyGrades',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('grade', models.CharField(max_length=100)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='HRMSApp.companydetails')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Grade',
                'verbose_name_plural': 'Grades',
                'unique_together': {('company', 'grade', 'is_deleted')},
            },
        ),
    ]

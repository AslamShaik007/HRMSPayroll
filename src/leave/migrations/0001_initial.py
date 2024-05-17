# Generated by Django 4.0.3 on 2023-06-22 09:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('directory', '0001_initial'),
        ('HRMSApp', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LeaveRules',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('name', models.CharField(max_length=100, verbose_name='Leave Type')),
                ('description', models.TextField(blank=True, default='This is a default description for the Leave Type. You can customise this.', help_text='Enter description', verbose_name='Leave Description')),
                ('leaves_allowed_in_year', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='Leaves Allowed in a Year')),
                ('weekends_between_leave', models.BooleanField(default=False, verbose_name='Weekends Between Leave')),
                ('holidays_between_leave', models.BooleanField(default=False, verbose_name='Holidays Between Leave')),
                ('creditable_on_accrual_basis', models.BooleanField(default=False, verbose_name='Creditable On Accrual Basis')),
                ('accrual_frequency', models.CharField(blank=True, choices=[('MONTHLY', 'Monthly'), ('QUARTERLY', 'Quarterly'), ('HALF_YEARLY', 'Half Yearly')], help_text='leaves credited in employee buccket by monthly, quarterly,halfyearly', max_length=20, null=True, verbose_name='Accrual Frequency')),
                ('accruel_period', models.CharField(blank=True, help_text='credit leaves end of the month or month start', max_length=10, null=True, verbose_name='Accrual Period')),
                ('allowed_under_probation', models.BooleanField(default=False, verbose_name='Allowed Under Probation')),
                ('allowed_negative_rules', models.BooleanField(default=False, verbose_name='Allowed Negative Leaves')),
                ('carry_forward_enabled', models.BooleanField(default=False, verbose_name='Carry Forward Enabled')),
                ('all_remaining_leaves', models.BooleanField(default=False, help_text='Flag to carry forward all remaining leaves', verbose_name='All Remaining Leaves')),
                ('max_leaves_to_carryforward', models.IntegerField(default=0, verbose_name='Max Leaves To Carry Forward')),
                ('continuous_leaves_allowed', models.IntegerField(default=0, verbose_name='Allowed Continuous Leaves')),
                ('max_leaves_allowed_in_month', models.IntegerField(blank=True, default=4, null=True, verbose_name='Max Allowed Leaves Per Month')),
                ('allow_backdated_leaves', models.BooleanField(default=False, verbose_name='Backdated Leaves allowed')),
                ('company', models.ForeignKey(help_text='Select Company Primary Key To Post Work Week Rules According To Company Wise', on_delete=django.db.models.deletion.CASCADE, to='HRMSApp.companydetails', verbose_name='Company')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Leave Rules',
                'verbose_name_plural': 'Leave Rules',
            },
        ),
        migrations.CreateModel(
            name='WorkRules',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('name', models.CharField(help_text='Enter Work Rule Maximum Length of 100', max_length=100, verbose_name='Rule Name')),
                ('description', models.CharField(blank=True, default='Custom Rule created', help_text=' Enter Description Maximum Length of 100', max_length=100, null=True, verbose_name='Rule Description')),
                ('is_default', models.BooleanField(default=False)),
                ('company', models.ForeignKey(help_text='Select Company Primary Key To Post Work Week Rules According To Company Wise', on_delete=django.db.models.deletion.CASCADE, to='HRMSApp.companydetails', verbose_name='Company Id')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'WorkRule',
                'verbose_name_plural': 'Work Rules',
                'ordering': ['-created_at'],
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='LeavesHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('start_date', models.DateField(verbose_name='Start Date')),
                ('start_day_session', models.CharField(blank=True, choices=[('FIRST_HALF', 'First Half'), ('SECOND_HALF', 'Second Half')], help_text='It indicates the employee taken full_day or half_day leave', max_length=20, null=True, verbose_name='Select Half')),
                ('end_date', models.DateField(verbose_name='End Date')),
                ('end_day_session', models.CharField(blank=True, choices=[('FIRST_HALF', 'First Half'), ('SECOND_HALF', 'Second Half')], help_text='It indicates the employee taken full_day or half_day leave', max_length=20, null=True, verbose_name='Select Half')),
                ('reason', models.CharField(help_text='Write Your Reason here for taking leave', max_length=500, verbose_name='Write your Reason')),
                ('reason_for_rejection', models.CharField(blank=True, help_text='Write Your Reason here for taking leave', max_length=500, null=True, verbose_name='Write your Reason')),
                ('attachment', models.FileField(blank=True, help_text='upload file for proof', null=True, upload_to='leave attachments/')),
                ('status', models.PositiveSmallIntegerField(choices=[(10, 'Approved'), (20, 'Pending'), (30, 'Cancelled'), (40, 'Rejected'), (50, 'Revoke')], help_text='It indicates the leave status', verbose_name='Leave Status')),
                ('extra_data', models.JSONField(blank=True, default=dict, help_text='Used to store additional information in the JSON format', null=True, verbose_name='Additional Info')),
                ('no_of_leaves_applied', models.DecimalField(decimal_places=1, default=0, help_text='Count of applied leaves', max_digits=2, verbose_name='No Of Leaves')),
                ('approved_on', models.DateTimeField(blank=True, null=True, verbose_name='Approved On')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='approved_by', to='directory.employee', verbose_name='Leave Approved By')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='directory.employee')),
                ('leave_rule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='leave.leaverules')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Leaves History',
                'verbose_name_plural': 'Leaves History',
            },
        ),
        migrations.CreateModel(
            name='WorkRuleChoices',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('monday', models.PositiveSmallIntegerField(choices=[(2, 'Full Day'), (1, 'Half Day'), (0, 'Week Off')], default=2, verbose_name='Monday')),
                ('tuesday', models.PositiveSmallIntegerField(choices=[(2, 'Full Day'), (1, 'Half Day'), (0, 'Week Off')], default=2, verbose_name='Tuesday')),
                ('wednesday', models.PositiveSmallIntegerField(choices=[(2, 'Full Day'), (1, 'Half Day'), (0, 'Week Off')], default=2, verbose_name='Wednesday')),
                ('thursday', models.PositiveSmallIntegerField(choices=[(2, 'Full Day'), (1, 'Half Day'), (0, 'Week Off')], default=2, verbose_name='Thursday')),
                ('friday', models.PositiveSmallIntegerField(choices=[(2, 'Full Day'), (1, 'Half Day'), (0, 'Week Off')], default=2, verbose_name='Friday')),
                ('saturday', models.PositiveSmallIntegerField(choices=[(2, 'Full Day'), (1, 'Half Day'), (0, 'Week Off')], default=2, verbose_name='Saturday')),
                ('sunday', models.PositiveSmallIntegerField(choices=[(2, 'Full Day'), (1, 'Half Day'), (0, 'Week Off')], default=2, verbose_name='Sunday')),
                ('week_number', models.IntegerField()),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
                ('work_rule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='work_rule_choices', to='leave.workrules')),
            ],
            options={
                'unique_together': {('work_rule', 'week_number')},
            },
        ),
        migrations.CreateModel(
            name='EmployeeWorkRuleRelation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('effective_date', models.DateField(default=django.utils.timezone.now, verbose_name='Effective Date')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='directory.employee')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
                ('work_rule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='leave.workrules')),
            ],
            options={
                'verbose_name': 'Employee Work Rule Relation',
                'verbose_name_plural': 'Employee Work Rule Relations',
                'unique_together': {('employee', 'work_rule')},
            },
        ),
        migrations.CreateModel(
            name='EmployeeLeaveRuleRelation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('effective_date', models.DateField(default=django.utils.timezone.now, verbose_name='Effective Date')),
                ('remaining_leaves', models.DecimalField(decimal_places=1, default=0, max_digits=3, verbose_name='Balance Leaves')),
                ('earned_leaves', models.DecimalField(decimal_places=1, default=0, max_digits=3, verbose_name='Earned Leaves')),
                ('used_so_far', models.DecimalField(decimal_places=1, default=0, max_digits=3, verbose_name='Applied Leaves')),
                ('penalty_deduction', models.DecimalField(decimal_places=1, default=0, max_digits=3, verbose_name='Penalty Deducted Leaves')),
                ('used_lop_leaves', models.DecimalField(decimal_places=1, default=0, help_text='Used Loss Of Pay Leaves', max_digits=3, verbose_name='LOP Leaves')),
                ('extra_data', models.JSONField(blank=True, default=dict, verbose_name='Extra Data')),
                ('created_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='directory.employee')),
                ('leave_rule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='leave.leaverules')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Employee Leave Rule Relation',
                'verbose_name_plural': 'Employee Leave Rule Relations',
                'unique_together': {('employee', 'leave_rule')},
            },
        ),
    ]
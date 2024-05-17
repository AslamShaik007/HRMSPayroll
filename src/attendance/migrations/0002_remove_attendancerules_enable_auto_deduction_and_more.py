# Generated by Django 4.0.3 on 2023-07-19 07:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='attendancerules',
            name='enable_auto_deduction',
        ),
        migrations.AlterField(
            model_name='penaltyrules',
            name='break_leave_deduction',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AlterField(
            model_name='penaltyrules',
            name='in_leave_deduction',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AlterField(
            model_name='penaltyrules',
            name='out_leave_deduction',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AlterField(
            model_name='penaltyrules',
            name='work_leave_deduction',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
    ]
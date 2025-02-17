# Generated by Django 4.0.3 on 2023-10-11 13:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0031_employeemonthlyattendancerecords_leaves_encash_count'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='attendancerulesettings',
            options={'verbose_name': 'Payroll Setting', 'verbose_name_plural': 'Payroll Settings'},
        ),
        migrations.AlterModelOptions(
            name='attendanceshiftssetup',
            options={'verbose_name': 'Shifts Setup', 'verbose_name_plural': 'Shifts Setups'},
        ),
        migrations.AlterModelOptions(
            name='autodeductionhistory',
            options={'ordering': ['request_date'], 'verbose_name': 'Auto Deduction History', 'verbose_name_plural': 'Auto Deduction Historys'},
        ),
        migrations.AlterModelOptions(
            name='consolidatenotificationdates',
            options={'verbose_name': 'Consolidate Reminder', 'verbose_name_plural': 'Consolidate Reminders'},
        ),
        migrations.AlterModelOptions(
            name='employeecheckinoutdetails',
            options={'verbose_name': 'Attendance History', 'verbose_name_plural': 'Attendance History'},
        ),
        migrations.AlterModelOptions(
            name='employeemonthlyattendancerecords',
            options={'verbose_name': 'Consolidated Reports', 'verbose_name_plural': 'Consolidated Reports'},
        ),
        migrations.AlterModelOptions(
            name='vgattendancelogs',
            options={'verbose_name': 'Boimetric Attendance Logs', 'verbose_name_plural': 'Biometric Attendance Logs'},
        ),
    ]

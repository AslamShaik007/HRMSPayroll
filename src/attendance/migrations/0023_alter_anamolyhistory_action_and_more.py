# Generated by Django 4.0.3 on 2023-09-22 07:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0022_employeemonthlyattendancerecords_is_payroll_run'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anamolyhistory',
            name='action',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(10, 'Mark as Present'), (20, 'Mark as Exact Time'), (30, 'Mark as Leave'), (40, 'Mark as LOP'), (60, 'Mark as OT'), (50, 'Mark as COMPOFF')], help_text='action requested by the user', null=True, verbose_name='Action'),
        ),
        migrations.AlterField(
            model_name='employeecheckinoutdetails',
            name='action',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(10, 'Mark as Present'), (20, 'Mark as Exact Time'), (30, 'Mark as Leave'), (40, 'Mark as LOP'), (60, 'Mark as OT'), (50, 'Mark as COMPOFF')], help_text='action requested by the user', null=True, verbose_name='Action'),
        ),
    ]
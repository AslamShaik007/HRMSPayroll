# Generated by Django 4.0.3 on 2023-07-29 06:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0006_employeeresignationdetails_last_working_day'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employeeworkdetails',
            name='employee_status',
            field=models.CharField(blank=True, default='YetToJoin', max_length=100, null=True),
        ),
    ]

# Generated by Django 4.0.3 on 2023-11-08 10:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0027_employeeresignationdetails_reason_of_leaving'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeeworkdetails',
            name='probation_period_left',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]

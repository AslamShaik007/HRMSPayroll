# Generated by Django 4.0.3 on 2024-02-04 10:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0033_employee_is_rehire'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeeworkhistorydetails',
            name='manager_type',
            field=models.CharField(blank=True, choices=[('Primary', 'Primary'), ('Secondary', 'Secondary')], default='Primary', max_length=32, null=True),
        ),
    ]

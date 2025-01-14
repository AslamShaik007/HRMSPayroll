# Generated by Django 4.0.3 on 2023-11-13 11:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0050_delete_payschedule'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollinformation',
            name='fixed_salary',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=120, null=True),
        ),
        migrations.AddField(
            model_name='payrollinformation',
            name='variable_pay',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=120, null=True),
        ),
    ]

# Generated by Django 4.0.3 on 2023-08-10 06:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0021_employeecompliancenumbers_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reimbursement',
            name='approved_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
    ]

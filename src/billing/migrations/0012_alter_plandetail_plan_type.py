# Generated by Django 4.0.3 on 2024-01-31 10:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0011_alter_plandetail_num_of_employees_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='plandetail',
            name='plan_type',
            field=models.CharField(choices=[('hrms', 'HRMS'), ('payroll', 'PAYROLL'), ('integrated', 'INTEGRATED')], max_length=28),
        ),
    ]

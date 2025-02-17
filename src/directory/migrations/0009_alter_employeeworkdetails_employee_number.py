# Generated by Django 4.0.3 on 2023-08-16 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0008_employeeaddressdetails_other_house_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employeeworkdetails',
            name='employee_number',
            field=models.CharField(blank=True, help_text='Required, Unique, maximum of 246 characters. Employee Unique Identifier.', max_length=246, null=True, verbose_name='Employee Serial Number'),
        ),
    ]

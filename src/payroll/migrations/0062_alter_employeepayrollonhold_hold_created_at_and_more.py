# Generated by Django 4.2 on 2024-03-06 09:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0061_merge_20240306_1427'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employeepayrollonhold',
            name='hold_created_at',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='employeepayrollonhold',
            name='hold_updated_at',
            field=models.DateTimeField(),
        ),
    ]

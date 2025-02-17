# Generated by Django 4.2 on 2023-10-02 12:18

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0030_alter_employeelops_lop_month_year_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeelops',
            name='comp_offs',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='employeelops',
            name='leaves_encashed',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))]),
            preserve_default=False,
        ),
    ]

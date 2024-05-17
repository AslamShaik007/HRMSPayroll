# Generated by Django 4.2 on 2023-10-05 13:56

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0039_payrollinformation_department_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='payrollinformation',
            constraint=models.CheckConstraint(check=models.Q(('salary_before_tds__gte', Decimal('0'))), name='salary_before_tds_constraint'),
        ),
        migrations.AddConstraint(
            model_name='payrollinformation',
            constraint=models.CheckConstraint(check=models.Q(('monthly_tds__gte', Decimal('0'))), name='monthly_tds_constraint'),
        ),
        migrations.AddConstraint(
            model_name='payrollinformation',
            constraint=models.CheckConstraint(check=models.Q(('tds_left__gte', Decimal('0'))), name='tds_left_constraint'),
        ),
    ]
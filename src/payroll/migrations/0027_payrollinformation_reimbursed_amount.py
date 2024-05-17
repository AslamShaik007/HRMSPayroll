# Generated by Django 4.0.3 on 2023-08-17 08:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0026_alter_payrollinformation_paid_days_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollinformation',
            name='reimbursed_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=120, null=True),
        ),
    ]

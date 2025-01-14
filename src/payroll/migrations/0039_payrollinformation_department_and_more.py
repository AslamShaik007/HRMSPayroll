# Generated by Django 4.0.3 on 2023-10-04 15:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0038_employeeot_created_from_employeeot_updated_from'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollinformation',
            name='department',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='payrollinformation',
            name='designation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='payrollinformation',
            name='leaves_taxable_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=70, null=True),
        ),
        migrations.AddField(
            model_name='payrollinformation',
            name='leaves_to_encash',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=70, null=True),
        ),
        migrations.AddField(
            model_name='payrollinformation',
            name='overtime_pay',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=70, null=True),
        ),
        migrations.AddField(
            model_name='payrollinformation',
            name='sub_department',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]

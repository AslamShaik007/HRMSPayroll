# Generated by Django 4.0.3 on 2023-07-25 05:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0017_payrollinformation_consider_tds_percent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollinformation',
            name='month_days',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
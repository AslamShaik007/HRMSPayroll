# Generated by Django 4.2 on 2024-03-14 18:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0064_payrollinformation_other_additions'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollinformation',
            name='mode_of_payment',
            field=models.CharField(blank=True, default='Bank Transfer', max_length=100, null=True),
        ),
    ]

# Generated by Django 4.0.3 on 2023-07-17 07:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investment_declaration', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='investmentdeclaration',
            name='tds_from_previous_employer',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, help_text='TDS From Previous Employer', max_digits=12, null=True, verbose_name='TDS From Previous Employer'),
        ),
    ]

# Generated by Django 4.0.3 on 2023-07-21 05:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0014_alter_payrollinformation_a_basic_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='esi',
            name='esi_no',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]

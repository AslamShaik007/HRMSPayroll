# Generated by Django 4.2 on 2023-09-20 08:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leave', '0009_alter_employeeleaverulerelation_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employeeleaverulerelation',
            name='earned_leaves',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=7, verbose_name='Earned Leaves'),
        ),
    ]
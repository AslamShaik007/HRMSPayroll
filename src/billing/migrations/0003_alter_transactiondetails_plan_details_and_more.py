# Generated by Django 4.0.3 on 2023-07-10 11:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_remove_transactiondetails_user_details'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transactiondetails',
            name='plan_details',
            field=models.CharField(blank=True, max_length=36, null=True),
        ),
        migrations.DeleteModel(
            name='PlanDetail',
        ),
    ]

# Generated by Django 4.0.3 on 2023-07-11 03:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_alter_transactiondetails_plan_details_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='billing',
            old_name='payment_approved_by',
            new_name='payment_updated_by',
        ),
    ]

# Generated by Django 4.0.3 on 2023-08-02 05:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0007_alter_plandetail_plan_type'),
    ]

    operations = [
        migrations.RenameField(
            model_name='billing',
            old_name='payment_approved_by',
            new_name='payment_updated_by',
        ),
    ]

# Generated by Django 4.0.3 on 2023-09-12 05:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0011_employee_is_sign_up'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='is_sign_up',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]

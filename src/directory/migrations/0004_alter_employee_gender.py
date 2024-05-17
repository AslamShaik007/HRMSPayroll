# Generated by Django 4.0.3 on 2023-06-28 11:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0003_alter_employee_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='gender',
            field=models.CharField(blank=True, choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('TRANSGENDER', 'Transgender')], max_length=20, null=True, verbose_name='Gender'),
        ),
    ]
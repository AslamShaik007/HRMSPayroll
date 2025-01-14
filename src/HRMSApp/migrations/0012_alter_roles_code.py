# Generated by Django 4.0.3 on 2023-10-17 11:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('HRMSApp', '0011_alter_companydetails_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='roles',
            name='code',
            field=models.CharField(help_text='Required, Unique, maximum of 50 characters. A category code.', max_length=50, unique=True, verbose_name='Code'),
        ),
    ]

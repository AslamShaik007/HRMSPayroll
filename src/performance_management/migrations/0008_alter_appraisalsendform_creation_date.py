# Generated by Django 4.0.3 on 2023-11-27 13:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('performance_management', '0007_alter_appraisalformsubmit_answer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appraisalsendform',
            name='creation_date',
            field=models.DateTimeField(auto_now=True, help_text='Date Will Be Add Default Current Date And Time', null=True, verbose_name='Creation Date'),
        ),
    ]

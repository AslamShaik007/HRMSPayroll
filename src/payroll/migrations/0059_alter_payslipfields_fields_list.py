# Generated by Django 4.2 on 2024-03-02 09:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0058_paysliptemplates_paysliptemplatefields_payslipfields_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payslipfields',
            name='fields_list',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
    ]
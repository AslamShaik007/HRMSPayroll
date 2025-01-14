# Generated by Django 4.2 on 2024-05-01 12:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0050_employee_al_sign_employee_col_sign_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='appointment_letter_pdf_content',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='employee',
            name='conditional_offer_letter_pdf_content',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='employee',
            name='al_sign',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='employee',
            name='col_sign',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]

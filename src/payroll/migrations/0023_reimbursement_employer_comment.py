# Generated by Django 4.0.3 on 2023-08-10 09:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0022_reimbursement_approved_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='reimbursement',
            name='employer_comment',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]

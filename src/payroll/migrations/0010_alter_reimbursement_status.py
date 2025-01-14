# Generated by Django 4.0.3 on 2023-07-12 09:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0009_reimbursement'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reimbursement',
            name='status',
            field=models.CharField(blank=True, choices=[('All', 'All'), ('Approved & Paid ', 'Approved & Paid'), ('Approved', 'Approved'), ('Pending', 'Pending'), ('Rejected', 'Rejected')], max_length=255, null=True),
        ),
    ]

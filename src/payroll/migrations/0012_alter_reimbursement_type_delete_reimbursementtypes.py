# Generated by Django 4.0.3 on 2023-07-12 11:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0011_alter_reimbursement_status_reimbursementtypes_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reimbursement',
            name='type',
            field=models.CharField(blank=True, choices=[('Travel', 'Travel'), ('Hotel & Accomodation', 'Hotel & Accomodation'), ('Food', 'Food'), ('Medical', 'Medical'), ('Telephone', 'Telephone'), ('Fuel', 'Fuel'), ('Imprest', 'Imprest'), ('Other', 'Other')], max_length=255, null=True),
        ),
        migrations.DeleteModel(
            name='ReimbursementTypes',
        ),
    ]

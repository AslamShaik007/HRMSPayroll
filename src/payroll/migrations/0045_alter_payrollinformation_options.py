# Generated by Django 4.2 on 2023-10-13 11:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0044_merge_20231006_1912'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='payrollinformation',
            options={'ordering': ['-month_year']},
        ),
    ]
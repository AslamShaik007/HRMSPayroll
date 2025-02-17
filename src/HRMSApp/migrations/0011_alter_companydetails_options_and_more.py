# Generated by Django 4.0.3 on 2023-10-11 13:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('HRMSApp', '0010_alter_companydetails_is_brand_name_updated'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='companydetails',
            options={'get_latest_by': 'created_at', 'ordering': ['created_at'], 'verbose_name': 'Organization', 'verbose_name_plural': 'Organization'},
        ),
        migrations.AlterModelOptions(
            name='futuremodule',
            options={'verbose_name': 'Future Module', 'verbose_name_plural': 'Future Modules'},
        ),
        migrations.AlterModelOptions(
            name='grade',
            options={'verbose_name': 'Add Grade Lable', 'verbose_name_plural': 'Add Grade Lables'},
        ),
        migrations.AlterModelOptions(
            name='registration',
            options={'verbose_name': 'Company Registration', 'verbose_name_plural': 'Company Registrations'},
        ),
    ]

# Generated by Django 4.0.3 on 2024-04-29 12:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0047_alter_employee_employee_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employeecertifications',
            name='select_file',
            field=models.FileField(max_length=512, upload_to='employee_certifications/'),
        ),
        migrations.AlterField(
            model_name='employeedocumentationwork',
            name='select_file',
            field=models.FileField(max_length=512, upload_to='documentation_work/'),
        ),
        migrations.AlterField(
            model_name='employeedocuments',
            name='select_file',
            field=models.FileField(blank=True, max_length=512, null=True, upload_to='employee_documents/'),
        ),
        migrations.AlterField(
            model_name='employeeworkdocuments',
            name='work_doc',
            field=models.FileField(max_length=512, upload_to='work_documents/'),
        ),
    ]
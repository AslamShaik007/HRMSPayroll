# Generated by Django 4.0.3 on 2023-07-27 12:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0007_employeemonthlyattendancerecords'),
    ]

    operations = [
        migrations.RenameField(
            model_name='employeemonthlyattendancerecords',
            old_name='updated_lop_count',
            new_name='updated_hr_lop_count',
        ),
        migrations.AddField(
            model_name='employeemonthlyattendancerecords',
            name='updated_manager_lop_count',
            field=models.IntegerField(default=0),
        ),
    ]

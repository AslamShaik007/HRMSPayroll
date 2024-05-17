# Generated by Django 4.0.3 on 2023-08-22 10:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0010_sessionyear'),
        ('attendance', '0013_alter_attendancerules_minimum_minitues_to_over_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignedattendancerules',
            name='session_year',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='directory.sessionyear'),
        ),
    ]

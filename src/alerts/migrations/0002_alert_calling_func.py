# Generated by Django 4.2 on 2024-02-06 14:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='alert',
            name='calling_func',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]
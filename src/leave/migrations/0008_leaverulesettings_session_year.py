# Generated by Django 4.0.3 on 2023-09-18 11:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0013_employeedocuments_document_description_and_more'),
        ('leave', '0007_leaverulesettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaverulesettings',
            name='session_year',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='directory.sessionyear'),
        ),
    ]

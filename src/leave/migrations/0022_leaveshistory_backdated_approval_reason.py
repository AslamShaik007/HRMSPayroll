# Generated by Django 4.0.3 on 2024-02-09 09:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leave', '0021_merge_20240205_1335'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaveshistory',
            name='backdated_approval_reason',
            field=models.TextField(blank=True, max_length=1024, null=True),
        ),
    ]

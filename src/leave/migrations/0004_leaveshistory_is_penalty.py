# Generated by Django 4.0.3 on 2023-07-27 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leave', '0003_alter_employeeleaverulerelation_earned_leaves_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaveshistory',
            name='is_penalty',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]

# Generated by Django 4.0.3 on 2023-10-11 13:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('performance_management', '0004_remove_appraisalsendform_revoke_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='appraisalformsubmit',
            options={'verbose_name': 'Appraisal Form Submit', 'verbose_name_plural': 'Appraisal Form Submit'},
        ),
        migrations.AlterModelOptions(
            name='appraisalsendform',
            options={'verbose_name': 'Send Form', 'verbose_name_plural': 'Send Forms'},
        ),
        migrations.AlterModelOptions(
            name='appraisalsetname',
            options={'verbose_name': 'ADD Questionnaire', 'verbose_name_plural': 'ADD Questionnaires'},
        ),
        migrations.AlterModelOptions(
            name='appraisalsetquestions',
            options={'verbose_name': 'Questionnaire', 'verbose_name_plural': 'Questionnaires'},
        ),
        migrations.AlterModelOptions(
            name='notificationdates',
            options={'verbose_name': 'Notification Date', 'verbose_name_plural': 'Notification Dates'},
        ),
    ]

# Generated by Django 4.0.3 on 2023-11-28 07:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('performance_management', '0008_alter_appraisalsendform_creation_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appraisalsendform',
            name='comment',
            field=models.TextField(blank=True, help_text='Comment Will Be Add To An Employee By Manager', verbose_name='Comment'),
        ),
        migrations.AlterField(
            model_name='appraisalsendform',
            name='reason',
            field=models.TextField(blank=True, default=' ', help_text='Reason Will be Add To An Employee According To Given Score', verbose_name='Reason'),
            preserve_default=False,
        ),
    ]

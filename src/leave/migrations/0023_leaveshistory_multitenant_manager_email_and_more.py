# Generated by Django 4.2 on 2024-03-05 17:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leave', '0022_leaveshistory_backdated_approval_reason'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaveshistory',
            name='multitenant_manager_email',
            field=models.EmailField(blank=True, help_text='Please Enter multitenant Manager Email', max_length=500, null=True, verbose_name='Multitenant Manager Email'),
        ),
        migrations.AddField(
            model_name='leaveshistory',
            name='multitenant_manager_id',
            field=models.CharField(blank=True, help_text='Please Enter multitenant Manager ID', max_length=500, null=True, verbose_name='Multitenant Manager ID'),
        ),
        migrations.AddField(
            model_name='leaveshistory',
            name='multitenant_manager_name',
            field=models.CharField(blank=True, help_text='Please Enter multitenant Manager Name', max_length=500, null=True, verbose_name='Multitenant Manager Name'),
        ),
    ]

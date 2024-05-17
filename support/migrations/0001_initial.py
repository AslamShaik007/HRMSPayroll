# Generated by Django 4.0.3 on 2023-07-07 06:57

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Tickect',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket_id', models.CharField(blank=True, max_length=128, null=True)),
                ('title', models.CharField(max_length=256)),
                ('description', models.TextField(blank=True, null=True)),
                ('raised_by', models.JSONField(default=dict)),
                ('resolved_by', models.JSONField(default=dict)),
                ('comments', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pen', 'Pending'), ('res', 'Resolved'), ('inv', 'Invalid'), ('pro', 'Processing')], default='pen', max_length=16)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
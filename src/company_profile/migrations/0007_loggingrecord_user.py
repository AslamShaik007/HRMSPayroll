# Generated by Django 4.0.3 on 2023-09-29 10:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('company_profile', '0006_loggingrecord_old_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='loggingrecord',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]

import os
from celery import Celery
from django.conf import settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"HRMSProject.settings.{os.environ.get('APP_ENV', 'local')}")

app = Celery('HRMSProject')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.base.INSTALLED_APPS)

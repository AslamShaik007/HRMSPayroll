# import os

# from celery import Celery


# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "HRMSProject.settings")

# app = Celery("insurance", broker="localhost")

# # Well, This means all the cofiguration related to celery will use 'CELERY_' prefix
# app.config_from_object("django.conf:settings", namespace="CELERY")

# # load modules from all registered Django app configs
# app.autodiscover_tasks()


# @app.task(bind=True)
# def debug_task(self):
#     """
#     Just a debug task and a test if celery is working.
#     """
#     print("Request: {!r}".format(self.request))
from .celery import app as celery_app

__all__ = ("celery_app",)
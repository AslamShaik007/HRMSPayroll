import json
import logging

# from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from django_celery_beat.models import CrontabSchedule, PeriodicTask


# import os


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Setup periodic tasks

    AJAY, 28.04.2023
    """

    help = "Setup periodic tasks"

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            "-c",
            action="store_true",
            dest="commit",
            default=False,
            help="Confirmation on populating data.",
        )
        parser.add_argument(
            "--file",
            "-f",
            dest="file",
            default="conf/periodic_tasks.json",
            help="Choose the date file to populate",
        )

    # @transaction.atomic
    def handle(self, **options):
        sid = transaction.set_autocommit(autocommit=False)
        action_commit = options["commit"]
        file = options["file"]

        # CLIENT_DIR = getattr(settings, "CLIENT_DIR", None)
        with open(file) as data_file:
            data = json.load(data_file)

        for task_data in data:
            old_tasks = PeriodicTask.objects.filter(name=task_data["name"])
            if old_tasks:
                continue

            crontab = CrontabSchedule.objects.create(
                minute=task_data["crontab"]["minute"],
                hour=task_data["crontab"]["hour"],
                day_of_month=task_data["crontab"]["day_of_month"],
                month_of_year=task_data["crontab"]["month_of_year"],
                day_of_week=task_data["crontab"]["day_of_week"],
            )

            PeriodicTask.objects.create(
                name=task_data["name"],
                task=task_data["task"],
                interval=None,
                crontab=crontab,
                solar=None,
                args=task_data["args"],
                kwargs=task_data["kwargs"],
                expires=None,
                enabled=True,
            )

        if action_commit:
            logger.info(self.style.SUCCESS("Successful commit"))
            transaction.commit()
        else:
            logger.info(self.style.WARNING("Successful dry-run"))
            transaction.rollback(sid)

from django.core.management import call_command

from celery import shared_task


# @shared_task(name="attendance.generate.anamoly", max_retries=3)
# def generate_anamoly():
#     call_command("generate_anamolies", "--commit")

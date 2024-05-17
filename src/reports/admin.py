from django.contrib import admin

from core.admin import AbstractModelAdmin
from reports.models import Report


@admin.register(Report)
class ReportAdmin(AbstractModelAdmin):
    ...

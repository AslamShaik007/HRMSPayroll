from django.contrib import admin

from core.admin import AbstractModelAdmin
from pss_calendar import models


@admin.register(models.Holidays)
class HolidaysAdmin(AbstractModelAdmin):
    search_fields = ("holiday_name", "holiday_date", "description", "holiday_type")
    list_filter = ("holiday_name", "holiday_type")

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(models.Events)
class EventsAdmin(AbstractModelAdmin):
    search_fields = ("event_title", "start_date", "end_date", "event_description")
    list_filter = ("event_title", "start_date")

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)

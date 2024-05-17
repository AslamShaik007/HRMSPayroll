from django.db import models
from django.utils.translation import gettext_lazy as _

from company_profile.models import Departments
from core.models import AbstractModel
from HRMSApp.models import CompanyDetails


class Holidays(AbstractModel):
    company = models.ForeignKey(
        CompanyDetails,
        on_delete=models.CASCADE,
    )
    holiday_name = models.CharField(
        verbose_name=_("Holiday Name"),
        max_length=200,
        help_text=_("Required, Maximum of 200 Characters."),
    )
    holiday_date = models.DateField(
        verbose_name=_("Holiday Date"),
    )
    description = models.CharField(
        verbose_name=_("Description"),
        max_length=500,
        help_text=_("Required, Maximum of 500 Characters."),
        null=True,
        blank=True,
    )
    holiday_type = models.BooleanField(default=False) #True means optional holiday, False means Mandate holiday
    
    class Meta:
        verbose_name = "Upload Holidays"
        verbose_name_plural = "Upload Holidays"

    def __str__(self) -> str:
        return self.holiday_name


class HolidayFile(models.Model):
    holiday_upload_file = models.FileField(upload_to="holiday_excel")


class Events(AbstractModel):
    VISIBILITY = (
        ("VISIBLE_TO_ALL", "Visible To All"),
        ("LIMITED_VISIBILITY", "Limited Visibility"),
    )

    company = models.ForeignKey(
        CompanyDetails,
        on_delete=models.CASCADE,
    )
    departments = models.ManyToManyField(Departments, related_name="event_departments", default=[])
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY,
        verbose_name="Visibility",
        help_text="It indicates the visibility to the employees",
        null=True,
        blank=True,
    )
    event_title = models.CharField(
        verbose_name=_("Event Title"),
        max_length=500,
    )
    start_date = models.DateField(
        verbose_name=_("Start Date"),
    )
    start_time = models.TimeField(
        verbose_name=_("Start Time"),
    )
    end_date = models.DateField(
        verbose_name=_("End Date"),
    )
    end_time = models.TimeField(
        verbose_name=_("End Time"),
    )
    event_description = models.CharField(
        verbose_name=_("Event Description"),
        max_length=500,
    )
    
    # class Meta:
    #     verbose_name = "Add Events"
    #     verbose_name_plural = "Add Events"

    def __str__(self) -> str:
        return self.event_title

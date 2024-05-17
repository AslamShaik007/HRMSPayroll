import os

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from core.models import AbstractModel


class MyFileStorage(FileSystemStorage):
    # This method is actually defined in Storage
    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))
        return name  # simply returns the name passed

    def url(self, name):
        """
        No matter what, the URL should point to the MEDIA_ROOT

        AJAY, 01.02.2023
        """
        REPORT_MEDIA_URL = settings.REPORT_MEDIA_URL
        return f"{REPORT_MEDIA_URL}{name}"


class Report(AbstractModel):
    """
    Report status information

    AJAY, 21.01.2023
    """

    SUCCESS = "success"
    PENDING = "pending"
    ERROR = "error"

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("error", "Error"),
    )
    name = models.CharField(
        verbose_name=_("Filename"),
        max_length=255,
        help_text=_("Report Filename"),
        blank=True,
        null=True,
    )
    file = models.FileField(
        verbose_name=_("Filename"), blank=True, null=True, storage=MyFileStorage()
    )
    category = models.CharField(
        verbose_name=_("File category"),
        max_length=255,
        help_text=_("File Category"),
    )
    status = models.CharField(
        _("Status"), max_length=128, default="success", choices=STATUS_CHOICES
    )
    notes = models.TextField(_("Notes"), blank=True, null=True)

    employee_model = models.Q(app_label="directory", model="employee")
    limited_models = employee_model

    # content_type = models.ForeignKey(
    #     ContentType,
    #     limit_choices_to=limited_models,
    #     on_delete=models.CASCADE,
    #     verbose_name=_("Content Type"),
    #     null=True,
    # )
    object_id = models.IntegerField(verbose_name=_("Object ID"), null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")

    def __str__(self) -> str:
        return self.name


@receiver(post_delete, sender=Report)
def on_delete(sender, instance, **kwargs):
    """
    Delete Report file.
    """
    if instance.file:
        file = instance.file
        if os.path.isfile(file.path):
            os.remove(file.path)


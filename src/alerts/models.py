from django.db import models

from django.contrib.postgres.fields import ArrayField
from core.models import AbstractModel
from HRMSApp.models import Roles

class Alert(AbstractModel):
    """
    Created-By: Padmaraju P
    Use: Schedule All alerts for given Time and Date
    "path": settings.BASE_DIR / 'scripts/attendance/anamolie_pending_report_to_manager.py',
    "description": "Some Desc",
    "roles": [],
    "interval": "",
    "time": [],
    "days": [],
    "weekdat": [],
    "is_active": False

    """
    class IntervalChoices(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        YEARLY = 'yearly', 'Yearly'

    log_path = models.TextField()
    desc_name = models.CharField(max_length=256, null=True, blank=True)
    name = models.CharField(max_length=256, null=True, blank=True)  # Name of the script file in
    db_name = models.CharField(max_length=256)  # Database Name to run the query on
    path = models.TextField(max_length=1024)
    description = models.TextField(null=True, blank=True)
    roles = models.ManyToManyField(Roles, default=[])
    interval = models.CharField(max_length=16, choices=IntervalChoices.choices, null=True, blank=True)
    run_time = ArrayField(models.CharField(max_length=16, null=True, blank=True), default=list)  # Format ['Hour','Minute']
    days = ArrayField(
        models.PositiveIntegerField(),  
        default=list
    )
    week_days = ArrayField(
        models.CharField(max_length=8, null=True, blank=True),        # Day of the week (Mon, Tue etc.)
        default=list
    )
    is_active = models.BooleanField(default=False)
    calling_func = models.CharField(max_length=256, null=True, blank=True)
    is_email = models.BooleanField(default=False)
    is_whatsapp = models.BooleanField(default=False)
    is_sms = models.BooleanField(default=False)
    
    def __str__(self):
        return f'{self.name} - {self.db_name} - {self.is_active}'
    


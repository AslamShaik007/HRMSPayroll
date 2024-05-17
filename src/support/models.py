import uuid
import random
import string

from django.db import models


def random_string_generator(size=20, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

class Tickect(models.Model):
    class TicketStatus(models.TextChoices):
        PENDING = 'pen', 'Pending'
        RESOLVED = 'res', 'Resolved'
        INVALID = 'inv', 'Invalid'
        PROCESSING = 'pro', 'Processing'
    
    class TicketCategory(models.TextChoices):
        BILLINGISSUE = 'billingissue', 'BillingIssue'
        ACCESSISSUE = 'accessissue', 'AccessIssue'
        PAYROLLISSUE = 'payrollissue', 'PayrollIssue'
    
    ticket_id = models.CharField(max_length=128, null=True, blank=True)
    title = models.CharField(max_length=256)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=28, choices=TicketCategory.choices, default='')
    raised_by = models.JSONField(default=dict, null=True, blank=True)
    resolved_by = models.JSONField(default=dict, null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=TicketStatus.choices, default=TicketStatus.PENDING)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.ticket_id} {self.status}'
    
    def generate_ticket_id(self):
        return random_string_generator(chars=string.ascii_uppercase + string.digits)

    def save(self, *args, **kwargs):
        ticket_id = self.generate_ticket_id()
        if self.__class__.objects.filter(ticket_id=ticket_id).exists():
            ticket_id = self.generate_ticket_id()
        self.ticket_id = ticket_id
        return super().save(*args, **kwargs)

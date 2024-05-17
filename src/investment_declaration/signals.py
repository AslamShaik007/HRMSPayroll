from django.db.models.signals import post_save
from .models import InvestmentDeclaration
from django.dispatch import receiver

from HRMSApp.utils import *
from alerts.utils import check_alert_notification

@receiver(post_save, sender=InvestmentDeclaration)
def invetment_declaration_send_email(sender, instance, created, **kwargs):    
    if instance.status == 50:
        emp_name = instance.employee.name
        emp_email = instance.employee.official_email     
        company_name = instance.employee.company.company_name   
        emp_number = instance.employee.work_details.employee_number
        emp_tag = emp_number if emp_number else "-"
        body = f" Hello {emp_name} [{emp_tag}], \n\nYour Saving Declaration cancelled \n\nThanks & Regards,\n{company_name}"
        data = {
            "subject": "Saving Declaration Form Decline/Revoked",
            "body": body,            
            "to_email": emp_email
        }    
        if check_alert_notification("Saving Declaration",'Form Decline/Revoked', email=True):  
            Util.send_email(data)        
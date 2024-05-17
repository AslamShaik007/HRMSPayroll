import logging

from core.utils import timezone_now
from core.whatsapp import WhatsappMessage

from HRMSApp.utils import Util

from alerts.utils import check_alert_notification

logger = logging.getLogger('django')


def manager_hr_email_notifications(instance, manager_ins, hr_email, logged_in_user):
    try:
        emp_designation = instance.work_details.designation.name if instance.work_details.designation else ''
        body=f"""
    Hello {manager_ins.manager.user.username.title()} [{manager_ins.manager.work_details.employee_number}],

    We would like to inform you that a new employee, {instance.user.username.title()} has been successfully added to your team in the HRMS system, 

    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()}

    {instance.user.username.title()} will be contributing to {emp_designation} We Trust they will be a valuable addition to your team.

    Thank you for your attention, and we appreciate your support in welcoming our new team member.

    Thanks & Regards,
    {instance.company.company_name.title()}.
    """
        data = {
                'subject': 'New Employee Assignment',
                'body':body,
                'to_email': manager_ins.manager.user.email,
                'cc' : hr_email
            }
        if check_alert_notification("Employee Management","Add Employee", email=True):
            Util.send_custom_email(data)
    except Exception as e:
        logger.warning(f"Error while sending email notificaton to {manager_ins.manager.user.username} in notifications Update on boarding employee: {e}") 
        
def manager_hr_whatsapp_notifications(instance, manager_ins, hr_phone, domain):
    try:
        manager_data = {
                'phone_number':  hr_phone,
                'subject': 'New Employee Assignment',
                "body_text1":f"{instance.user.username.title()} has been successfully added to your team",
                'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                'url': f"{domain}directory",
                "company_name":instance.company.company_name.title()
                }
        if check_alert_notification("Employee Management","Add Employee", whatsapp=True):
            WhatsappMessage.whatsapp_message(manager_data)
    except Exception as e:
        logger.warning(f"Error while sending Whatsapp notificaton to {manager_ins.manager.user.username} in notifications Update on boarding employee: {e}") 

def employee_email_about_manager(instance, manager_ins, logged_in_user):
    try:
        body=f"""                                                                                                                                                                   
    Hello {instance.user.username.title()},

    We would like to inform you that a new reporting manager {manager_ins.manager.user.username.title()}, has been assigned to you in our HRMS system

    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},

    {manager_ins.manager.user.username.title()},will be overseeing your role and responsibilities moving forward. If you have any questions or need assistance during this transition, 

    please feel free to reach out to {manager_ins.manager.user.username.title()} directly.

    We appreciate your cooperation and wish you continued success in your role under the guidance of your new reporting manager.

    Thanks & Regards,
    {instance.company.company_name.title()}.
        """
        data={
                'subject': 'New Reporting Manager Assignment',
                'body':body,
                'to_email': instance.user.email
            }
        if check_alert_notification("Employee Management","Add Employee", email=True):
            Util.send_custom_email(data)
    except Exception as e:
        logger.warning(f"Error while sending email notificaton to {instance.user.username} in notifications Update on boarding employee: {e}") 

def employee_whatsapp_about_manager(instance, manager_ins, domain):
    try:
        employee_data = {
                'phone_number': instance.user.phone,
                'subject': 'New Reporting Manager Assignment',
                "body_text1": f"We would like to inform you that a new reporting manager {manager_ins.manager.user.username.title()} has been assigned to you",
                'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                'url': f"{domain}userprofile",
                "company_name":instance.company.company_name.title()
                }
        if check_alert_notification("Employee Management","Add Employee", whatsapp=True):
            WhatsappMessage.whatsapp_message(employee_data)
    except Exception as e:
        logger.warning(f"Error while sending whatsapp notificaton to {instance.user.username} in notifications Update on boarding employee: {e}") 

def employee_email_welcome(instance, manager_ins):
    try:
        body=f"""
    Hello {instance.user.username.title()},

    We are pleased to inform you that you have been successfully added to {instance.company.company_name.title()}.

    If you have any questions or need assistance during this transition, please feel free to reach out to {manager_ins.manager.user.username.title()} directly.

    Thank you for your attention, and we appreciate your support in welcoming our new team member.

    Thanks & Regards,
    {instance.company.company_name.title()}.
        """
        data={
                'subject': f'Welcome To {instance.company.company_name.title()}',
                'body':body,
                'to_email': instance.official_email
            }
        if check_alert_notification("Employee Management","Add Employee", email=True):
            Util.send_custom_email(data)
    except Exception as e:
        logger.warning(f"Error while sending whatsapp notificaton to {instance.user.username} in notifications Update on boarding employee: {e}") 

def employee_whatsapp_welcome(instance, domain):
    try:
        whatsapp_data = {
                        'phone_number': instance.user.phone,
                        'subject': f'Welcome To {instance.company.company_name.title()}',
                        "body_text1":f"We are pleased to inform you that you have been successfully added to {instance.company.company_name.title()}",
                        'body_text2': " ",
                        'url': f"{domain}userprofile",
                        "company_name":instance.company.company_name.title()
                        }
        if check_alert_notification("Employee Management","Add Employee", whatsapp=True):
            WhatsappMessage.whatsapp_message(whatsapp_data)
    except Exception as e:
        logger.warning(f"Error while sending whatsapp notificaton to {instance.user.username} in notifications Update on boarding employee: {e}") 
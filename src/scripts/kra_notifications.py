import sys
import os
import django
from django.db import models as db_models
from django.contrib.postgres.aggregates import ArrayAgg
sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from core.utils import timezone_now
from core.utils import timezone_now, get_domain

from performance_management.models import AppraisalSendForm,NotificationDates
from HRMSApp.utils import Util
from directory.models import ManagerType

import logging
logger = logging.getLogger("django")
from core.whatsapp import WhatsappMessage


class KraNotifications:
    
    def __init__(self,company_id):
        self.company_id = company_id
    
    def main(self):
        today = timezone_now().date()
        current_date = today.strftime('%m-%Y')
        params = {
            'company__id': company_id
        }
        manager_domain = get_domain(sys.argv[-1], sys.argv[1], 'allkrafromlist')
        emp_domain = get_domain(sys.argv[-1], sys.argv[1], 'employeekra')
        notification_date = NotificationDates.objects.filter(**params).first()
        q_filters = db_models.Q(employee__company__id=company_id)
        obj = AppraisalSendForm.objects.filter(q_filters).select_related(
                'employee'
                ).annotate(
                            employee_name = db_models.F('employee__user__username'),
                            employee_official_email = db_models.F('employee__official_email'),
                            employee_phone = db_models.F('employee__phone'),
                            # manager_name =db_models.F('employee__manager__user__username'),
                            # manager_official_email = db_models.F('employee__employee_manager__manager__official_email'),
                            # manager_employee_name =db_models.F('employee__employee_manager__employee__user__username')
                            manager_name  = ArrayAgg('employee__employee__manager__user__username',
                                    filter=db_models.Q(employee__employee__isnull=False, employee__is_deleted=False, 
                                                       employee__employee__manager__work_details__employee_status='Active',
                                                    employee__employee__manager_type__manager_type=ManagerType.PRIMARY,
                                                    employee__employee__is_deleted=False),
                                    distinct=True),
                            manager_official_email  = ArrayAgg('employee__employee__manager__user__email',
                                    filter=db_models.Q(employee__employee__isnull=False, employee__is_deleted=False, 
                                                       employee__employee__manager__work_details__employee_status='Active',
                                                    employee__employee__manager_type__manager_type=ManagerType.PRIMARY,
                                                    employee__employee__is_deleted=False),
                                    distinct=True),
                            manager_phone  = ArrayAgg('employee__employee__manager__phone',
                                    filter=db_models.Q(employee__employee__isnull=False, employee__is_deleted=False, 
                                                       employee__employee__manager__work_details__employee_status='Active',
                                                    employee__employee__manager_type__manager_type=ManagerType.PRIMARY,
                                                    employee__employee__is_deleted=False),
                                    distinct=True),
                            rp_gender=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False),
                                                                     then=db_models.F('employee__employee__manager__gender')),
                                                       default=db_models.Value(''), output_field=db_models.CharField()),
                            rp_emp_code=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False),
                                                                     then=db_models.F('employee__employee__manager__work_details__employee_number')),
                                                       default=db_models.Value(''), output_field=db_models.CharField())
                            ).values(
                                    'creation_date',
                                    'candidate_status',
                                    'employee_name',
                                    'employee_official_email',
                                    'monthly_score_status',         
                                    'manager_name',
                                    'manager_official_email',
                                    'form_deadline_date',
                                    'employee__company__company_name',
                                    'rp_gender',
                                    'employee__gender',
                                    'employee__work_details__employee_number',
                                    'rp_emp_code',
                                    'employee_phone',
                                    'manager_phone'
                                    )

        for qs in obj:
            qs_date = qs['creation_date']
            dead_line_date = qs['form_deadline_date']
            company_name = qs['employee__company__company_name']
            month_year = qs_date.strftime('%m-%Y')
            emp_code = qs['employee__work_details__employee_number']
            rp_emp_code = qs['rp_emp_code']
            if qs['candidate_status'] == "NOT SUBMITTED" and month_year == current_date and timezone_now().date().day >= notification_date.notification_start_date.day and timezone_now().date().day <= notification_date.notification_end_date.day:
                try:
                    body1 = f""" 
    Hello {qs['employee_name'].title()} [{emp_code}],
    
    This is a gentle reminder that you have to submit your monthly KRA Form before {qs['form_deadline_date'].strftime('%d')}th of {dead_line_date.strftime('%b')},

    Please refer the link for more information {emp_domain} 
    
    Thanks & Regards,
    {company_name.title()}.
    """
                    data = {
                        "subject": "Reminder- Monthly check-in due date approaching",
                        "body": body1,
                        "to_email": qs['employee_official_email']
                    }
                    if "commit" in sys.argv:
                        Util.send_email(data)
                        try:
                            employee_data = {
                                    'phone_number':qs['employee_phone'],
                                    'subject': "Reminder- to submit KRA",
                                    'body_text1' : "You should submit KRA Form before",
                                    'body_text2' : f"{qs['form_deadline_date'].strftime('%d')}th of {dead_line_date.strftime('%b')}",
                                    'url': f"{emp_domain}",
                                    "company_name": company_name
                                    }
                            WhatsappMessage.whatsapp_message(employee_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to emp about kra : {e}")
                except Exception as e:
                    pass

            if qs['candidate_status'] == "NOT SUBMITTED" and month_year == current_date and timezone_now().date().day == dead_line_date.day:
                try:
                    body2 = f""" 
    Hello {qs['employee_name'].title()} [{emp_code}],
    
    This is a gentle reminder that you have not submitted your monthly KRA form on the due date of the month {today.strftime('%B')}.
    
    So fill the KRA form by {dead_line_date},
    
    Please refer the link for more information {emp_domain} 
    
    Thanks & Regards,
    {company_name.title()}
    """
                    data = {
                        "subject": "Alert- Monthly check-in passed due date",
                        "body": body2,
                        "to_email": qs['employee_official_email']
                    }
                    if "commit" in sys.argv:
                        Util.send_email(data)
                        try:
                            employee_data = {
                                    'phone_number':qs['employee_phone'],
                                    'subject': "Alert- Monthly check-in passed due date",
                                    'body_text1' : "This is to remind you have not submitted your monthly KRA form of this month ",
                                    'body_text2' : f"Last date to fill form is {dead_line_date}.",
                                    'url': f"{emp_domain}",
                                    "company_name": company_name
                                    }
                            WhatsappMessage.whatsapp_message(employee_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to about Exit interview sheet : {e}")
                except Exception as e:
                    pass
            
            if qs['monthly_score_status'] == "PENDING" and qs['candidate_status'] == "SUBMITTED" and month_year == current_date and timezone_now().date().day >= notification_date.reporting_manager_start_date.day and timezone_now().date().day <= notification_date.reporting_manager_end_date.day:
                try:
                    body3 = f"""
    Hello {qs['manager_name'][0].title()} [{rp_emp_code}],
    
    This e-mail is a gentle reminder to submit your score for the Monthly check-in assessment to the employee {qs['employee_name'].title()} [{qs['employee__work_details__employee_number']}] before {qs['form_deadline_date'].strftime('%d')}th of {dead_line_date.strftime('%b')},
    
    Please refer the link for more information {manager_domain} 
    
    Thanks & Regards,
    {company_name.title()}.
    """
                    print("came_herer")
                    data = {
                        "subject": "Monthly check in assessment completion",
                        "body": body3,
                        "to_email": qs['manager_official_email'][0]
                    }
                    if "commit" in sys.argv:
                        Util.send_email(data)
                        try:
                            employee_data = {
                                    'phone_number': qs['manager_phone'],
                                    'subject': "Score card",
                                    'body_text1' : f" {qs['employee_name'].title()} [{qs['employee__work_details__employee_number']}]",
                                    'body_text2' : f"Provide scores to above employees for this month.before {qs['form_deadline_date'].strftime('%d')}th",
                                    'url': f"{manager_domain}",
                                    "company_name": company_name
                                    }
                            WhatsappMessage.whatsapp_message(employee_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to about submit your score : {e}")
                except Exception as e:
                    pass

            if qs['monthly_score_status'] == "PENDING" and qs['candidate_status'] == "SUBMITTED" and month_year == current_date and timezone_now().date().day == dead_line_date.day:
                try:
                    body4 = f"""
    Hello {qs['manager_name'][0].title()} [{rp_emp_code}],
    
    This is to notify that you have not given monthly check in score for the employee {qs['employee_name'].title()} [{qs['employee__work_details__employee_number']}] for the month of {today.strftime('%b')}. Please complete the Monthly check-in assessment immediately,
    
    Please refer the link for more information {manager_domain}
    
    Thanks & Regards,
    {company_name.title()}
    """
                    data = {
                        "subject": "Monthly check-in assessment pending",
                        "body": body4,
                        "to_email": qs['manager_official_email'][0]
                    }
                    if "commit" in sys.argv:
                        Util.send_email(data)
                        try:
                            employee_data = {
                                    'phone_number': qs['manager_phone'],
                                    'subject': "Monthly check in assessment pending",
                                    'body_text1' :  f" {qs['employee_name'].title()} ,for the month of {today.strftime('%b')} ",
                                    'body_text2' : " This is to notify that you have not given monthly check in score for these employee",
                                    'url': f"{manager_domain}",
                                    "company_name": company_name
                                    }
                            WhatsappMessage.whatsapp_message(employee_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to about Exit interview sheet : {e}")
                except Exception as e:
                    pass
        
        
        # print("KRA Notification mails sent successfully")
        if "commit" in sys.argv:
            print("KRA Notification mails sent successfully")
        else:
            print("Dry Run!")
if __name__ == "__main__":
    company_id = 1
    KraNotifications(company_id=company_id).main()
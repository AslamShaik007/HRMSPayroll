import sys
import os
import django
import datetime
import logging
from django.db import models as db_models

sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from attendance.models import AssignedAttendanceRules
from HRMSApp.utils import Util
from core.utils import timezone_now, get_domain
from core.whatsapp import WhatsappMessage

logger=logging.getLogger('django')

class WeeklyAttedanceReminders:
    
    def __init__(self,company_id):
        self.company_id = company_id
        
    def main(self):
        
        q_filter = db_models.Q(employee__work_details__employee_status='Active', is_deleted=False, effective_date__lte=timezone_now().date())
        emp_emails = list(AssignedAttendanceRules.objects.filter(q_filter).values('employee__user__username','employee__official_email',
                                                                                  'employee__company__company_name','employee__work_details__employee_number',
                                                                                  'employee__user__phone'))

        domain = get_domain(sys.argv[-1], sys.argv[1], 'userAttendancelogs')
        
        if "commit" in sys.argv:  
            print("Weekly Attedance Reminders sending in progress")
            if emp_emails:
                print("emp_emails:",emp_emails)
                for data in emp_emails:
                    emp_email = data['employee__official_email']
                    emp_name = data['employee__user__username'].title()
                    cmp_name = data['employee__company__company_name'].title()
                    
                    emp_number = data['employee__work_details__employee_number']
                    # gender = data['employee__gender']
                    tag = emp_number if emp_number else "-"
                    today = timezone_now().date() - datetime.timedelta(days=1)
                    last_week = today - datetime.timedelta(days=6)
                    emp_phone = data['employee__user__phone']
                    try:
                        body = f'''
    Hello {emp_name} [{tag}],
    
    We kindly request you to take a moment to log in to the attendance system at {domain} and verify that your hours for the {last_week.strftime('%d-%m-%Y')} to {today.strftime('%d-%m-%Y')} are accurately recorded. 
    
    Should you encounter any issues or have questions regarding the process, please don't hesitate to reach out to the Reporting Manager or HR department for assistance.

    Your cooperation is greatly appreciated. Thank you,
    
    Thanks & Regards,
    {cmp_name}.
    '''
                        data = {
                            "subject": "Reminder Check Your Weekly Attendance",
                            "body": body,
                            "to_email": emp_email
                        }
                        Util.send_email(data)
                    except Exception as e:
                        print(f"exception in sending Weekly Attedance Reminders mail to {emp_email}:",e)
                    
                    # employee Whatsapp notifications
                    try:
                        whatsapp_data = {
                                        'phone_number': emp_phone,
                                        'subject': "Reminder Check Your Weekly Attendance",
                                        "body_text1":"We kindly request you to take a moment to log in to the attendance system and ",
                                        'body_text2': f"Verify that your hours for the {last_week.strftime('%d-%m-%Y')} to {today.strftime('%d-%m-%Y')} are accurately recorded.",
                                        'url': f"{domain}",
                                        "company_name":cmp_name
                                        }
                        if "commit" in sys.argv:
                            WhatsappMessage.whatsapp_message(whatsapp_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {emp_name} in employee weekly attendace reminders emails: {e}") 
                print("Weekly Attedance Reminders sent successfully!")

        else:
            print("Dry Run!")
        

if __name__ == "__main__":
    company_id = 1
    WeeklyAttedanceReminders(company_id=company_id).main()

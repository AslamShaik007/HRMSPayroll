import os
import sys
import django
from django.db import models as db_models
from django.contrib.postgres.aggregates import ArrayAgg
import pandas as pd
sys.path.append('./')
if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]
from django.db import transaction

from investment_declaration.models import InvestmentDeclaration
from core.utils import timezone_now, get_domain, email_render_to_string
from HRMSApp.utils import Util
from HRMSApp.models import Roles
from directory.models import ManagerType

import logging
logger = logging.getLogger("django")
from core.whatsapp import WhatsappMessage


class UpcomingLastSubmissionDate:

    def main(self):
        
        domain = get_domain(sys.argv[-1], sys.argv[1], 'approveddeclarations')
        current_year = timezone_now().date().year
        current_day = timezone_now().date()
        start_year = current_day.year
        end_year = current_day.year + 1
        if current_day.month < 3:
            start_year = current_day.year - 1
            end_year = current_day.year
        q_filter = db_models.Q(is_deleted=False, status= 10, regime_type__in =[10,20],employee__work_details__employee_status="Active",start_year=start_year,end_year=end_year)
        emp = InvestmentDeclaration.objects.filter(q_filter).values('employee__work_details__employee_number','employee__user__username',
                                                            'employee__company__company_name','employee__user__email','start_year','end_year','employee__user__phone')
        
        if "commit" in sys.argv:
            print(" Reminder for Upcoming Submission Deadline Emails Sending in Progress")
        else:
            print("Dry Run!")   
            
        for obj in emp:   
            try:
                emp_name = obj['employee__user__username'].title()
                emp_official_email = obj['employee__user__email']
                emp_number = obj['employee__work_details__employee_number']
                company_name = obj['employee__company__company_name'].title()

                body = f'''
    Dear {emp_name} [{emp_number}],

    This is a friendly reminder to declare your savings for the year {start_year} to {end_year} on or before the deadline. Please ensure timely submission for compliance.

    Thank you for your cooperation.

    Best regards,
    {company_name}.

    '''          
                data={
                    'subject': f'Reminder for submission of Saving Declaration before End Date for the year {start_year} to {end_year}',
                    'body':body,
                    'to_email':emp_official_email
                }
                if "commit" in sys.argv:
                    Util.send_email(data)
                    # employee Whatsapp notifications
                    try:
                        employee_data = {
                                'phone_number': obj['employee__user__phone'],
                                'subject': 'Reminder to submit Saving Declaration form',
                                'body_text1' : f"please submit Saving Declaration before End Date for the year {start_year} to {end_year} ",
                                'body_text2' : " ",
                                'url': f"{domain}",
                                "company_name": company_name
                                }
                        WhatsappMessage.whatsapp_message(employee_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {emp_name} about saving declaration : {e}")
            except Exception as e:
                print("Execption in  Reminder for Upcoming Submission Deadline Emails to Emp:",e)
                
if __name__ == "__main__":
    UpcomingLastSubmissionDate().main()
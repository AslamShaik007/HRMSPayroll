import os
import sys
import django
from django.db import models as db_models
sys.path.append('./')
if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from investment_declaration.models import InvestmentDeclaration
from core.utils import timezone_now, get_domain, email_render_to_string
from HRMSApp.utils import Util

import logging
logger = logging.getLogger("django")
from core.whatsapp import WhatsappMessage


class YearEndSummaryStatement:

    def main(self):
        
        domain = get_domain(sys.argv[-1], sys.argv[1], 'savingdeclarationList')
        current_day = timezone_now().date()
        start_year = current_day.year
        end_year = current_day.year + 1
        if current_day.month < 3:
            start_year = current_day.year - 1
            end_year = current_day.year
            
        q_filter = db_models.Q(is_deleted=False, admin_resubmit_status__in= [90], regime_type__in =[10,20], start_year=start_year, end_year=end_year)
        emp = InvestmentDeclaration.objects.filter(q_filter).values('employee__work_details__employee_number','employee__user__username',
                                                            'employee__company__company_name','employee__user__email','employee__user__phone')
        
        if "commit" in sys.argv:
            print("Year End Summary Statement Emails Sending in Progress")
        else:
            print("Dry Run!")   
            
        for obj in emp:   
            try:
                emp_name = obj['employee__user__username'].title()
                emp_official_email = obj['employee__user__email']
                emp_number = obj['employee__work_details__employee_number']
                company_name = obj['employee__company__company_name'].title()

                body = f'''
    Hello {emp_name} [{emp_number}],
    
    As the year concludes, here is a summary of your declared savings for your records and tax planning purposes.
    
    Link : {domain}
    
    Thanks & Regards,
    {company_name}.
    '''
                
                data={
                        'subject':f"{emp_name} Savings Declaration Year-End Summary",
                        'body':body,
                        'to_email':emp_official_email
                    }
                if "commit" in sys.argv:
                    Util.send_email(data)
                # employee Whatsapp notifications
                try:
                    employee_data = {
                            'phone_number': obj['employee__user__phone'],
                            'subject': 'Savings Declaration of this Year-End Summary',
                            'body_text1' : f"Here is a summary of your declared savings, intended for your records and for facilitating tax planning purposes ",
                            'body_text2' : " ",
                            'url': f"{domain}",
                            "company_name": company_name
                            }
                    WhatsappMessage.whatsapp_message(employee_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to {emp_name} about saving declaration approval: {e}")
            except Exception as e:
                print("Execption in Year End Summary Statement Emails to Emp:",e)
                
if __name__ == "__main__":
    YearEndSummaryStatement().main()

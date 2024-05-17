import sys
import os
import django
import traceback
from datetime import timedelta

sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]
from HRMSApp.utils import Util
from core.utils import timezone_now,get_domain
from attendance.models import AttendanceRuleSettings
from HRMSApp.models import CompanyDetails
from directory.models import Employee
from payroll.management.commands.tax_config_json import state_taxes_dict

import logging
logger = logging.getLogger("django")
from core.whatsapp import WhatsappMessage

class Pay_Cycle_Send_Emails:
    """
    this class is used to fix the state tax config if any new state is added
    """
    # @transaction.atomic
    def main(self):
        try:
            domain = get_domain(sys.argv[-1], sys.argv[1], 'userprofile')
            company_name = CompanyDetails.objects.first().company_name
            admin_data = Employee.objects.filter(work_details__employee_status='Active', roles__name__in=['ADMIN']).values('user__username','official_email','phone')
            ars_obj = AttendanceRuleSettings.objects.get(company_id=1)
            today = timezone_now().date()
            end_day = ars_obj.attendance_paycycle_end_date
            formatted_end_day = end_day.strftime('%d-%m-%Y')
            pay_before_day = end_day - timedelta(days=3)
           
            
            
            # if now.hour == 8 and now.minute == 0:
            if pay_before_day <= today <= end_day:
             for data in admin_data:
                admin_username = data['user__username']
                admin_email = data['official_email']
                body = f'''
    Dear {admin_username},
    
    This is to inform you that date is approaching to run the payroll for the month of {formatted_end_day}.

    Best Regards,
    {company_name}
    
    '''
                data = {
                        'subject':'Reminder to run payroll for the month',
                        'body':body,
                        'to_email': admin_email
                       }
                if "commit" in sys.argv:
                    Util.send_email(data)
                    try:
                        employee_data = {
                                'phone_number': data['phone'],
                                'subject': 'Reminder to run payroll for the month',
                                'body_text1' : f"This is to inform you that date is approaching to run the payroll for the month of {formatted_end_day}.",
                                'body_text2' : " ",
                                'url': f"{domain}",
                                "company_name": company_name
                                }
                        WhatsappMessage.whatsapp_message(employee_data)
                    except Exception as e:
                        print('e',e)
                        logger.warning(f"Error while sending Whatsapp notificaton to {admin_username} about saving declaration : {e}")
        except Exception as e:
            print("exception in sending mails in payroll Reminder:",e)
            pass

if __name__ == "__main__":
    Pay_Cycle_Send_Emails().main()
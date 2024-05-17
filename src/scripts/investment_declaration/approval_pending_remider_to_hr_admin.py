import os
import sys
import django
from django.db import models as db_models
import pandas as pd


sys.path.append('./')
if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]
from django.db import transaction

from investment_declaration.models import InvestmentDeclaration
from core.utils import timezone_now, get_paycycle_dates, email_render_to_string,get_domain
from HRMSApp.utils import Util
from HRMSApp.models import Roles
from HRMSApp.models import CompanyDetails

import logging
logger = logging.getLogger("django")
from core.whatsapp import WhatsappMessage


class ApprovalPendingRemiderHrAdmin:
    
    def main(self):
        try:
            today = timezone_now()
            company_id = 1
            company_obj = CompanyDetails.objects.filter(id=company_id).first()
            company_name = company_obj.company_name
            current_day = timezone_now().date()
            start_year = current_day.year
            end_year = current_day.year + 1
            if current_day.month < 3:
                start_year = current_day.year - 1
                end_year = current_day.year
            
            hr_admin_emails = Roles.objects.filter(name__in=["ADMIN","HR"],roles_employees__company_id = 1,roles_employees__work_details__employee_status="Active").values(
                                                                                            "roles_employees__official_email",
                                                                                            "roles_employees__user__username",
                                                                                            "roles_employees__work_details__employee_number",
                                                                                            "roles_employees__phone")
            domain = get_domain(sys.argv[-1], sys.argv[1], 'savingdeclarationList')
            q_filter = db_models.Q(is_deleted=False, status__in = [20,30], employee__work_details__employee_status="Active",
                                   employee__payroll_status=True,start_year=start_year,end_year=end_year)
            
            data = InvestmentDeclaration.objects.filter(q_filter & ~(db_models.Q(admin_resubmit_status =90))).values(
                'employee__user__username','employee__official_email','employee__work_details__employee_number','status','start_year','end_year'
            )
            
            df_data = pd.DataFrame(data,columns = ['employee__user__username','employee__official_email',
                                                'employee__work_details__employee_number','employee__work_details__department__name','status','start_year','end_year'])
            data_dict = df_data.to_dict('records')
            if ("commit" in sys.argv) and (len(df_data) != 0):
                print("Email Sending in progress")
                # if len(df_data) != 0:
                for obj in hr_admin_emails:
                    try:
                        name = obj['roles_employees__user__username'].title()
                        email = obj['roles_employees__official_email']
                        emp_code = obj['roles_employees__work_details__employee_number']
                        phone = obj['roles_employees__phone']
                        body = email_render_to_string(
                                        template_name="mails/saving_declaration_templates/approval_pending_reminder.html", context={"recds":data_dict,
                                                                                                                            "company_name":company_name.title(),
                                                                                                                            "name":name,"emp_code":emp_code}
                                    )
                        data={
                                'subject':f'Approval Request: Savings Declaration for the year {start_year} to {end_year}',
                                'body':body,
                                'to_email':email
                            }  
                        Util.send_email(data,is_content_html=True)   
                        # Hr and manager Whatsapp notifications
                        try:
                            employee_data = {
                                    'phone_number': phone,
                                    'subject': 'We request you to review and approve the savings declaration forms.',
                                    'body_text1' : "Pending requests from employees of ",
                                    'body_text2' : f"Savings Declaration for the year {start_year} to {end_year}",
                                    'url': f"{domain}",
                                    "company_name": company_name
                                    }
                            WhatsappMessage.whatsapp_message(employee_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to {name} about leave and attendence approval: {e}")
                    except Exception as e:
                        print("Execption in sending Emails:",e) 
            else:
                print("Dry Run!")  
        except Exception as e:
                print("Overall_Exception:",e)      
                    
if __name__ == "__main__":
    ApprovalPendingRemiderHrAdmin().main()
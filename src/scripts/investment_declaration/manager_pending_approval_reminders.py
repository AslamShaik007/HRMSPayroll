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

from investment_declaration.models import InvestmentDeclaration
from core.utils import email_render_to_string,get_domain
from HRMSApp.utils import Util

import logging
logger = logging.getLogger("django")
from core.whatsapp import WhatsappMessage


class StatusReminder:

    def main(self):
        
        domain = get_domain(sys.argv[-1], sys.argv[1], 'savingdeclaration')

        q_filter = db_models.Q(is_deleted=False, status__in= [20,30], regime_type__in =[10,20] )
        emp = InvestmentDeclaration.objects.filter(q_filter).annotate(
                manager_name  = db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                            then=db_models.F('employee__employee__manager__user__username')),
                                                    default=db_models.Value(''), output_field=db_models.CharField()),
                manager_official_email  = db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                            then=db_models.F('employee__employee__manager__user__email')),
                                                    default=db_models.Value(''), output_field=db_models.CharField()),
                manager_emp_code = db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                            then=db_models.F('employee__employee__manager__work_details__employee_number')),
                                                    default=db_models.Value(''), output_field=db_models.CharField()),
                manager_phone = db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                            then=db_models.F('employee__employee__manager__user__phone')),
                                                    default=db_models.Value(''), output_field=db_models.CharField()),
            ).values('employee__work_details__employee_number','employee__user__username','employee__company__company_name',
                     'manager_name','manager_official_email','employee__work_details__department__name','employee__work_details__designation__name','manager_emp_code')
        emp_df = pd.DataFrame(emp, columns=['employee__work_details__employee_number','employee__user__username','employee__company__company_name',
                                             'manager_name','manager_official_email','employee__work_details__department__name','employee__work_details__designation__name','manager_emp_code'])
        emp_df = emp_df[emp_df['manager_name'].notnull() & (emp_df['manager_official_email'] != '')]
        emp_df["combine"] = emp_df.apply(lambda obj: f"{obj['employee__work_details__employee_number']}---->{obj['employee__user__username']}---->{obj['employee__work_details__designation__name']}---->{obj['employee__work_details__department__name']}", axis=1)
        emp_df = emp_df.groupby('manager_official_email').agg({"combine": list,
                                            "manager_emp_code":"first",
                                            "employee__company__company_name":"first",
                                            "manager_name":"first"
                                            }).reset_index()
        data_dict = emp_df.to_dict('records')
        
        if "commit" in sys.argv:
            print("Reminder To Approve The Saving Declaration Emails Sending in Progress")
        else:
            print("Dry Run!")   
            
        for obj in data_dict:   
            try:
                rep_name = obj['manager_name'].title()
                rep_official_email = obj['manager_official_email']
                rp_emp_number = obj['manager_emp_code']
                rep_official_phone = obj['employee__employee__manager__user__phone']
                company_name = obj['employee__company__company_name'].title()
                if rep_official_email:
                    combine_data = obj['combine']
                    split_data = [item.split('---->') for item in combine_data]
                    name_dep_df = pd.DataFrame(split_data, columns=['emp_id','emp_name', 'designation', 'department'])
                    name_dep_df1 = name_dep_df.to_dict('records')
                    context = {"recds":name_dep_df1,
                                "company_name":company_name,
                                "reporting_manager_name":rep_name,"rp_emp_number":rp_emp_number}
                    body = email_render_to_string(
                                template_name="mails/payroll_templates/manager_approvals.html", context=context
                            )
                    data={
                            'subject':"Reminder To Approve The Saving Declaration",
                            'body':body,
                            'to_email':rep_official_email
                        }
                    if "commit" in sys.argv:
                        Util.send_email(data,is_content_html=True)
                        # manager Whatsapp notifications
                        try:
                            employee_data = {
                                    'phone_number': rep_official_phone,
                                    'subject': 'Reminder To Approve The Saving Declaration ',
                                    'body_text1' : f"Approve Employee saving Declaration form ",
                                    'body_text2' : " ",
                                    'url': f"{domain}",
                                    "company_name": company_name
                                    }
                            WhatsappMessage.whatsapp_message(employee_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to {rep_name} about saving declaration approval: {e}")
            except Exception as e:
                print("Execption in Reminder To Approve The Saving Declaration Emails to RM:",e)
                
if __name__ == "__main__":
    StatusReminder().main()

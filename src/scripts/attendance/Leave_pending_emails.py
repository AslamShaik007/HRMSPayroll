import sys
import os
import django
import pandas as pd
from django.db import models as db_models
import logging
sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from leave.models import LeavesHistory
from HRMSApp.models import CompanyDetails
from HRMSApp.utils import Util
import datetime
from core.utils import timezone_now, email_render_to_string, get_domain
from core.whatsapp import WhatsappMessage
logger = logging.getLogger('django')

class LeavePending:
            
    def date_converter(self, x):
        new_dates = []
        if x:
            new_dates.extend(obj.strftime('%d-%m-%Y') for obj in x)
        return ', '.join(new_dates) 
    
    def main(self):
        try:
            if "commit" in sys.argv:
                print("emails sending in progress")
            company_id = 1
            emp_domain = get_domain(sys.argv[-1], sys.argv[1], 'userLeaveLogsTable')
            manager_domain = get_domain(sys.argv[-1], sys.argv[1], 'adminLeaveLogs')
            current_date =timezone_now()
            company_name = CompanyDetails.objects.first().company_name

            # send leave pending details to reporting manager
            data4 = LeavesHistory.objects.filter(is_deleted=False, status=20, employee__company_id=company_id).annotate(
                                rp_name=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False),
                                                                     then=db_models.F('employee__employee__manager__user__username')),
                                                       default=db_models.Value(''), output_field=db_models.CharField()),
                                rp_mail=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False),
                                                                     then=db_models.F('employee__employee__manager__user__email')),
                                                       default=db_models.Value(''), output_field=db_models.CharField()),
                                rp_emp_number=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False),
                                                                     then=db_models.F('employee__employee__manager__work_details__employee_number')),
                                                       default=db_models.Value(''), output_field=db_models.CharField()),
                                rp_emp_phone=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False),
                                                                     then=db_models.F('employee__employee__manager__user__phone')),
                                                       default=db_models.Value(''), output_field=db_models.CharField())
                                ).values('rp_name', 'rp_mail', 'employee__user__username',
                                         'employee__work_details__department__name','employee__work_details__designation__name',
                                         'start_date','created_at','employee__user__email','rp_emp_number', 'employee__work_details__employee_number',
                                         'rp_emp_phone','employee__user__phone')
            dfr2 = pd.DataFrame(data4, columns=['rp_name', 'rp_mail', 'employee__user__username',
                                                'employee__work_details__department__name','start_date',
                                                'created_at','employee__user__email','employee__work_details__designation__name',
                                                'rp_emp_number','rp_emp_phone','employee__user__phone'])
            if not dfr2.empty:
                dfr2['status'] = dfr2.apply(lambda obj:'ok' if (obj['created_at'] + datetime.timedelta(hours=24)) <= current_date else None,axis=1)
                dfr2 = dfr2.dropna(subset=['status'])
            dfr2.reset_index(drop=True, inplace=True)
            dfr2 = dfr2.drop_duplicates(subset=['employee__user__username'])
            dfr2['combine'] = dfr2.apply(lambda obj: f"{obj['employee__user__username']}---->{obj['employee__work_details__department__name']}---->{obj['employee__work_details__designation__name']}", axis=1)
            dfr2 = dfr2.groupby('rp_mail').agg({"combine": list,
                                                "employee__user__username": 'first',
                                                "rp_name": 'first',
                                                'employee__user__email':'first',
                                                'start_date':'first',
                                                'rp_emp_number':'first',
                                                'rp_emp_phone':'first',
                                                'employee__user__phone':'first'
                                                }).reset_index()
            
            data_dict2 = dfr2.to_dict('records')
            for obj in data_dict2:
                try:
                    rep_name = obj['rp_name'].title()
                    rep_official_email = obj['rp_mail']
                    rp_emp_number = obj['rp_emp_number']
                    rp_emp_phone = obj['rp_emp_phone']
                    # tag = 'Mr' if gender == 'MALE' else('Ms' if gender == 'FEMALE' else 'Mr/Ms')
                    combine_data = obj['combine']
                    split_data = [item.split('---->') for item in combine_data]
                    name_dep_df = pd.DataFrame(split_data, columns=['Name', 'Department', 'Designation'])
                    name_dep_df1 = name_dep_df.to_dict('records')
                    if rep_official_email:
                        body = email_render_to_string(
                            template_name="mails/consolidate_email_templates/LeavePending.html",
                            context={"recds": name_dep_df1,
                                    "company_logo": '',
                                    "reporting_manager_name":rep_name,
                                    "company_name": company_name.title(),
                                    "domain":manager_domain, "tag":rp_emp_number}
                        )
                        data={
                            'subject': 'Pending Leave Approvals for Your Reportees',
                            'body': body,
                            'to_email': rep_official_email
                        }
                        if "commit" in sys.argv:
                            Util.send_email(data,is_content_html=True)
                        # manager Whatsapp notifications
                        try:
                            whatsapp_data = {
                                            'phone_number': rp_emp_phone,
                                            'subject': 'Pending Leave Approvals for Your Reportees',
                                            "body_text1":"Kindly review the request at your earliest convenience and provide the necessary updates.",
                                            'body_text2': " ",
                                            'url': f"{manager_domain}",
                                            "company_name":company_name.title()
                                            }
                            if "commit" in sys.argv:
                                WhatsappMessage.whatsapp_message(whatsapp_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to {rep_name} in leave pending emails: {e}") 
                except Exception as e:
                    print("Exception in send leave pending details to RM:",e)
               
            # send leave pending details to Employees
            emp_dfr = pd.DataFrame(data4, columns=['rp_name', 'rp_mail', 'employee__user__username',
                                    'employee__work_details__department__name','start_date','created_at','employee__user__email',
                                    'employee__work_details__employee_number','employee__user__phone'])
            emp_dfr = emp_dfr.drop_duplicates(subset=['employee__user__username'])
            if not emp_dfr.empty:
                emp_dfr['status'] = emp_dfr.apply(lambda obj:'ok' if (obj['created_at'] + datetime.timedelta(hours=24)) <= current_date else None,axis=1)
                emp_dfr = emp_dfr.dropna(subset=['status'])
            emp_data = emp_dfr.to_dict('records')
            for obj in emp_data:  
                try:
                    emp_email = obj['employee__user__email']
                    employee_name = obj['employee__user__username'].title()
                    emp_number = obj['employee__work_details__employee_number']
                    tag = emp_number if emp_number else "-"
                    start_date = obj['start_date']
                    emp_phone = obj['employee__user__phone']
                    body = f"""
    Hello {employee_name} [{tag}],
    
    We have noticed that the leave applied on {start_date}  is pending for approval from your manager.

    If there are any specific details or additional information needed to facilitate the approval, please feel free to provide them at your earliest convenience.
    
    Please refer the link for more information {emp_domain}.
    
    Thanks & Regards,
    {company_name.title()}.                 
                            
                            """
                    data={
                            'subject':'Approval Required for Leaves',
                            'body':body,
                            'to_email':emp_email
                        }
                    if "commit" in sys.argv:
                        Util.send_email(data)
                    # employee Whatsapp notifications
                    try:
                        whatsapp_data = {
                                            'phone_number': emp_phone,
                                            'subject': 'Approval Required for Leaves',
                                            "body_text1":f"We have noticed that the leave applied on {start_date}  is pending for approval from your manager",
                                            'body_text2': "Please ensure you promptly seek approval",
                                            'url': f"{emp_domain}",
                                            "company_name":company_name.title()
                                            }
                        if "commit" in sys.argv:
                            WhatsappMessage.whatsapp_message(whatsapp_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {employee_name} in leave pending emails: {e}")         
                except Exception as e:
                    print("Exception in send leave pending details to Employee:", e)
                            
                if "commit" in sys.argv: 
                    print("emails sent successfully!")  
                else:print("Dry Run!")
        except Exception as e:
            print("Overall_Exception:", e)
                      
if __name__ == "__main__":
    LeavePending().main()
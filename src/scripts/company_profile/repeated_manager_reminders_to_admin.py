import sys
import os
import django
import logging

import pandas as pd
from django.db import models as db_models
from datetime import datetime, timedelta
sys.path.append('./')

sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]
    
from HRMSApp.utils import Util
from core.utils import timezone_now, email_render_to_string, get_domain
from HRMSApp.models import Roles
from directory.models import Employee
from leave.models import LeavesHistory
from attendance.models import AnamolyHistory, EmployeeCheckInOutDetails
from company_profile.models import CompanyDetails

logger = logging.getLogger("django")
from core.whatsapp import WhatsappMessage


class RepeatedRemindersToAdmin:
    
    def __init__(self,company_id):
        self.company_id = company_id
        
        
    def main(self):
        today = timezone_now().date()
        leave_domain = get_domain(sys.argv[-1], sys.argv[1], 'adminLeaveLogs')
        att_domain = get_domain(sys.argv[-1], sys.argv[1], 'adminApproveLogs')
        yesterday = today - timedelta(days=1)
        company_name = CompanyDetails.objects.first().company_name
        admin_emails = Roles.objects.filter(name__in=["ADMIN","CEO"],roles_employees__company_id = 1,roles_employees__work_details__employee_status="Active").values(
                                                                                        "roles_employees__official_email",
                                                                                        "roles_employees__user__username",
                                                                                        "roles_employees__work_details__employee_number",
                                                                                        "roles_employees__phone")
        leaves_qs = LeavesHistory.objects.filter(is_deleted=False, status=LeavesHistory.PENDING, employee__work_details__employee_status="Active").annotate(
                            rp_mail=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False),
                                                                    then=db_models.F('employee__employee__manager__user__email')),
                                                    default=db_models.Value(''), output_field=db_models.CharField()),
                            ).values('rp_mail', 'employee__work_details__employee_number')
            
        leaves_df = pd.DataFrame(leaves_qs, columns = ['rp_mail', 'employee__work_details__employee_number'])
        # leave_clean_df = leaves_df.dropna()
        # leaves_df = leaves_df.groupby(['rp_mail']).agg({
        #                                         'rp_employee_code':'first',
        #                                         'rp_name':'first',
        #                                         'rp_department':'first',
        #                                         'employee__work_details__employee_number':lambda x: len(x.tolist()),
        #                                         }).reset_index()
        leaves_df = leaves_df.groupby(['rp_mail']).aggregate({'employee__work_details__employee_number': list}).reset_index()
        leaves_df['leaves_count'] = leaves_df.employee__work_details__employee_number.apply(lambda x: len(x))
        leaves_df = leaves_df.loc[leaves_df.rp_mail != '']
        leaves_df.drop(columns=['employee__work_details__employee_number'], inplace=True)
        anamoly_qs = EmployeeCheckInOutDetails.objects.filter(is_deleted=False, action_status = EmployeeCheckInOutDetails.PENDING, employee__work_details__employee_status="Active").annotate(
                            rp_mail=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                        then=db_models.F('employee__employee__manager__user__email')),
                                                default=db_models.Value(''), output_field=db_models.CharField()),
                            ).values('rp_mail', 'employee__work_details__employee_number')
        
        anamoly_df  =pd.DataFrame(anamoly_qs, columns = ['rp_mail','employee__work_details__employee_number'])
        anamoly_df = anamoly_df.groupby(['rp_mail']).aggregate({'employee__work_details__employee_number': list}).reset_index()
        anamoly_df['anamoly_count'] = anamoly_df.employee__work_details__employee_number.apply(lambda x: len(x))
        anamoly_df = anamoly_df.loc[anamoly_df.rp_mail != '']
        anamoly_df.drop(columns=['employee__work_details__employee_number'], inplace=True)
        
        # final_df = pd.merge(leaves_df, anamoly_df, how="inner", on='rp_mail') 
        merged_df = pd.merge(leaves_df, anamoly_df, on=['rp_mail'], how='outer')
        merged_df = merged_df.fillna('-')
        merged_df['rp_manager'] = merged_df.rp_mail.apply(lambda x: Employee.objects.get(official_email=x))
        merged_df['rp_name'] = merged_df.rp_manager.apply(lambda x: x.user.username)
        merged_df['rp_emp_id'] = merged_df.rp_manager.apply(lambda x: x.work_details.employee_number)
        merged_df['department'] = merged_df.rp_manager.apply(lambda x: x.work_details.department.name if hasattr(x.work_details.department, 'name') else '-')
        data_dict = merged_df.to_dict('records')       
        if "commit" in sys.argv and not merged_df.empty:
            print("Email Sending in progress")
            try:
                for item in admin_emails:
                    admin_email = item['roles_employees__official_email']
                    admin_name = item['roles_employees__user__username'].title()
                    admin_emp_number = item['roles_employees__work_details__employee_number']
                    admin_phone = item['roles_employees__phone']
                    admin_phone = item['roles_employees__phone']
                    tag = admin_emp_number if admin_emp_number else "-"
                    body = email_render_to_string(
                                template_name="mails/admin_mails/repeated_manager_reminders.html", context={"recds":data_dict, "company_name":company_name.title(),
                                                                                                            "admin_name":admin_name, "leave_domain":leave_domain,
                                                                                                            "attendance_domain":att_domain, "tag":tag}
                            )
                    data={
                            'subject':"Repeated Reminders to Managers",
                            'body':body,
                            'to_email':admin_email
                        }
                    Util.send_email(data,is_content_html=True)
                    print("Successfully Sent Manager Repeated Reminders!")

                    # Admin Whatsapp notifications
                    try:
                        employee_data = {
                                'phone_number': admin_phone,
                                'subject': 'Repeated Reminders to Managers',
                                'body_text1' : "Pending approval requests from employees that have not been addressed by their respective reporting managers.",
                                'body_text2' : "For leave module and attendance module ",
                                'url': f"{att_domain}",
                                "company_name": company_name
                                }
                        WhatsappMessage.whatsapp_message(employee_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {admin_name} about leave and attendence approval: {e}")
            except Exception as e:
                print(f"Exception in sending mails: {e}")
        print(f"Dry Run!")
        

if __name__ == "__main__":
    company_id = 1
    RepeatedRemindersToAdmin(company_id=company_id).main()
import sys
import os
import django
import pandas as pd
import logging

from datetime import datetime,  timedelta

from django.db import models as db_models

sys.path.append('./')

if __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from attendance.models import (
    AnamolyHistory,
    AttendanceRuleSettings
)
from leave.models import LeavesHistory
from HRMSApp.utils import Util
from HRMSApp.models import CompanyDetails
from directory.models import Employee
from core.utils import timezone_now, get_paycycle_dates, email_render_to_string, get_domain
from core.whatsapp import WhatsappMessage

logger = logging.getLogger('django')
class AnamoliePendingReport:
    
    def main(self):
        try:
            if "commit" in sys.argv:
                print("emails sending in progress")
            emp_domain = get_domain(sys.argv[-1], sys.argv[1], 'userAttendancelogs')
            manager_domain = get_domain(sys.argv[-1], sys.argv[1], 'adminApproveLogs')
            company_id = 1
            company_obj = CompanyDetails.objects.filter(id=company_id).first()
            company_logo = company_obj.company_image.url
            company_name = company_obj.company_name
            q_filter = db_models.Q(is_deleted=False, status = 20, clock__employee__work_details__employee_status="Active", clock__employee__payroll_status=True, action__isnull=False)
            
            data = AnamolyHistory.objects.filter(q_filter).annotate(
                                rp_name=db_models.Case(db_models.When(db_models.Q(clock__employee__employee__manager_type_id=1, clock__employee__employee__is_deleted=False), 
                                                            then=db_models.F('clock__employee__employee__manager__user__username')),
                                                    default=db_models.Value(''), output_field=db_models.CharField()),
                                rp_mail=db_models.Case(db_models.When(db_models.Q(clock__employee__employee__manager_type_id=1,clock__employee__employee__is_deleted=False), 
                                                            then=db_models.F('clock__employee__employee__manager__user__email')),
                                                    default=db_models.Value(''), output_field=db_models.CharField()),
                                rp_gender=db_models.Case(db_models.When(db_models.Q(clock__employee__employee__manager_type_id=1,clock__employee__employee__is_deleted=False), 
                                                            then=db_models.F('clock__employee__employee__manager__gender')),
                                                    default=db_models.Value(''), output_field=db_models.CharField()),
                                rp_emp_code=db_models.Case(db_models.When(db_models.Q(clock__employee__employee__manager_type_id=1,clock__employee__employee__is_deleted=False), 
                                                            then=db_models.F('clock__employee__employee__manager__work_details__employee_number')),
                                                    default=db_models.Value(''), output_field=db_models.CharField()),
                                rp_emp_phone=db_models.Case(db_models.When(db_models.Q(clock__employee__employee__manager_type_id=1,clock__employee__employee__is_deleted=False), 
                                                            then=db_models.F('clock__employee__employee__manager__user__phone')),
                                                    default=db_models.Value(''), output_field=db_models.CharField()),
                                ).values(
                                        'clock__employee__user__email',
                                        'clock__employee__user__username',
                                        'request_date',
                                        'clock__employee__company__consolidate_notification_date__reporting_manager_start_date__day',
                                        'clock__employee__company__consolidate_notification_date__reporting_manager_end_date__day',
                                        'rp_name', 'rp_mail','clock__employee__work_details__department__name','clock__employee__work_details__employee_number',
                                        'clock__employee__gender','rp_gender','updated_at','rp_emp_code', 'clock__employee__user__phone')
            df_data = pd.DataFrame(data,columns = ['clock__employee__user__username','clock__employee__user__email',
                                            'request_date','clock__employee__company__consolidate_notification_date__reporting_manager_start_date__day',
                                            'clock__employee__company__consolidate_notification_date__reporting_manager_end_date__day',
                                            'rp_name','rp_mail','clock__employee__work_details__department__name','clock__employee__work_details__employee_number',
                                            'clock__employee__gender','rp_gender','updated_at','rp_emp_code','clock__employee__user__phone','rp_emp_phone'])
            df_data = df_data.drop_duplicates(subset=['clock__employee__user__username'])
            # if not df_data.empty:
            #     df_data['status'] = df_data.apply(lambda obj:'ok' if (obj['updated_at'] + timedelta(hours=24)) <= timezone_now() else None,axis=1)
            #     df_data = df_data.dropna(subset=['status'])
            data_dict1 = df_data.to_dict('records')
            df_data['combine'] = df_data.apply(lambda obj: f"{obj['clock__employee__work_details__employee_number']}---->{obj['clock__employee__user__username']}---->{obj['clock__employee__work_details__department__name']}", axis=1)
            df_data = df_data.groupby('rp_mail').agg({"combine": list,
                                                'clock__employee__user__email':'first',
                                                'clock__employee__company__consolidate_notification_date__reporting_manager_start_date__day':'first',
                                                'clock__employee__company__consolidate_notification_date__reporting_manager_end_date__day':'first',
                                                'rp_name':'first',
                                                'clock__employee__work_details__department__name':'first',
                                                'clock__employee__work_details__employee_number':'first',
                                                'clock__employee__gender':'first',
                                                'rp_gender':'first',
                                                'request_date':'first',
                                                'rp_emp_code':'first',
                                                'clock__employee__user__phone':'first',
                                                'rp_emp_phone':'first',
                                                'clock__employee__user__username':'first' }).reset_index()
            
            data_dict2 = df_data.to_dict('records')
            if len(data)>0:
                for obj in data_dict1:                   
                    try:
                        employee_name = obj['clock__employee__user__username']
                        official_email = obj['clock__employee__user__email']
                        phone = obj['clock__employee__user__phone']
                        dt = obj['request_date']
                        emp_code = obj['clock__employee__work_details__employee_number']
                        body = f"""
    Hello {employee_name.title()} [{emp_code}],

    Your Anamolie is pending for approval which you have applied for the {dt.strftime('%d-%m-%Y')}

    Please connect your reporting manager for approval.

    Please refer the link for more information {emp_domain}.

    Thanks & Regards,
    {company_name.title()}.                         
"""
                        data={
                            'subject':'Approval Pending for Anamoly',
                            'body':body,
                            'to_email':official_email
                        }
                        if "commit" in sys.argv:
                            Util.send_email(data)
                    except Exception as e:
                        print("Execption in send Anamoly pending details to Employee:",e)
                        
                    # employee Whatsapp notifications
                    try:
                        whatsapp_data = {
                                'phone_number': phone,
                                'subject': 'Approval Pending for Anamoly',
                                "body_text1":"Your Anamolie is pending for approval ",
                                'body_text2': f"which you have applied for the {dt.strftime('%d-%m-%Y')}",
                                'url': f"{emp_domain}",
                                "company_name":company_name.title()
                                }
                        if "commit" in sys.argv:
                            WhatsappMessage.whatsapp_message(whatsapp_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {obj['clock__employee__user__username']} in anamoly pending report to manager: {e}") 
            if len(df_data)>0:
                for obj in data_dict2:  
                    try:
                        rep_name = obj['rp_name'].title()
                        rep_official_email = obj['rp_mail']
                        rp_emp_code = obj['rp_emp_code']
                        rp_emp_phone = obj['rp_emp_phone']
                        combine_data = obj['combine']
                        split_data = [item.split('---->') for item in combine_data]
                        dep_df = pd.DataFrame(split_data, columns=['EmpId','Name', 'Department'])
                        dep_df1 = dep_df.to_dict('records')
                        body = email_render_to_string(
                                    template_name="mails/attendance_reminders/anamolies_pending_report.html", context={"recds":dep_df1, "company_logo":company_logo, 
                                                                                                                        "company_name":company_name.title(), "reporting_manager_name":rep_name,
                                                                                                                        "domain":manager_domain, "emp_code":rp_emp_code}
                                )
                        if rep_official_email:
                            data={
                                    'subject':'Anamoly Approvals Pending for Your Reportees',
                                    'body':body,
                                    'to_email':rep_official_email
                                }
                            if "commit" in sys.argv:
                                Util.send_email(data,is_content_html=True)
                        
                    except Exception as e:
                        print("Execption in send Anamoly pending details to RM:",e)
                        
                    # manager Whatsapp notifications
                    print("rp_emp_phone:",rp_emp_phone)
                    if rp_emp_phone:
                        try:
                            whatsapp_data = {
                                    'phone_number': rp_emp_phone,
                                    'subject': 'Anamoly Approvals Pending for Your Reportees',
                                    "body_text1":"Kindly review and approve the anomalies at your earliest convenience",
                                    'body_text2': " ",
                                    'url': f"{manager_domain}",
                                    "company_name":company_name.title()
                                    }
                            if "commit" in sys.argv:
                                WhatsappMessage.whatsapp_message(whatsapp_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to {rep_name} in anamoly pending report to manager: {e}") 
                        
            if "commit" in sys.argv: 
                print("emails sent successfully!")  
            else:
                print("Dry Run!")
        except Exception as e:
            print("Overall_Exception:",e)


if __name__ == "__main__":
    AnamoliePendingReport().main()
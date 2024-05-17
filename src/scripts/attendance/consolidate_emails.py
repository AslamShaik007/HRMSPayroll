import sys
import os
import django
import pandas as pd
import logging
import traceback

from datetime import datetime, timedelta
from django.conf import settings
from django.db import models as db_models

sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from attendance.models import (
    AnamolyHistory,
    AttendanceRuleSettings,
    EmployeeCheckInOutDetails
)
from leave.models import LeavesHistory
from HRMSApp.utils import Util
from HRMSApp.models import CompanyDetails
from directory.models import Employee
from core.utils import timezone_now, get_paycycle_dates, email_render_to_string, get_domain, TimestampToStrDateTime, TimestampToIST, get_month_weeks
from core.whatsapp import WhatsappMessage
from pss_calendar.models import Holidays
logger = logging.getLogger('django')
class ConsolidateEmails:
            
    def date_converter(self,x):
        new_dates = []
        if x:
            new_dates.extend(obj.strftime('%d-%m-%Y') for obj in x)
        return ', '.join(new_dates) 
    
    def main(self):
        try:
            if "commit" in sys.argv:
                print("emails sending in progress")
            company_id = 1
            hls = Holidays.objects.filter(holiday_type=True).values_list('holiday_date',flat=True)
            emp_domain = get_domain(sys.argv[-1], sys.argv[1], 'userAttendancelogs')
            manager_domain = get_domain(sys.argv[-1], sys.argv[1], 'adminApproveLogs')
            leave_manager_domain = get_domain(sys.argv[-1], sys.argv[1], 'adminLeaveLogs')
            leave_user_domain = get_domain(sys.argv[-1], sys.argv[1], 'userLeaveLogsTable')
            current_dates =timezone_now().date()
            current_date = current_dates.day
            company_obj = CompanyDetails.objects.filter(id=company_id).first()
            company_logo = company_obj.company_image.url
            company_name = company_obj.company_name
            att_sett_data = AttendanceRuleSettings.objects.filter(company_id = company_id)
            if att_sett_data.exists():
                psc_from_date =  att_sett_data.first().attendance_input_cycle_from
                psc_to_date   =  att_sett_data.first().attendance_input_cycle_to
                
                pay_cycle_from_date,pay_cycle_to_date,current_payout_date = get_paycycle_dates(current_dates,psc_from_date,psc_to_date)
                #send attendance pending emails to employee
                # q_filter = db_models.Q(is_deleted=False, status__in = [20,30], request_date__gte = pay_cycle_from_date,
                #                        request_date__lte = pay_cycle_to_date, clock__employee__work_details__employee_status='Active', 
                #                        clock__employee__payroll_status=True, clock__employee__is_deleted=False)

                dates = [pay_cycle_from_date + timedelta(i) for i in range(((pay_cycle_to_date + timedelta(1)) - pay_cycle_from_date).days)]
                results = []
                for date in dates:
                    q_filter = db_models.Q(is_deleted=False, status__in=[20,30], request_date=date, 
                                           clock__employee__work_details__employee_status='Active', 
                                       clock__employee__payroll_status=True, clock__employee__is_deleted=False)
                    week_number = get_month_weeks(date)[date.day]
                    pp = date.strftime("%A").lower()
                    week_off_filter = {
                        "clock__employee__employeeworkrulerelation__work_rule__work_rule_choices__week_number": week_number,
                            f'clock__employee__employeeworkrulerelation__work_rule__work_rule_choices__{pp}': 2
                    }

                    anamoly_data = AnamolyHistory.objects.filter(q_filter, **week_off_filter)
                    results.append(anamoly_data.first().id) if anamoly_data.exists() else None
                
                data2 = AnamolyHistory.objects.filter(id__in=results).values(
                                                                'clock__employee__user__email',
                                                                'clock__employee__user__username',
                                                                'request_date',
                                                                'clock__employee__company__consolidate_notification_date__employee_start_date__day',
                                                                'clock__employee__company__consolidate_notification_date__employee_end_date__day',
                                                                'clock__employee__gender', 'clock__employee__work_details__employee_number',
                                                                'clock__employee__user__phone'
                                                                )
                dfr = pd.DataFrame(data2,columns = ['clock__employee__user__username','clock__employee__user__email',
                                                'request_date','clock__employee__company__consolidate_notification_date__employee_start_date__day',
                                                'clock__employee__company__consolidate_notification_date__employee_end_date__day','clock__employee__gender',
                                                'clock__employee__work_details__employee_number','clock__employee__user__phone'])
                
                dfr = dfr.groupby('clock__employee__user__username').agg({'clock__employee__user__email':'first',
                                                                    'clock__employee__company__consolidate_notification_date__employee_start_date__day':'first',
                                                                    'clock__employee__company__consolidate_notification_date__employee_end_date__day':'first',
                                                                    'clock__employee__gender':'first',
                                                                    'clock__employee__work_details__employee_number':'first',
                                                                    'clock__employee__user__phone':'first',
                                                                    'request_date':list}).reset_index()
                data_dict = dfr.to_dict('records')
                
                for obj in data_dict:  
                    # dts = sorted([d.strftime('%d-%m-%Y') for d in set(obj['request_date'])])        
                    try:
                        employee_name = obj['clock__employee__user__username']
                        official_email = obj['clock__employee__user__email']
                        # request_dates = list(set(obj['request_date']))
                        employee_start_date = obj['clock__employee__company__consolidate_notification_date__employee_start_date__day']
                        employee_end_date = obj['clock__employee__company__consolidate_notification_date__employee_end_date__day']
                        # converted_dates = self.date_converter(request_dates)
                        emp_code =  obj['clock__employee__work_details__employee_number']
                        emp_phone = obj['clock__employee__user__phone']
                        if employee_start_date <= current_date <= employee_end_date:
                            body = f"""
    Hello {employee_name.title()} [{emp_code}],

    We have identified anomalies in your attendance records for the dates, Which require approval from your manager.

    Please ensure you promptly seek approval, as pending or rejected anomalies may lead to penalty actions.
    
    Please refer the link for more information {emp_domain}.
    
    Thanks & Regards,
    {company_name.title()}.                         
                            
                            """
                            data={
                                    'subject':'Approval Required for Anomalies',
                                    'body':body,
                                    'to_email':official_email
                                }
                            if "commit" in sys.argv:
                                Util.send_email(data)
                    except Exception as e:
                        logger.warning(f"Execption in send Anamoly pending details to Employee {e}")
                    
                    # employee Whatsapp notifications
                    if emp_phone and (employee_start_date <= current_date <= employee_end_date):
                        try:
                            whatsapp_data = {
                                    'phone_number': emp_phone,
                                    'subject': 'Approval Required for Anomalies',
                                    "body_text1":f"Your Anamolie is pending for approval",
                                    'body_text2': "Please ensure you promptly seek approval",
                                    'url': f"{emp_domain}",
                                    "company_name":company_name.title()
                                    }
                            if "commit" in sys.argv:
                                WhatsappMessage.whatsapp_message(whatsapp_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to {rep_name} in anamoly pending report to employee: {e}") 
                            
                #send attendance pending emails to reporting manager
                q1_filter = db_models.Q(is_deleted=False, status = 30, request_date__gte = pay_cycle_from_date,
                                        request_date__lte = pay_cycle_to_date,clock__employee__work_details__employee_status='Active', 
                                       clock__employee__payroll_status=True, clock__employee__is_deleted=False)

                data3 = AnamolyHistory.objects.filter(q1_filter).annotate(
                                    rp_name=db_models.Case(db_models.When(db_models.Q(clock__employee__employee__manager_type_id=1, clock__employee__employee__is_deleted=False), 
                                                                then=db_models.F('clock__employee__employee__manager__user__username')),
                                                        default=db_models.Value(''), output_field=db_models.CharField()),
                                    rp_mail=db_models.Case(db_models.When(db_models.Q(clock__employee__employee__manager_type_id=1, clock__employee__employee__is_deleted=False), 
                                                                then=db_models.F('clock__employee__employee__manager__user__email')),
                                                        default=db_models.Value(''), output_field=db_models.CharField()),
                                    rp_gender=db_models.Case(db_models.When(db_models.Q(clock__employee__employee__manager_type_id=1, clock__employee__employee__is_deleted=False), 
                                                                then=db_models.F('clock__employee__employee__manager__gender')),
                                                        default=db_models.Value(''), output_field=db_models.CharField()),
                                    rp_emp_code=db_models.Case(db_models.When(db_models.Q(clock__employee__employee__manager_type_id=1, clock__employee__employee__is_deleted=False), 
                                                                then=db_models.F('clock__employee__employee__manager__work_details__employee_number')),
                                                        default=db_models.Value(''), output_field=db_models.CharField()),
                                    rp_emp_phone=db_models.Case(db_models.When(db_models.Q(clock__employee__employee__manager_type_id=1, clock__employee__employee__is_deleted=False), 
                                                                then=db_models.F('clock__employee__employee__manager__user__phone')),
                                                        default=db_models.Value(''), output_field=db_models.CharField())
                                    ).values(
                                            'clock__employee__user__email',
                                            'clock__employee__user__username',
                                            'request_date',
                                            'clock__employee__company__consolidate_notification_date__reporting_manager_start_date__day',
                                            'clock__employee__company__consolidate_notification_date__reporting_manager_end_date__day',
                                            'rp_name', 'rp_mail','clock__employee__work_details__department__name','rp_gender','rp_emp_code','rp_emp_phone')
                dfr1 = pd.DataFrame(data3,columns = ['clock__employee__user__username','clock__employee__user__email',
                                                'request_date','clock__employee__company__consolidate_notification_date__reporting_manager_start_date__day',
                                                'clock__employee__company__consolidate_notification_date__reporting_manager_end_date__day',
                                                'rp_name','rp_mail','clock__employee__work_details__department__name','rp_gender','rp_emp_code','rp_emp_phone'])
                dfr1 = dfr1.drop_duplicates(subset=['clock__employee__user__username'])
                dfr1['combine'] = dfr1.apply(lambda obj: f"{obj['clock__employee__user__username']}---->{obj['clock__employee__work_details__department__name']}", axis=1)
                dfr1 = dfr1.groupby('rp_mail').agg({"combine": list,
                                                    'clock__employee__user__email':'first',
                                                    'clock__employee__company__consolidate_notification_date__reporting_manager_start_date__day':'first',
                                                    'clock__employee__company__consolidate_notification_date__reporting_manager_end_date__day':'first',
                                                    'rp_name':'first',
                                                    'clock__employee__work_details__department__name':'first',
                                                    'rp_gender':'first',
                                                    'rp_emp_code':'first',
                                                    'rp_emp_phone':'first',
                                                    'clock__employee__user__username':'first' }).reset_index()
                
                data_dict1 = dfr1.to_dict('records')
                for obj in data_dict1:                    
                    try:
                        reporting_manager_start_date = obj['clock__employee__company__consolidate_notification_date__reporting_manager_start_date__day']
                        reporting_manager_end_date = obj['clock__employee__company__consolidate_notification_date__reporting_manager_end_date__day']
                        # emp_count = len(obj['clock__employee__user__username'])
                        # empls_names = ', '.join(obj['clock__employee__user__username'])
                        rep_name = obj['rp_name'].title()
                        rep_official_email = obj['rp_mail']
                        emp_code = obj['rp_emp_code'] 
                        rp_emp_phone = obj['rp_emp_phone']
                        combine_data = obj['combine']
                        split_data = [item.split('---->') for item in combine_data]
                        dep_df = pd.DataFrame(split_data, columns=['Name', 'Department'])
                        dep_df1 = dep_df.to_dict('records')
                        body = email_render_to_string(
                                    template_name="mails/consolidate_email_templates/AnamolyTemplate.html", context={"recds":dep_df1, "company_logo":company_logo, 
                                                                                                                     "company_name":company_name.title(),"domain":manager_domain,
                                                                                                                     'manager_name':rep_name,"emp_code":emp_code}
                                )
                        if rep_official_email and reporting_manager_start_date <= current_date <= reporting_manager_end_date:
                            data={
                                    'subject':'Pending Anomalies Approvals for Your Reportees',
                                    'body':body,
                                    'to_email':rep_official_email
                                }
                            if "commit" in sys.argv:
                                Util.send_email(data,is_content_html=True)
                        # manager Whatsapp notifications
                        if rp_emp_phone and reporting_manager_start_date <= current_date <= reporting_manager_end_date:
                            try:
                                whatsapp_data = {
                                        'phone_number': rp_emp_phone,
                                        'subject': 'Pending Anomalies Approvals for Your Reportees',
                                        "body_text1":"Kindly review and approve the anomalies at your earliest convenience",
                                        'body_text2': " ",
                                        'url': f"{manager_domain}",
                                        "company_name":company_name.title()
                                        }
                                if "commit" in sys.argv:
                                    WhatsappMessage.whatsapp_message(whatsapp_data)
                            except Exception as e:
                                logger.warning(f"Error while sending Whatsapp notificaton to {rep_name} in anamoly pending report to manager: {e}") 
                    except Exception as e:
                        print("Execption in send Anamoly pending details to RM:",e)

                    
                # send attendance pending details to HR manager
                att_pending_data = data3.values('clock__employee__user__username','clock__employee__company__consolidate_notification_date__hr_manager_start_date__day',
                                        'clock__employee__company__consolidate_notification_date__hr_manager_end_date__day','clock__employee__work_details__department__name')
                
                dfr4 = pd.DataFrame(att_pending_data,columns = ['clock__employee__user__username',
                                    'clock__employee__company__consolidate_notification_date__hr_manager_start_date__day',
                                    'clock__employee__company__consolidate_notification_date__hr_manager_end_date__day',
                                    'clock__employee__work_details__department__name'])
                dfr4 = dfr4.drop_duplicates(subset=['clock__employee__user__username'])
                hr_admin = Employee.objects.filter(roles__name = 'HR',work_details__employee_status='Active',payroll_status=True, is_deleted=False)
                
                if not dfr4.empty:
                    hr_manager_start_date = dfr4.at[0, 'clock__employee__company__consolidate_notification_date__hr_manager_start_date__day']
                    hr_manager_end_date = dfr4.at[0, 'clock__employee__company__consolidate_notification_date__hr_manager_end_date__day']    
                    if not dfr4.empty and hr_admin.exists() and hr_manager_start_date <= current_date <= hr_manager_end_date:
                        for hr_obj in hr_admin:
                            try:
                                # employees_names = dfr3['clock__employee__user__username'].str.cat(sep=' ')
                                dfr4 = dfr4.rename(
                                        columns = {'clock__employee__user__username':'Name','clock__employee__work_details__department__name':'Department'})
                                dfr4_data = dfr4.to_dict('records')
                                hr_name = hr_obj.user.username.title()
                                hr_mail = hr_obj.user.email
                                emp_code = hr_obj.work_details.employee_number
                                body = email_render_to_string(
                                        template_name="mails/consolidate_email_templates/AnamolyTemplate.html", context={"recds":dfr4_data, "company_logo":company_logo, 
                                                                                                                        "company_name":company_name.title(),"manager_name":hr_name,
                                                                                                                        "domain":manager_domain,"emp_code":emp_code}
                                    )
                                data={
                                        'subject':'Pending Anomalies Approvals for Your Reportees',
                                        'body':body,
                                        'to_email':hr_mail
                                    }
                                if "commit" in sys.argv:
                                    Util.send_email(data,is_content_html=True)
                                
                            except Exception as e:
                                print("Execption in send Anamoly pending details to HR:",e)

                            # HR Whatsapp notifications
                            if hr_obj.user.phone:
                                try:
                                    whatsapp_data = {
                                            'phone_number': hr_obj.user.phone,
                                            'subject': 'Pending Anomalies Approvals for Your Reportees',
                                            "body_text1":"Kindly review and approve the anomalies at your earliest convenience",
                                            'body_text2': " ",
                                            'url': f"{manager_domain}",
                                            "company_name":company_name.title()
                                            }
                                    if "commit" in sys.argv:
                                        WhatsappMessage.whatsapp_message(whatsapp_data)
                                except Exception as e:
                                    logger.warning(f"Error while sending Whatsapp notificaton to {hr_obj.user.username} in anamoly pending report to HR: {e}")
                # send leave pending details to reporting manager
                leave_filter = db_models.Q(is_deleted=False, status=20, employee__company_id=company_id, 
                                           start_date__gte = pay_cycle_from_date,end_date__lte = pay_cycle_to_date,
                                           employee__work_details__employee_status='Active', employee__payroll_status=True, 
                                           employee__is_deleted=False)
                data4 = LeavesHistory.objects.filter(leave_filter).annotate(
                                    rp_name=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                                then=db_models.F('employee__employee__manager__user__username')),
                                                        default=db_models.Value(''), output_field=db_models.CharField()),
                                    rp_mail=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                                then=db_models.F('employee__employee__manager__user__email')),
                                                        default=db_models.Value(''), output_field=db_models.CharField()),
                                    rp_gender=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                                then=db_models.F('employee__employee__manager__gender')),
                                                        default=db_models.Value(''), output_field=db_models.CharField()),
                                    rp_emp_code=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                                then=db_models.F('employee__employee__manager__work_details__employee_number')),
                                                        default=db_models.Value(''), output_field=db_models.CharField()),
                                    rp_emp_phone=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                                then=db_models.F('employee__employee__manager__user__phone')),
                                                        default=db_models.Value(''), output_field=db_models.CharField())
                                    ).values('rp_name','rp_mail','employee__user__username',
                                                'employee__company__consolidate_notification_date__reporting_manager_start_date__day',
                                                'employee__company__consolidate_notification_date__reporting_manager_end_date__day',
                                                'employee__work_details__department__name','rp_gender','rp_emp_code','rp_emp_phone','employee__user__phone')
            
                dfr2 = pd.DataFrame(data4,columns = ['rp_name','rp_mail','employee__user__username',
                                                'employee__company__consolidate_notification_date__reporting_manager_start_date__day',
                                                'employee__company__consolidate_notification_date__reporting_manager_end_date__day',
                                                'employee__work_details__department__name','rp_gender','rp_emp_code','rp_emp_phone','employee__user__phone'])
                dfr2.reset_index(drop=True, inplace=True)
                dfr2 = dfr2.drop_duplicates(subset=['employee__user__username'])
                dfr2['combine'] = dfr2.apply(lambda obj: f"{obj['employee__user__username']}---->{obj['employee__work_details__department__name']}", axis=1)
                dfr2 = dfr2.groupby('rp_mail').agg({"combine": list,
                                                   "employee__company__consolidate_notification_date__reporting_manager_start_date__day":'first',
                                                   "employee__company__consolidate_notification_date__reporting_manager_end_date__day":"first",
                                                   "employee__user__username":'first',
                                                   "rp_name":'first',
                                                   "rp_gender":'first',
                                                   'rp_emp_code':'first',
                                                   'rp_emp_phone':'first',
                                                    'employee__user__phone':'first'
                                                   }).reset_index()

                data_dict2 = dfr2.to_dict('records')
                for obj in data_dict2:                    
                    try:
                        reporting_manager_start_date = obj['employee__company__consolidate_notification_date__reporting_manager_start_date__day']
                        reporting_manager_end_date = obj['employee__company__consolidate_notification_date__reporting_manager_end_date__day']
                        rep_name = obj['rp_name'].title()
                        rep_official_email = obj['rp_mail']
                        emp_code = obj['rp_emp_code']
                        rp_emp_phone = obj['rp_emp_phone']
                        if rep_official_email and reporting_manager_start_date <= current_date <= reporting_manager_end_date:
                            combine_data = obj['combine']
                            split_data = [item.split('---->') for item in combine_data]
                            name_dep_df = pd.DataFrame(split_data, columns=['Name', 'Department'])
                            name_dep_df1 = name_dep_df.to_dict('records')
                            body = email_render_to_string(
                                        template_name="mails/consolidate_email_templates/LeaveTemplate.html", context={"recds":name_dep_df1, 
                                                                                                                       "company_logo":company_logo,
                                                                                                                       "company_name":company_name.title(),
                                                                                                                       "domain":leave_manager_domain,
                                                                                                                       "manager_name":rep_name,
                                                                                                                       "emp_code":emp_code}
                                    )
                            data={
                                    'subject':'Pending Leave Approvals for Your Reportees',
                                    'body':body,
                                    'to_email':rep_official_email
                                }
                            if "commit" in sys.argv:
                                Util.send_email(data,is_content_html=True)
                            
                        # manager Whatsapp notifications
                        if rp_emp_phone and reporting_manager_start_date <= current_date <= reporting_manager_end_date:
                            try:
                                whatsapp_data = {
                                        'phone_number': rp_emp_phone,
                                        'subject': 'Pending Leave Approvals for Your Reportees',
                                        "body_text1":"Kindly review the request at your earliest convenience and provide the necessary updates.",
                                        'body_text2': " ",
                                        'url': f"{leave_manager_domain}",
                                        "company_name":company_name.title()
                                        }
                                if "commit" in sys.argv:
                                    WhatsappMessage.whatsapp_message(whatsapp_data)
                            except Exception as e:
                                logger.warning(f"Error while sending Whatsapp notificaton to {rep_name} in leave pending report to manager: {e}")       
                                
                    except Exception as e:
                        print("Execption in send leave pending details to RM:",e)  
                        

                # send leave pending details to HR manager
                leave_data = data4.values(
                    'employee__company__consolidate_notification_date__hr_manager_start_date__day',
                    'employee__company__consolidate_notification_date__hr_manager_end_date__day',
                    'employee__user__username','employee__work_details__department__name')
                dfr3 = pd.DataFrame(leave_data,columns = ['employee__user__username',
                                'employee__company__consolidate_notification_date__hr_manager_start_date__day',
                                'employee__company__consolidate_notification_date__hr_manager_end_date__day',
                                'employee__work_details__department__name'])
                dfr3.reset_index(drop=True, inplace=True)
                dfr3 = dfr3.drop_duplicates(subset=['employee__user__username'])
                hr_admin = Employee.objects.filter(roles__name='HR', work_details__employee_status='Active', payroll_status=True, is_deleted=False)
                if not dfr3.empty :
                    emp_data = dfr3[['employee__user__username', 'employee__work_details__department__name']]
                    emp_data = emp_data.rename(
                        columns = {'employee__user__username':'Name','employee__work_details__department__name':'Department'})
                    
                    hr_manager_start_date = dfr3.at[0, 'employee__company__consolidate_notification_date__hr_manager_start_date__day']
                    hr_manager_end_date = dfr3.at[0, 'employee__company__consolidate_notification_date__hr_manager_end_date__day']
                    if hr_admin.exists() and hr_manager_start_date <= current_date <= hr_manager_end_date:
                        for hr_obj in hr_admin:
                            try:
                                hr_name = hr_obj.user.username.title()
                                hr_mail = hr_obj.user.email  
                                emp_code = hr_obj.work_details.employee_number
                                recds = emp_data.to_dict('records')
                                body = email_render_to_string(
                                            template_name="mails/consolidate_email_templates/LeaveTemplate.html", context={
                                                                                                                        "recds":recds, "company_logo":company_logo, 
                                                                                                                        "company_name":company_name.title(), "domain":leave_manager_domain,
                                                                                                                        "manager_name":hr_name, "emp_code":emp_code}
                                        )
                                data={
                                        'subject':'Pending Leave Approvals for Your Reportees',
                                        'body':body,
                                        'to_email':hr_mail
                                    }
                                if "commit" in sys.argv:
                                    Util.send_email(data,is_content_html=True)
                                    
                            except Exception as e:
                                print("Execption in send leave pending details to HR:",e)
                            # HR Whatsapp notifications
                            if hr_obj.user.phone:
                                try:
                                    whatsapp_data = {
                                            'phone_number': hr_obj.user.phone,
                                            'subject': 'Pending Leave Approvals for Your Reportees',
                                            "body_text1":"Kindly review the request at your earliest convenience and provide the necessary updates.",
                                            'body_text2': " ",
                                            'url': f"{leave_manager_domain}",
                                            "company_name":company_name.title()
                                            }
                                    if "commit" in sys.argv:
                                        WhatsappMessage.whatsapp_message(whatsapp_data)
                                except Exception as e:
                                    logger.warning(f"Error while sending Whatsapp notificaton to {hr_obj.user.username} in leave pending report to HR: {e}")
                # send leave pending details to Employees
                emp_leave_data = data4.values('employee__user__username','employee__user__email',
                                          'employee__company__consolidate_notification_date__employee_start_date__day',
                                          'employee__company__consolidate_notification_date__employee_end_date__day','employee__gender',
                                          'employee__work_details__employee_number', 'employee__user__phone')
                emp_leave_df = pd.DataFrame(emp_leave_data,columns = ['employee__user__username','employee__user__email',
                                                            'employee__company__consolidate_notification_date__employee_start_date__day',
                                                            'employee__company__consolidate_notification_date__employee_end_date__day','employee__gender',
                                                            'employee__work_details__employee_number', 'employee__user__phone'])
                
                emp_leave_df = emp_leave_df.drop_duplicates(subset=['employee__user__username'])
                if not emp_leave_df.empty :
                    data_dict3 = emp_leave_df.to_dict('records')
                    for obj in data_dict3: 
                        employee_start_date = obj['employee__company__consolidate_notification_date__employee_start_date__day']
                        employee_end_date = obj['employee__company__consolidate_notification_date__employee_end_date__day']  
                        if employee_start_date <= current_date <= employee_end_date:             
                            try:
                                emp_email = obj['employee__user__email']
                                employee_name = obj['employee__user__username'].title()
                                emp_code = obj['employee__work_details__employee_number']
                                body = f"""
    Hello {employee_name} [{emp_code}],

    We have identified your leave request in pending status for the currect month, which require approval from your manager.

    Please ensure you promptly seek approval, as pending or rejected Leaves may lead to LOP Day.

    Please refer the link for more information {leave_user_domain}.
    
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
                                
                            except Exception as e:
                                print("Execption in send leave pending details to Employee:",e)
                                
                            # employee Whatsapp notifications
                            if obj['employee__user__phone']:
                                try:
                                    whatsapp_data = {
                                            'phone_number': obj['employee__user__phone'],
                                            'subject': 'Approval Required for Leaves',
                                            "body_text1":"We have identified your leave request in pending status for the currect month",
                                            'body_text2': "Please ensure you promptly seek approval",
                                            'url': f"{leave_user_domain}",
                                            "company_name":company_name.title()
                                            }
                                    if "commit" in sys.argv:
                                        WhatsappMessage.whatsapp_message(whatsapp_data)
                                except Exception as e:
                                    logger.warning(f"Error while sending Whatsapp notificaton to {obj['employee__user__phone']} in anamoly pending report to employee: {e}") 
                #comp off emails to employees
                emp_comp_filter = db_models.Q(is_deleted=False, action_status=50, action__isnull=True, 
                                              compoff_added__isnull=False, employee__company_id=company_id, status='A',
                                              date_of_checked_in__gte = pay_cycle_from_date,
                                            date_of_checked_in__lte = pay_cycle_to_date,)
                emp_comp_off_records = EmployeeCheckInOutDetails.objects.filter(emp_comp_filter).values('employee__user__username','employee__work_details__employee_number',
                                                                                                        'employee__company__consolidate_notification_date__employee_start_date__day',
                                                                                                        'employee__company__consolidate_notification_date__employee_end_date__day',
                                                                                                        'employee__user__email','employee__user__phone')
                emp_comp_off_records = emp_comp_off_records.exclude(date_of_checked_in__in=hls)
                emp_comp_off_df = pd.DataFrame(emp_comp_off_records,columns = ['employee__user__username','employee__work_details__employee_number',
                                                                               'employee__user__email','employee__user__phone',
                                                                                'employee__company__consolidate_notification_date__employee_start_date__day',
                                                                                'employee__company__consolidate_notification_date__employee_end_date__day'])
                emp_comp_off_df = emp_comp_off_df.drop_duplicates(subset=['employee__user__username'])
                if not emp_comp_off_df.empty :
                    data_dict4 = emp_comp_off_df.to_dict('records')
                    for obj in data_dict4: 
                        employee_start_date = obj['employee__company__consolidate_notification_date__employee_start_date__day']
                        employee_end_date = obj['employee__company__consolidate_notification_date__employee_end_date__day']
                        if employee_start_date <= current_date <= employee_end_date:             
                            try:
                                emp_email = obj['employee__user__email']
                                employee_name = obj['employee__user__username'].title()
                                emp_code = obj['employee__work_details__employee_number']
                                body = f"""
    Hello {employee_name} [{emp_code}],

    We have identified your Comp Off request in pending status for the currect month, We kindly request that you promptly submit a request.

    Timely submission is crucial to ensure efficient processing and scheduling.

    Please refer the link for more information {emp_domain}.
    
    Thanks & Regards,
    {company_name.title()}.                        
                            
                            """
                                data={
                                    'subject':'Please Raise a Comp Off Request',
                                    'body':body,
                                    'to_email':emp_email
                                }
                                if "commit" in sys.argv:
                                    Util.send_email(data)
                                
                            except Exception as e:
                                print("Execption in send leave pending details to Employee:",e)
                            
                            # employee Whatsapp notifications
                            if obj['employee__user__phone']:
                                try:
                                    whatsapp_data = {
                                            'phone_number': obj['employee__user__phone'],
                                            'subject': 'Please Raise a Comp Off Request',
                                            "body_text1":"We have identified your Comp Off request in pending status for the currect month",
                                            'body_text2': "Please ensure you promptly seek approval",
                                            'url': f"{emp_domain}",
                                            "company_name":company_name.title()
                                            }
                                    if "commit" in sys.argv:
                                        WhatsappMessage.whatsapp_message(whatsapp_data)
                                except Exception as e:
                                    logger.warning(f"Error while sending Whatsapp notificaton to {obj['employee__user__phone']} in anamoly pending report to employee: {e}") 
                #comp off emails to Managers
                man_comp_filter = db_models.Q(is_deleted=False, action_status=20, action=50, employee__company_id=company_id, 
                                              date_of_checked_in__gte = pay_cycle_from_date,
                                            date_of_checked_in__lte = pay_cycle_to_date,)
                man_comp_off_records = EmployeeCheckInOutDetails.objects.filter(man_comp_filter).annotate(
                                                        rp_name=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                                                    then=db_models.F('employee__employee__manager__user__username')),
                                                                            default=db_models.Value(''), output_field=db_models.CharField()),
                                                        rp_mail=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                                                    then=db_models.F('employee__employee__manager__user__email')),
                                                                            default=db_models.Value(''), output_field=db_models.CharField()),
                                                        rp_emp_code=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                                                    then=db_models.F('employee__employee__manager__work_details__employee_number')),
                                                                            default=db_models.Value(''), output_field=db_models.CharField()),
                                                        rp_emp_phone=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1, employee__employee__is_deleted=False), 
                                                                                    then=db_models.F('employee__employee__manager__user__phone')),
                                                                            default=db_models.Value(''), output_field=db_models.CharField()),
                                                        date_of_checkedin = TimestampToStrDateTime(TimestampToIST(db_models.F('created_at'), settings.TIME_ZONE)),
                                                ).values('employee__user__username','employee__work_details__employee_number',
                                                        'employee__company__consolidate_notification_date__reporting_manager_start_date__day',
                                                         'employee__company__consolidate_notification_date__reporting_manager_end_date__day',
                                                         'rp_name','rp_mail','rp_emp_code','employee__work_details__department__name','date_of_checkedin','rp_emp_phone')
                man_comp_off_records = man_comp_off_records.exclude(date_of_checked_in__in=hls)
                man_comp_off = pd.DataFrame(man_comp_off_records,columns = ['employee__user__username','employee__work_details__employee_number',
                                                        'employee__company__consolidate_notification_date__reporting_manager_start_date__day',
                                                         'employee__company__consolidate_notification_date__reporting_manager_end_date__day',
                                                         'rp_name','rp_mail','rp_emp_code','date_of_checkedin','employee__work_details__department__name','rp_emp_phone'])
                man_comp_off.reset_index(drop=True, inplace=True)
                man_comp_off = man_comp_off.drop_duplicates(subset=['employee__user__username'])
                man_comp_off['combine'] = man_comp_off.apply(lambda obj: f"{obj['employee__user__username']}---->{obj['employee__work_details__department__name']}---->{obj['date_of_checkedin']}", axis=1)
                man_comp_off = man_comp_off.groupby('rp_mail').agg({"combine": list,
                                                   "employee__company__consolidate_notification_date__reporting_manager_start_date__day":'first',
                                                   "employee__company__consolidate_notification_date__reporting_manager_end_date__day":"first",
                                                   "rp_name":'first',
                                                   'rp_emp_code':'first',
                                                   'rp_emp_phone':'first',
                                                   'employee__work_details__employee_number':'first',
                                                   }).reset_index()

                man_comp_off_dict = man_comp_off.to_dict('records')
                for obj in man_comp_off_dict:                    
                    try:
                        reporting_manager_start_date = obj['employee__company__consolidate_notification_date__reporting_manager_start_date__day']
                        reporting_manager_end_date = obj['employee__company__consolidate_notification_date__reporting_manager_end_date__day']
                        rep_name = obj['rp_name'].title()
                        rep_official_email = obj['rp_mail']
                        rp_emp_code = obj['rp_emp_code']
                        rp_emp_phone = obj['rp_emp_phone']
                        if rep_official_email and reporting_manager_start_date <= current_date <= reporting_manager_end_date:
                            combine_data = obj['combine']
                            split_data = [item.split('---->') for item in combine_data]
                            name_dep_df = pd.DataFrame(split_data, columns=['Name', 'Department','Date'])
                            name_dep_df1 = name_dep_df.to_dict('records')
                            body = email_render_to_string(
                                        template_name="mails/consolidate_email_templates/CompOffTemplate.html", context={"recds":name_dep_df1, 
                                                                                                                       "company_logo":company_logo,
                                                                                                                       "company_name":company_name.title(),
                                                                                                                       "domain":manager_domain,
                                                                                                                       "manager_name":rep_name,
                                                                                                                       "rp_emp_code":rp_emp_code}
                                    )
                            data={
                                    'subject':'Pending Comp Off Approvals for Your Reportees',
                                    'body':body,
                                    'to_email':rep_official_email
                                }
                            if "commit" in sys.argv:
                                Util.send_email(data,is_content_html=True)
                                
                        # manager Whatsapp notifications
                        if rp_emp_phone and reporting_manager_start_date <= current_date <= reporting_manager_end_date:
                            try:
                                whatsapp_data = {
                                        'phone_number': rp_emp_phone,
                                        'subject': 'Pending Comp Off Approvals for Your Reportees',
                                        "body_text1":"Kindly review the request at your earliest convenience and provide the necessary updates.",
                                        'body_text2': " ",
                                        'url': f"{manager_domain}",
                                        "company_name":company_name.title()
                                        }
                                if "commit" in sys.argv:
                                    WhatsappMessage.whatsapp_message(whatsapp_data)
                            except Exception as e:
                                logger.warning(f"Error while sending Whatsapp notificaton to {obj['employee__user__username']} in anamoly pending report to manager: {e}")     
                                
                    except Exception as e:
                        print("Execption in send leave pending details to RM:",e)
                
                if "commit" in sys.argv: 
                    print("emails sent successfully!")  
                else:
                    print("Dry Run!")
        except Exception as e:
            logger.warning(f"Final Exception in Consolidate emials, error:{e}, location: {traceback.format_exc()}")
            
        
            
if __name__ == "__main__":
    ConsolidateEmails().main()
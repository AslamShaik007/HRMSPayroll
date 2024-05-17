import sys
import os
import django
import pandas as pd
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('django')


sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from django.db import models as db_models
from django.conf import settings

from core.utils import timezone_now, get_domain, get_month_weeks
from HRMSApp.utils import Util
from attendance import models as attendance_models
from directory import models as directory_models
from leave import models as leave_models
from pss_calendar import models as pss_calendar_models
from core.whatsapp import WhatsappMessage



def custom_is_day_type(week_number, work_type, dt_input, employee):
    work_rule_choice_obj = employee.employeeworkrulerelation_set.first()
    if not hasattr(employee.employeeworkrulerelation_set.first(), 'work_rule'):
        return False
    work_rule_choice_obj = work_rule_choice_obj.work_rule.work_rule_choices.filter(
        week_number=week_number)
    if not work_rule_choice_obj.exists():
        return False
    work_rule_choice_obj = work_rule_choice_obj.first()
    day = dt_input.strftime("%A")
    if day.lower() not in [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]:
        raise ValueError("Invalid day of the week")
    return getattr(work_rule_choice_obj, day.lower()) == work_type

class EmpCheckinData:
    
    def main(self, late_check_inattendance_rules):
        domain = get_domain(sys.argv[-1], sys.argv[1], 'userAttendancelogs')
        emps = directory_models.Employee.objects.filter(
            work_details__employee_status='Active',
            assignedattendancerules__attendance_rule__id__in=list(late_check_inattendance_rules.values_list('id', flat=True))
        ).exclude(
            id__in=list(
                attendance_models.EmployeeCheckInOutDetails.objects.filter(
                    date_of_checked_in=timezone_now().date(),
                ).values_list('employee_id', flat=True)
            )
        )
        # Check Emps Contain Leaves Or Not
        # Check Is that weekend or holyday
        leave_taken_emps = leave_models.LeavesHistory.objects.filter(employee__in=emps, start_date__lte=timezone_now().date(), 
                                                                     end_date__gte=timezone_now().date(), status__in=[10,20])
        emps = emps.exclude(id__in=list(leave_taken_emps.values_list('employee_id', flat=True)))

        for emp in emps:
            week_number = get_month_weeks(timezone_now().date())[timezone_now().date().day]
            week_off = custom_is_day_type(week_number, 0, timezone_now().date(), emp)
            check_in_notify_check_obj, is_created = directory_models.LateCheckInOutReminderCheck.objects.get_or_create(employee=emp, date_of_check_in=timezone_now().date())
            emp_code = emp.work_details.employee_number
            manager = emp.employee.filter(manager_type__manager_type=10,manager__work_details__employee_status='Active').first()
            if not week_off and not check_in_notify_check_obj.is_late_check_in_reminder_sent:
                if manager:
                    manager_email = manager.manager.official_email
                    try:
                        body = f'''
        Hello {emp.user.username.title()} [{emp_code}],
        
        It seems you might have forgotten to check in on the HRMS application for today. 
        
        Please take a moment to log in and complete your check-in to ensure accurate attendance records.
        
        If you encounter any issues or have questions, feel free to reach out to the HR department for assistance.
        
        Thank you for your cooperation.
        
        Please refer the link for more information {domain}.

        Thanks & Regards,
        {emp.company.company_name.title()}.  
            '''
                        data = {
                            "subject": "Gentle Reminder: HRMS Check-In for Today",
                            "body": body,
                            "to_email": emp.official_email,
                            "cc" : [manager_email]
                        }
                        if "commit" in sys.argv:
                            Util.send_email(data)
                    except Exception as e:
                        logger.warning(f"Error while sending Email notificaton to {emp.user.username} in forgot checkin employee: {e}") 
                    
                # employee Whatsapp notifications
                try:
                    whatsapp_data = {
                            'phone_number': emp.user.phone,
                            'subject': "Gentle Reminder: HRMS Check-In for Today",
                            "body_text1":"It seems you might have forgotten to check in on the HRMS application for today",
                            'body_text2': "Please take a moment to log in and complete your check-in to ensure accurate attendance records",
                            'url': f"{domain}",
                            "company_name":emp.company.company_name.title()
                            }
                    if "commit" in sys.argv:
                        WhatsappMessage.whatsapp_message(whatsapp_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to {emp.user.username} in forgot checkin employee: {e}") 
            if "commit" in sys.argv:
                check_in_notify_check_obj.is_late_check_in_reminder_sent = True
                check_in_notify_check_obj.save()
class EmplCheckOutData:
    
    def main(self, attendance_rule):
        domain = get_domain(sys.argv[-1], sys.argv[1], 'userAttendancelogs')
        
        emp = directory_models.Employee.objects.filter(
            work_details__employee_status='Active',
            assignedattendancerules__attendance_rule__id__in=list(late_check_inattendance_rules.values_list('id', flat=True))
        )
        
        # Check Is that weekend or holyday
        leave_taken_emps = leave_models.LeavesHistory.objects.filter(employee__in=emp, start_date__lte=timezone_now().date(), 
                                                                     end_date__gte=timezone_now().date(), status__in=[10,20])
        emp = emp.exclude(id__in=list(leave_taken_emps.values_list('employee_id', flat=True)))
        
        check_outs = attendance_models.EmployeeCheckInOutDetails.objects.filter(
            date_of_checked_in=timezone_now().date(), is_logged_out=False, employee_id__in=emp.values_list('id',flat=True)
        )
        
        for checkout in check_outs:
            week_number = get_month_weeks(timezone_now().date())[timezone_now().date().day]
            week_off = custom_is_day_type(week_number, 0, timezone_now().date(), checkout.employee)
            check_out_notify_check_obj, is_created = directory_models.LateCheckInOutReminderCheck.objects.get_or_create(employee=checkout.employee, date_of_check_in=timezone_now().date())
            manager = checkout.employee.employee.filter(manager_type__manager_type=10,manager__work_details__employee_status='Active').first()
            if not week_off and not check_out_notify_check_obj.is_late_check_out_reminder_sent:
                if manager:
                    manager_email = manager.manager.official_email
                    try:
                        emp_code = checkout.employee.work_details.employee_number
                        body = f'''
            Hello {checkout.employee.user.username.title()} [{emp_code}],
            
            It appears that you may have forgotten to check out on the HRMS application for today. Kindly log in and complete your check-out to ensure accurate attendance records.
            
            If you encounter any difficulties or have questions, please don't hesitate to contact the HR department for assistance.
            
            Thank you for your prompt attention to this matter .
            
            Please refer the link for more information {domain}.
            
            Thanks & Regards,
            {checkout.employee.company.company_name.title()}.  
            '''
                        data = {
                            "subject": "Gentle Reminder: HRMS Check-Out for Today",
                            "body": body,
                            "to_email": checkout.employee.user.official_email,
                            "cc" : [manager_email]
                        }
                        if "commit" in sys.argv:
                            Util.send_email(data)
                    except Exception as e:
                        logger.warning(f"Error while sending Email notificaton to {checkout.employee.user.username} in late checkout employee: {e}") 
                
                # employee Whatsapp notifications
                try:
                    whatsapp_data = {
                            'phone_number': checkout.employee.user.phone,
                            'subject': "Gentle Reminder: HRMS Check-Out for Today",
                            "body_text1":"It appears that you may have forgotten to check out on the HRMS application for today",
                            'body_text2': "Kindly log in and complete your check-out to ensure accurate attendance records",
                            'url': f"{domain}",
                            "company_name":checkout.employee.company.company_name.title()
                            }
                    if "commit" in sys.argv:
                        WhatsappMessage.whatsapp_message(whatsapp_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to {checkout.employee.user.username} in late checkout employee: {e}") 
            if "commit" in sys.argv:
                check_out_notify_check_obj.is_late_check_out_reminder_sent = True
                check_out_notify_check_obj.save()

if __name__ == "__main__":
    late_check_in_time = (timezone_now() + timedelta(minutes=30)).time()
    # For Checkin Parts
    late_check_inattendance_rules = attendance_models.AttendanceRules.objects.filter(
        shift_in_time__hour__lte=late_check_in_time.hour, shift_in_time__minute__lte=late_check_in_time.minute
    )
    holidays_exist = pss_calendar_models.Holidays.objects.filter(holiday_date=timezone_now().date(), holiday_type=False)
    if late_check_inattendance_rules.exists() and not holidays_exist.exists():
        EmpCheckinData().main(late_check_inattendance_rules)
    
    late_check_out_time = (timezone_now() - timedelta(hours=3)).time()
    
    late_check_out_attendance_rules = attendance_models.AttendanceRules.objects.filter(
        shift_out_time__hour__lte=late_check_out_time.hour, shift_out_time__minute__lte=late_check_out_time.minute
    )
    if late_check_out_attendance_rules.exists() and not holidays_exist.exists():
        EmplCheckOutData().main(late_check_out_attendance_rules)


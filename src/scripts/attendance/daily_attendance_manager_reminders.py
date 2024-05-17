import sys
import os
import django
import datetime
from django.db import models as db_models
import pandas as pd
sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from attendance.models import EmployeeCheckInOutDetails
from HRMSApp.utils import Util
from core.utils import timezone_now, email_render_to_string, get_domain

class DailyAttedanceReminders:
    
    def __init__(self,company_id):
        self.company_id = company_id
    def convert_date_time(self,date_obj):
        date_time_obj = '-'
        try:
            parsed_time = datetime.datetime.strptime(str(date_obj), '%Y-%m-%d %H:%M:%S.%f%z')
            date_time_obj = parsed_time.strftime('%I:%M %p')
        except Exception as e:
            pass
        return date_time_obj    
    def main(self):
        
        today = timezone_now().date()
        domain = get_domain(sys.argv[-1], sys.argv[1], 'adminAttendanceLogs')
        yesterday = today - datetime.timedelta(days=1)
        checkin_data = EmployeeCheckInOutDetails.objects.filter(date_of_checked_in=yesterday).annotate(
                        rp_name=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type__manager_type=10, employee__employee__is_deleted=False),
                                                                     then=db_models.F('employee__employee__manager__user__username')),
                                                        default=db_models.Value(''), output_field=db_models.CharField()),
                        rp_mail=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type__manager_type=10, employee__employee__is_deleted=False),
                                                                     then=db_models.F('employee__employee__manager__user__email')),
                                                             default=db_models.Value(''), output_field=db_models.CharField()),
                        rp_emp_number=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type__manager_type=10, employee__employee__is_deleted=False),
                                                                     then=db_models.F('employee__employee__manager__work_details__employee_number')),
                                                             default=db_models.Value(''), output_field=db_models.CharField())
                ).values('date_of_checked_in','rp_mail','rp_name','time_in','time_out','employee__user__username',
                         'employee__work_details__department__name','employee__company__company_name','rp_emp_number')

        df = pd.DataFrame(checkin_data,columns = ['date_of_checked_in','rp_mail','rp_name','time_in','time_out',
                                                  'employee__user__username','employee__work_details__department__name',
                                                  'employee__company__company_name','rp_emp_number'])
        if not df.empty:
            df['time_in_hrs'] = df.apply(lambda obj: self.convert_date_time(obj['time_in']) if obj['time_in'] and obj['time_in'] is not None  else '-', axis=1)
            df['time_out_hrs'] = df.apply(lambda obj: self.convert_date_time(obj['time_out']) if obj['time_out'] and obj['time_out'] is not None  else '-', axis=1)
            df.reset_index(drop=True, inplace=True)
            df = df.drop_duplicates(subset=['employee__user__username'])
            df['combine'] = df.apply(lambda obj: f"{obj['employee__user__username']}---->{obj['employee__work_details__department__name']}---->{obj['time_in_hrs']}---->{obj['time_out_hrs']}", axis=1)
            df = df.groupby('rp_mail').agg({"combine": list,
                                                "date_of_checked_in":'first',
                                                "rp_name":"first",
                                                "employee__company__company_name":"first",
                                                "rp_emp_number":'first'
                                                }).reset_index()

        data_dict = df.to_dict('records')
        for obj in data_dict:                    
            try:
                rep_name = obj['rp_name']
                rep_official_email = obj['rp_mail']
                company_name = obj['employee__company__company_name']
                emp_number = obj['rp_emp_number']
                tag = emp_number if emp_number else "-"
                if rep_official_email:
                    combine_data = obj['combine']
                    split_data = [item.split('---->') for item in combine_data]
                    name_dep_df = pd.DataFrame(split_data, columns=['Name', 'Department','Check_In', 'Check_Out'])
                    name_dep_df1 = name_dep_df.to_dict('records')
                    context = {"recds":name_dep_df1,
                                "company_name":company_name,
                                "reporting_manager_name":rep_name,
                                "date":yesterday,"domain":domain, "tag":tag}
                    body = email_render_to_string(
                                template_name="mails/attendance_reminders/daily_attendance_reminders.html", context=context
                            )
                    data={
                            'subject':"Daily Attendance Report",
                            'body':body,
                            'to_email':rep_official_email
                        }
                    if "commit" in sys.argv:
                        Util.send_email(data,is_content_html=True)
            except Exception as e:
                print("Execption in send leave pending details to RM:",e)

        if "commit" in sys.argv:
            print("Daily Attendance Report Emails Sending in Progress")
        else:
            print("Dry Run!")

if __name__ == "__main__":
    company_id = 1
    DailyAttedanceReminders(company_id=company_id).main()

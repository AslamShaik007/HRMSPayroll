import sys
import os
import django
from django.db import models as db_models
import pandas as pd
from datetime import datetime, timedelta
import logging
sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from attendance.models import EmployeeCheckInOutDetails
from HRMSApp.utils import Util
from core.utils import timezone_now, email_render_to_string, get_domain
from core.whatsapp import WhatsappMessage

logger=logging.getLogger('django')
class WeeklyManagerAttedanceReminders:
    
    def __init__(self,company_id):
        self.company_id = company_id
    def convert_date_time(self,date_obj):
        date_time_obj = '-'
        try:
            parsed_time = datetime.strptime(str(date_obj), '%Y-%m-%d %H:%M:%S.%f%z')
            date_time_obj = parsed_time.strftime('%I:%M %p')
        except Exception as e:
            pass
        return date_time_obj 
    
    def calculate_work_duration(self, work_duration):
        total_time = timedelta()

        for time_data in work_duration:
            if time_data and time_data is not None:
                hours, minutes = map(int, time_data.split(':'))
                time_delta = timedelta(hours=hours, minutes=minutes)
                total_time += time_delta

        total_hours = total_time.seconds // 3600
        total_minutes = (total_time.seconds % 3600) // 60

        return f"{total_hours}:{total_minutes:02}"
    
    def calculate_break_duration(self,break_duration):
        total_time = timedelta()

        for time_data in break_duration:
            # work_duration = time_data.get('break_duration')
            if time_data and time_data is not None:
                hours, minutes = map(int, time_data.split(':'))
                time_delta = timedelta(hours=hours, minutes=minutes)
                total_time += time_delta

        total_hours = total_time.seconds // 3600
        total_minutes = (total_time.seconds % 3600) // 60
        return f"{total_hours}:{total_minutes:02}"   

    def main(self):
        emp_domain = get_domain(sys.argv[-1], sys.argv[1], 'userAttendancelogs')
        manager_domain = get_domain(sys.argv[-1], sys.argv[1], 'adminAttendanceLogs')
        today = timezone_now().date()
        week_start_date = today-timedelta(days=5)
        week_end_date = today-timedelta(days=1)
        checkin_data = EmployeeCheckInOutDetails.objects.filter(employee__work_details__employee_status="Active",date_of_checked_in__range=(today-timedelta(days=5),today-timedelta(days=1)),
                                                                time_in__isnull = False,work_duration__isnull = False).annotate(
                        rp_name=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type__manager_type=10, employee__employee__is_deleted=False),
                                                                     then=db_models.F('employee__employee__manager__user__username')),
                                                        default=db_models.Value(''), output_field=db_models.CharField()),
                        rp_mail=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type__manager_type=10, employee__employee__is_deleted=False),
                                                                     then=db_models.F('employee__employee__manager__user__email')),
                                                             default=db_models.Value(''), output_field=db_models.CharField()),
                        rp_phone=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type__manager_type=10, employee__employee__is_deleted=False),
                                                                     then=db_models.F('employee__employee__manager__user__phone')),
                                                             default=db_models.Value(''), output_field=db_models.CharField()),
                        emp_code=db_models.F('employee__work_details__employee_number'),
                        email = db_models.F('employee__official_email'),
                        rp_emp_number=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type__manager_type=10, employee__employee__is_deleted=False),
                                                                     then=db_models.F('employee__employee__manager__work_details__employee_number')),
                                                             default=db_models.Value(''), output_field=db_models.CharField()),
                ).values('date_of_checked_in','rp_mail','rp_name','time_in','time_out','work_duration','break_duration','breaks','employee__user__username','email',
                         'employee__work_details__department__name','employee__company__company_name','emp_code','employee__work_details__employee_number','rp_emp_number',
                         'rp_phone','employee__user__phone')

        df_data = pd.DataFrame(checkin_data,columns = ['date_of_checked_in','rp_mail','rp_name','time_in','time_out','work_duration','break_duration','breaks',
                                                  'employee__user__username','email','employee__work_details__department__name','employee__company__company_name',
                                                  'emp_code','employee__work_details__employee_number','rp_emp_number','rp_phone','employee__user__phone'])
        data = df = []
        if not df_data.empty:
            data = df_data.groupby(['emp_code']).agg(
                {'date_of_checked_in':'first','rp_mail':'first','rp_name':'first',
                    'time_in':list,'time_out':list,'work_duration':list,'break_duration':list,'breaks':list,
                    'employee__user__username':'first','email':'first','employee__work_details__department__name':'first',
                    'employee__company__company_name':'first','employee__work_details__employee_number':'first','rp_emp_number':'first',
                    'rp_phone':'first','employee__user__phone':'first'}
            ).reset_index()
            data['work_duration'] = data.apply(lambda obj: self.calculate_work_duration(obj['work_duration']), axis=1)
            data['break_duration'] = data.apply(lambda obj: self.calculate_break_duration(obj['break_duration']), axis=1)
            data['work_duration'] = data['work_duration'].apply(lambda x: timedelta(hours=int(x.split(':')[0]), minutes=int(x.split(':')[1])))
            data['break_duration'] = data['break_duration'].apply(lambda x: timedelta(hours=int(x.split(':')[0]), minutes=int(x.split(':')[1])))
            data['week_work_duration'] = data['work_duration'] - data['break_duration']
            data['week_work_duration'] = data['week_work_duration'].apply(lambda x: f"{x.seconds // 3600:02d}:{(x.seconds // 60) % 60:02d}")
            data_dict1 = data.to_dict('records')
            data['combine'] = data.apply(lambda obj: f"{obj['emp_code']}---->{obj['employee__user__username']}---->{obj['employee__work_details__department__name']}---->{obj['week_work_duration']}", axis=1)
            df = data.groupby('rp_mail').agg({"combine": list,
                                                "date_of_checked_in":'first',
                                                "rp_name":"first",
                                                "employee__company__company_name":"first",
                                                "employee__work_details__employee_number":'first',
                                                "rp_emp_number":'first',
                                                'rp_phone':'first',
                                                'employee__user__phone':'first'
                                                }).reset_index()

            data_dict = df.to_dict('records')
        if "commit" in sys.argv:  
            if len(data)>0:
                print("Employee Weekly Attedance Reminders sending in progress")
                for obj in data_dict1:
                    emp_number = obj['employee__work_details__employee_number']
                    rp_phone=obj['rp_phone']
                    # tag = 'Mr' if gender == 'MALE' else('Ms' if gender == 'FEMALE' else 'Mr/Ms')
                    try:
                        body = f'''
    Hello {obj['employee__user__username']} {emp_number},

    Total Week Work Duration : {obj['week_work_duration']}

    Please check your weekly attendace total work duration for the past week. {week_start_date} To {week_end_date} , if you have any queries regarding the your total working hour, 
    
    please don't hesitate to reach out to the HR department or your manager.

    Please refer the link for more information {emp_domain}.

    Thanks & Regards,
    {obj['employee__company__company_name']}.
    '''
                        data = {
                        "subject": "Reminder To Check Your Weekly Attendance Work Duration",
                        "body": body,
                        "to_email": obj['email']
                        }
                        Util.send_email(data) 
                    except Exception as e:
                        print(f"exception in sending Weekly Attedance Reminders mail to {obj['email']}:",e)  
                        
                        # employee Whatsapp notifications
                        try:
                            ph_number = obj['employee__user__phone']
                            whatsapp_data = {
                                            'phone_number': ph_number,
                                            'subject': "Reminder To Check Your Weekly Attendance Work Duration",
                                            "body_text1":f"Please check your weekly attendace total work duration for the past week. {week_start_date} To {week_end_date} ",
                                            'body_text2': f" Total Week Work Duration : {obj['week_work_duration']}",
                                            'url': f"{emp_domain}",
                                            "company_name":company_name.title()
                                            }
                            if "commit" in sys.argv:
                                WhatsappMessage.whatsapp_message(whatsapp_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to {obj['employee__user__username']} in manager weekly attendace reminders emails: {e}") 
                print("Employee Weekly Attedance Reminders sent successfully!")
            
            if len(df)>0:
                print("Manager Weekly Attedance Reminders sending in progress")
                for obj in data_dict:                  
                    try:
                        rep_name = obj['rp_name'].title()
                        rep_official_email = obj['rp_mail']
                        company_name = obj['employee__company__company_name'].title()
                        rp_emp_number = obj['rp_emp_number']
                        # gender = obj['rp_gender']
                        tag = rp_emp_number if rp_emp_number else "-"
                        rp_phone=obj['rp_phone']
                        if rep_official_email:
                            combine_data = obj['combine']
                            split_data = [item.split('---->') for item in combine_data]
                            name_dep_df = pd.DataFrame(split_data, columns=['EmpId','Name','Department', 'TotalWorkDuration'])
                            name_dep_df1 = name_dep_df.to_dict('records')
                            context = {"recds":name_dep_df1,
                                        "company_name":company_name,
                                        "reporting_manager_name":rep_name,
                                        "from_date":today-timedelta(days=5),
                                        "to_date":today-timedelta(days=1),
                                        "domain":manager_domain,
                                        "tag":tag
                                        }
                            body = email_render_to_string(
                                        template_name="mails/attendance_reminders/manager_weekly_attendance_reminder.html", context=context
                                    )
                            data={
                                    'subject':"Weekly Attendance Report",
                                    'body':body,
                                    'to_email':rep_official_email
                                }
                            if "commit" in sys.argv:
                                Util.send_email(data,is_content_html=True)
                            
                    except Exception as e:
                        print("Execption in send leave pending details to RM:",e)
                print("Manager Weekly Attedance Reminders sent successfully!")

        else:
            print("Dry Run!")
    

if __name__ == "__main__":
    company_id = 1
    WeeklyManagerAttedanceReminders(company_id=company_id).main()

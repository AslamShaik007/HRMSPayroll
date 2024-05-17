import sys
import os
import django
import datetime
from django.db import models as db_models
import pandas as pd
from django.contrib.postgres.aggregates import ArrayAgg
    
sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from HRMSApp.utils import Util
from core.utils import timezone_now, email_render_to_string, get_month_weeks, get_domain
from directory.models import Employee

class EarlyCheckoutAttedanceReminders:
    
    def __init__(self,company_id):
        self.company_id = company_id
    def convert_date_time(self,date_obj):
        date_time_obj = '-'
        try:
            date_time_obj = datetime.datetime.strptime(date_obj[:19], '%Y-%m-%dT%H:%M:%S').strftime('%I:%M %p')
        except Exception as e:
            pass
        return date_time_obj  
    def check_is_week_off(self,obj,date):
        day_name = date.strftime("%A").upper()
        week_data = {key.upper(): value for key, value in obj.items()}
        day_id = week_data.get(str(day_name),0)
        st = False
        if day_id < 1:
            st = True
        return st    
    def main(self):
        today = timezone_now().date()
        domain = get_domain(sys.argv[-1], sys.argv[1], 'adminAttendanceLogs')
        yesterday = today - datetime.timedelta(days=1)
        empls_data = Employee.objects.filter(work_details__employee_status='Active',
                                             employeeworkrulerelation__work_rule__work_rule_choices__week_number=get_month_weeks(yesterday)[yesterday.day]).annotate(
            leave_status = ArrayAgg('leaveshistory__no_of_leaves_applied', filter = db_models.Q(leaveshistory__start_date__gte=yesterday, 
                                                                                                leaveshistory__end_date__lte=yesterday, leaveshistory__status=10)),
            check_status = ArrayAgg(
                                db_models.expressions.Func(
                                    db_models.Value('time_in'), "clock_details__time_in",
                                    db_models.Value('time_out'), "clock_details__time_out",
                                    db_models.Value('work_duration'), "clock_details__work_duration",
                                    function="jsonb_build_object",
                                    output_field=db_models.JSONField()
                                ),
                                    distinct=True,
                                    filter = db_models.Q(
                                        clock_details__date_of_checked_in=yesterday)
                                ),
            rp_name=db_models.Case(db_models.When(db_models.Q(employee__manager_type__manager_type=10, employee__is_deleted=False),
                                                                        then=db_models.F('employee__manager__user__username')),
                                                            default=db_models.Value(''), output_field=db_models.CharField()),
            rp_mail=db_models.Case(db_models.When(db_models.Q(employee__manager_type__manager_type=10, employee__is_deleted=False),
                                                            then=db_models.F('employee__manager__user__email')),
                                                    default=db_models.Value(''), output_field=db_models.CharField()),
            work_week_details = db_models.expressions.Func(
                                        db_models.Value('monday'), "employeeworkrulerelation__work_rule__work_rule_choices__monday",
                                        db_models.Value('tuesday'), "employeeworkrulerelation__work_rule__work_rule_choices__tuesday",
                                        db_models.Value('wednesday'), "employeeworkrulerelation__work_rule__work_rule_choices__wednesday",
                                        db_models.Value('thursday'), "employeeworkrulerelation__work_rule__work_rule_choices__thursday",
                                        db_models.Value('friday'), "employeeworkrulerelation__work_rule__work_rule_choices__friday",
                                        db_models.Value('saturday'), "employeeworkrulerelation__work_rule__work_rule_choices__saturday",
                                        db_models.Value('sunday'), "employeeworkrulerelation__work_rule__work_rule_choices__sunday",
                                    function="jsonb_build_object",
                                        output_field=db_models.JSONField()
                                            ),
            rp_emp_number=db_models.Case(db_models.When(db_models.Q(employee__manager_type__manager_type=10, employee__is_deleted=False),
                                                            then=db_models.F('work_details__employee_number')),
                                                    default=db_models.Value(''), output_field=db_models.CharField()),
                ).values('leave_status','check_status','rp_name','rp_mail','user__username','work_details__department__name',
                                    'company__company_name','work_details__employee_number','work_details__designation__name','work_week_details','rp_emp_number')
        
        empls_data_df = pd.DataFrame(empls_data,columns = ['leave_status','check_status','rp_name','rp_mail','user__username',
                                                            'work_details__department__name','company__company_name','work_details__employee_number',
                                                            'work_details__designation__name','work_week_details','rp_emp_number'])
    
        if not empls_data_df.empty:
            empls_data_df['is_week_off'] = empls_data_df.apply(lambda obj: self.check_is_week_off(obj['work_week_details'], yesterday), axis=1)
            empls_data_df = empls_data_df[empls_data_df['is_week_off'] != True]
        if not empls_data_df.empty:
            empls_data_df['time_in'] = empls_data_df.apply(lambda obj:obj['check_status'][0].get('time_in') if obj['check_status'] else '',axis=1)
            empls_data_df['time_out'] = empls_data_df.apply(lambda obj:obj['check_status'][0].get('time_out') if obj['check_status'] else '',axis=1)
            empls_data_df['work_duration'] = empls_data_df.apply(lambda obj:obj['check_status'][0].get('work_duration') if obj['check_status'] else '',axis=1)
            empls_data_df['status'] = empls_data_df.apply(lambda obj: 'Not Check Out' if not obj['work_duration'] else ('Early Checkout' if int(obj['work_duration'].split(':')[0]) < 8 else ('Late Checkout' if int(obj['work_duration'].split(':')[0]) > 12 else '')), axis=1)
            empls_data_df['status'] = empls_data_df.apply(lambda obj:'Not Check In' if not obj['leave_status'] and not obj['check_status'] else (('Full Day Leave' if int(obj['leave_status'][0]) > 1 else 'Half Day Leave') if obj['leave_status'] else obj['status']),axis=1)
            empls_data_df['time_in_hrs'] = empls_data_df.apply(lambda obj: self.convert_date_time(obj['time_in']) if obj['time_in'] and obj['time_in'] is not None  else '-', axis=1)
            empls_data_df['time_out_hrs'] = empls_data_df.apply(lambda obj: self.convert_date_time(obj['time_out']) if obj['time_out'] and obj['time_out'] is not None  else '-', axis=1)
            empls_data_df.reset_index(drop=True, inplace=True)
            empls_data_df = empls_data_df.drop_duplicates(subset=['user__username'])
            empls_data_df = empls_data_df[empls_data_df['rp_mail'].notnull() & (empls_data_df['rp_mail'] != '')]
            empls_data_df['combine'] = empls_data_df.apply(lambda obj: f"{obj['work_details__employee_number']}---->{obj['user__username']}---->{obj['work_details__designation__name']}---->{obj['work_details__department__name']}---->{obj['time_in_hrs']}---->{obj['time_out_hrs']}---->{obj['status']}", axis=1)
            empls_data_df = empls_data_df.groupby('rp_mail').agg({"combine": list,
                                                "rp_name":"first",
                                                "company__company_name":"first",
                                                "rp_emp_number":'first'
                                                }).reset_index()

        data_dict = empls_data_df.to_dict('records')
        
        if "commit" in sys.argv:
            print("Daily Login Details Report Emails Sending in Progress")
        else:
            print("Dry Run!")   
            
        for obj in data_dict:   
            try:
                rep_name = obj['rp_name'].title()
                rep_official_email = obj['rp_mail']
                rp_emp_number = obj['rp_emp_number']
                tag = rp_emp_number if rp_emp_number else "-"
                company_name = obj['company__company_name'].title()
                if rep_official_email:
                    combine_data = obj['combine']
                    split_data = [item.split('---->') for item in combine_data]
                    name_dep_df = pd.DataFrame(split_data, columns=['Emp_Id','Emp_Name', 'Designation', 'Department','Check_In', 'Check_Out', 'Status'])
                    name_dep_df1 = name_dep_df.to_dict('records')
                    context = {"recds":name_dep_df1,
                                "company_name":company_name,
                                "reporting_manager_name":rep_name,
                                "date":yesterday, "domain":domain,"tag":tag}
                    body = email_render_to_string(
                                template_name="mails/attendance_reminders/early_and_late_checkout.html", context=context
                            )
                    data={
                            'subject':"Daily Login Details Report",
                            'body':body,
                            'to_email':rep_official_email
                        }
                    if "commit" in sys.argv:
                        Util.send_email(data,is_content_html=True)
            except Exception as e:
                print("Execption in Daily Login Details Report Emails to RM:",e)
                 

if __name__ == "__main__":
    company_id = 1
    EarlyCheckoutAttedanceReminders(company_id=company_id).main()

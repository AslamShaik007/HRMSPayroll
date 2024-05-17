from datetime import datetime
from typing import Any
import pandas as pd

from django.db import models as db_models
from django.db import models as db_models
from django.core.management.base import BaseCommand, CommandParser

from attendance.models import (
    AnamolyHistory,
    AttendanceRuleSettings
)
from leave.models import LeavesHistory
from HRMSApp.utils import Util
from HRMSApp.models import CompanyDetails
from directory.models import Employee
from core.utils import timezone_now, get_paycycle_dates


class Command(BaseCommand):
      
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--commit",
            "-c",
            default=False,
            action="store_true",
            dest="commit",
            help="Commit into DB",
        )
        
    def date_converter(self,x):
        new_dates = []
        if x:
            new_dates.extend(obj.strftime('%d-%m-%Y') for obj in x)
        return ', '.join(new_dates) 
    
    def handle(self, *args: Any, **options: Any):
        if options["commit"]:
            self.stdout.write(self.style.SUCCESS("emails sending in progress"))
            
            current_date = timezone_now().date()
            company_obj = CompanyDetails.objects.first()
            company_name = company_obj.company_name
            company_id = company_obj.id
            att_sett_data = AttendanceRuleSettings.objects.filter(company_id = company_id)
            if att_sett_data.exists():
                psc_from_date =  att_sett_data.first().attendance_input_cycle_from
                psc_to_date   =  att_sett_data.first().attendance_input_cycle_to
                pay_cycle_from_date,pay_cycle_to_date,current_payout_date = get_paycycle_dates(current_date,psc_from_date,psc_to_date)
                #send attendance pending emails to employee
                q_filter = db_models.Q(is_deleted=False, status = 20, request_date__gte = pay_cycle_from_date,request_date__lte = pay_cycle_to_date)
    
                data2 = AnamolyHistory.objects.filter(q_filter).values(
                                                                'clock__employee__user__email',
                                                                'clock__employee__user__username',
                                                                'request_date',
                                                                'clock__employee__company__consolidate_notification_date__employee_start_date',
                                                                'clock__employee__company__consolidate_notification_date__employee_end_date'
                                                                )
                
                dfr = pd.DataFrame(data2,columns = ['clock__employee__user__username','clock__employee__user__email',
                                                'request_date','clock__employee__company__consolidate_notification_date__employee_start_date',
                                                'clock__employee__company__consolidate_notification_date__employee_end_date'])
                
                dfr = dfr.groupby('clock__employee__user__username').agg({'clock__employee__user__email':'first',
                                                                    'clock__employee__company__consolidate_notification_date__employee_start_date':'first',
                                                                    'clock__employee__company__consolidate_notification_date__employee_end_date':'first',
                                                                    'request_date':list}).reset_index()
                
                data_dict = dfr.to_dict('records')
                
                for obj in data_dict:                    
                    try:
                        employee_name = obj['clock__employee__user__username']
                        official_email = obj['clock__employee__user__email']
                        request_dates = list(set(obj['request_date']))
                        employee_start_date = obj['clock__employee__company__consolidate_notification_date__employee_start_date']
                        employee_end_date = obj['clock__employee__company__consolidate_notification_date__employee_end_date']
                        converted_dates = self.date_converter(request_dates)
                        if employee_start_date <= current_date <= employee_end_date:
                            body=f'Hello Mr/Ms {employee_name},\n\nAnomalies are pending for the dates {converted_dates}, Connect to your HRMS application to find more details.\n\nThanks,\n{company_name}' 
                            data={
                                    'subject':'Anamoly Pending',
                                    'body':body,
                                    'to_email':official_email
                                }
                            Util.send_email(data)
                    except Exception as e:
                        pass
                    
                #send attendance pending emails to reporting manager
                q1_filter = db_models.Q(is_deleted=False, status = 30, request_date__gte = pay_cycle_from_date,request_date__lte = pay_cycle_to_date)
    
                data3 = AnamolyHistory.objects.filter(q1_filter).annotate(
                                    rp_name=db_models.Case(db_models.When(db_models.Q(clock__employee__employee__manager_type_id=1), 
                                                                then=db_models.F('clock__employee__employee__manager__user__username')),
                                                        default=db_models.Value(''), output_field=db_models.CharField()),
                                    rp_mail=db_models.Case(db_models.When(db_models.Q(clock__employee__employee__manager_type_id=1), 
                                                                then=db_models.F('clock__employee__employee__manager__user__email')),
                                                        default=db_models.Value(''), output_field=db_models.CharField())
                                    ).values(
                                            'clock__employee__user__email',
                                            'clock__employee__user__username',
                                            'request_date',
                                            'clock__employee__company__consolidate_notification_date__reporting_manager_start_date',
                                            'clock__employee__company__consolidate_notification_date__reporting_manager_end_date',
                                            'rp_name', 'rp_mail')
                dfr1 = pd.DataFrame(data3,columns = ['clock__employee__user__username','clock__employee__user__email',
                                                'request_date','clock__employee__company__consolidate_notification_date__reporting_manager_start_date',
                                                'clock__employee__company__consolidate_notification_date__reporting_manager_end_date',
                                                'rp_name','rp_mail'])
                
                dfr1 = dfr1.groupby('rp_mail').agg({'clock__employee__user__email':'first',
                                                    'clock__employee__company__consolidate_notification_date__reporting_manager_start_date':'first',
                                                    'clock__employee__company__consolidate_notification_date__reporting_manager_end_date':'first',
                                                    'rp_name':'first',
                                                    'clock__employee__user__username':set }).reset_index()
                # dfr1['new'] = dfr1.apply(lambda x: str({x['clock__employee__user__username']: x['request_date']}), axis=1)
                # dfr1 = dfr1.groupby('rp_mail').agg({'new': 'unique'}).reset_index()
                
                data_dict1 = dfr1.to_dict('records')
                for obj in data_dict1:                    
                    try:
                        reporting_manager_start_date = obj['clock__employee__company__consolidate_notification_date__reporting_manager_start_date']
                        reporting_manager_end_date = obj['clock__employee__company__consolidate_notification_date__reporting_manager_end_date']
                        emp_count = len(obj['clock__employee__user__username'])
                        empls_names = ', '.join(obj['clock__employee__user__username'])
                        rep_name = obj['rp_name']
                        rep_official_email = obj['rp_mail']
                        if rep_official_email and reporting_manager_start_date <= current_date <= reporting_manager_end_date:
                            body=f'Hello Mr/Ms {rep_name},\n\nAnomalies are pending for the mentioned employees,\nEmployee Names : {empls_names},\nPending employees count :{emp_count},\nConnect to your HRMS application to find more details.\n\nThanks,\n{company_name}' 
                            data={
                                    'subject':'Anamoly Pending',
                                    'body':body,
                                    'to_email':rep_official_email
                                }
                            Util.send_email(data)
                    except Exception as e:
                        pass
                    
                # send attendance pending details to HR manager
                att_pending_data = data3.values('clock__employee__user__username','clock__employee__company__consolidate_notification_date__hr_manager_start_date',
                                     'clock__employee__company__consolidate_notification_date__hr_manager_end_date')
                
                dfr4 = pd.DataFrame(att_pending_data,columns = ['clock__employee__user__username',
                                    'clock__employee__company__consolidate_notification_date__hr_manager_start_date',
                                    'clock__employee__company__consolidate_notification_date__hr_manager_end_date'])
                dfr4 = dfr4.drop_duplicates(subset=['clock__employee__user__username'])
                hr_admin = Employee.objects.filter(roles__name = 'HR')
                
                if not dfr4.empty:
                    hr_manager_start_date = dfr4.at[0, 'clock__employee__company__consolidate_notification_date__hr_manager_start_date']
                    hr_manager_end_date = dfr4.at[0, 'clock__employee__company__consolidate_notification_date__hr_manager_end_date']    
                    if not dfr4.empty and hr_admin.exists() and hr_manager_start_date <= current_date <= hr_manager_end_date:
                        try:
                            employees_names = dfr3['clock__employee__user__username'].str.cat(sep=' ')
                            hr_name = hr_admin.first().user.username
                            hr_mail = hr_admin.first().user.email
                            body=f'Hello Mr/Ms {hr_name},\n\nAnomalies are pending for the mentioned employees,\nEmployee Names : {employees_names},\nPending employees count :{emp_count},\nConnect to your HRMS application to find more details.\n\nThanks,\n{company_name}' 
                            data={
                                    'subject':'Anamoly Pending',
                                    'body':body,
                                    'to_email':hr_mail
                                }
                            Util.send_email(data)
                        except Exception as e:
                            pass
                    
                # send leave pending details to reporting manager
                data4 = LeavesHistory.objects.filter(is_deleted=False,status=20,employee__company_id =company_id).annotate(
                                    rp_name=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1), 
                                                                then=db_models.F('employee__employee__manager__user__username')),
                                                        default=db_models.Value(''), output_field=db_models.CharField()),
                                    rp_mail=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type_id=1), 
                                                                then=db_models.F('employee__employee__manager__user__email')),
                                                        default=db_models.Value(''), output_field=db_models.CharField())
                                    ).values('rp_name','rp_mail','employee__user__username',
                                             'employee__company__consolidate_notification_date__reporting_manager_start_date',
                                             'employee__company__consolidate_notification_date__reporting_manager_end_date')
            
                dfr2 = pd.DataFrame(data4,columns = ['rp_name','rp_mail','employee__user__username',
                                                'employee__company__consolidate_notification_date__reporting_manager_start_date',
                                                'employee__company__consolidate_notification_date__reporting_manager_end_date'])
                
                dfr2 = dfr2.groupby('rp_mail').agg({'rp_name':'first',
                                                    'employee__company__consolidate_notification_date__reporting_manager_start_date':'first',
                                                    'employee__company__consolidate_notification_date__reporting_manager_end_date':'first',
                                                    'employee__user__username':set }).reset_index()

                data_dict2 = dfr2.to_dict('records')
                for obj in data_dict2:                    
                    try:
                        reporting_manager_start_date = obj['employee__company__consolidate_notification_date__reporting_manager_start_date']
                        reporting_manager_end_date = obj['employee__company__consolidate_notification_date__reporting_manager_end_date']
                        emp_counts = len(obj['employee__user__username'])
                        empls_names = ', '.join(obj['employee__user__username'])
                        rep_name = obj['rp_name']
                        rep_official_email = obj['rp_mail']
                        if rep_official_email and reporting_manager_start_date <= current_date <= reporting_manager_end_date:
                            body=f'Hello Mr/Ms {rep_name},\n\nLeaves are pending for the mentioned employees,\nEmployee Names : {empls_names},\nPending employees count :{emp_counts},\nConnect to your HRMS application to find more details.\n\nThanks,\n{company_name}' 
                            data={
                                    'subject':'Leave Pending',
                                    'body':body,
                                    'to_email':rep_official_email
                                }
                            Util.send_email(data)
                    except Exception as e:
                        pass
                    
                # send leave pending details to HR manager
                leave_data = data4.values(
                    'employee__company__consolidate_notification_date__hr_manager_start_date',
                    'employee__company__consolidate_notification_date__hr_manager_end_date',
                    'employee__user__username')
                dfr3 = pd.DataFrame(leave_data,columns = ['employee__user__username',
                                'employee__company__consolidate_notification_date__hr_manager_start_date',
                                'employee__company__consolidate_notification_date__hr_manager_end_date'])
                dfr3 = dfr3.drop_duplicates(subset=['employee__user__username'])
                hr_admin = Employee.objects.filter(roles__name = 'HR')
                if not dfr3.empty :
                    hr_manager_start_date = dfr3.at[0, 'employee__company__consolidate_notification_date__hr_manager_start_date']
                    hr_manager_end_date = dfr3.at[0, 'employee__company__consolidate_notification_date__hr_manager_start_date']
                    if hr_admin.exists() and hr_manager_start_date <= current_date <= hr_manager_end_date:
                        try:
                            employees_names = dfr3['employee__user__username'].str.cat(sep=' ')
                            hr_name = hr_admin.first().user.username
                            hr_mail = hr_admin.first().user.email
                            body=f'Hello Mr/Ms {hr_name},\n\nLeaves are pending for the mentioned employees,\nEmployee Names : {employees_names},\nPending employees count :{emp_counts},\nConnect to your HRMS application to find more details.\n\nThanks,\n{company_name}' 
                            data={
                                    'subject':'Leave Pending',
                                    'body':body,
                                    'to_email':hr_mail
                                }
                            Util.send_email(data)
                        except Exception as e:
                            pass
            self.stdout.write(self.style.SUCCESS("emails sent successfully!"))    
        else :
            self.stdout.write(self.style.WARNING("Consolidate Dry Run!"))
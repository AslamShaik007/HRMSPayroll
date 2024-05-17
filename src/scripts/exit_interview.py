import sys
import os
from datetime import timedelta   
import pandas as pd

import django
from django.db import models as db_models

sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from core.utils import timezone_now, TimestampToStr, email_render_to_string,get_domain
from directory.models import EmployeeResignationDetails, Employee, ManagerType
from HRMSApp.utils import Util
from django.contrib.postgres.aggregates import ArrayAgg
import logging
logger = logging.getLogger("django")
from core.whatsapp import WhatsappMessage

class ExitInterview:
    
    def __init__(self,company_id):
        self.company_id = company_id
    
    def main(self):
        
        q_filter = db_models.Q(company_id=1, resignation_info__isnull = False, resignation_info__notice_period__isnull = False, 
                               work_details__employee_status = 'Active', resignation_info__exit_interview_date = timezone_now().date())
        # q_filter = db_models.Q(company_id=1, resignation_info__exit_interview_date = timezone_now().date())
        hr_domain = get_domain(sys.argv[-1], sys.argv[1], 'directory')
        domain = get_domain(sys.argv[-1], sys.argv[1], 'userprofile')
        query = Employee.objects.filter(q_filter).prefetch_related('work_details').annotate(
            hr_man_name = db_models.F('resignation_info__updated_by__username'),
            hr_man_phone = db_models.F('resignation_info__updated_by__phone'),
            hr_man_email = db_models.F('resignation_info__updated_by__email'),
            hr_man_emp_code = db_models.F('resignation_info__updated_by__employee_details__work_details__employee_number'),
            exit_interview_time = TimestampToStr(db_models.F('resignation_info__exit_interview_time')),
            rep_man_details = ArrayAgg(
                        db_models.expressions.Func(
                            db_models.Value('emp_name'),'employee__manager__user__username',
                            db_models.Value('emp_phone'),'employee__manager__user__phone',
                            function="jsonb_build_object",
                            output_field=db_models.JSONField()
                        ),
                            distinct=True,
                            filter=db_models.Q(employee__isnull=False, employee__is_deleted=False, 
                                               employee__manager__work_details__employee_status='Active', employee__manager_type__manager_type=ManagerType.PRIMARY),
                        ),
            ).values(
            'user__username','resignation_info__notice_period','work_details__employee_number',
            'work_details__department__name','roles__name','hr_man_name','hr_man_phone','resignation_info__resignation_date',
            'hr_man_email','company__company_name','resignation_info__exit_interview_date','exit_interview_time','official_email','rep_man_details',
            'resignation_info__last_working_day','gender','hr_man_emp_code','phone'
        )
        
        df1 = pd.DataFrame(query, columns=['user__username','resignation_info__notice_period','work_details__employee_number','rep_man_details',
                                            'work_details__department__name','roles__name','hr_man_name','hr_man_phone','resignation_info__resignation_date',
                                            'hr_man_email','company__company_name','resignation_info__exit_interview_date','exit_interview_time','official_email',
                                            'resignation_info__last_working_day','gender','hr_man_emp_code','phone'])
        if len(df1) != 0:
            # df1['last_day'] = df1.apply(lambda obj: obj['resignation_info__resignation_date'] + timedelta(days=obj['resignation_info__notice_period']) if obj['resignation_info__resignation_date'] else '', axis=1)
            df2=df1
            df2['report_man_name'] = df2.apply(lambda obj:obj['rep_man_details'][0].get('emp_name') if obj['rep_man_details'] else '',axis=1)
            df2['report_man_phone'] = df2.apply(lambda obj:obj['rep_man_details'][0].get('emp_phone') if obj['rep_man_details'] else '',axis=1)
            df2['resignation_info__last_working_day']= df2.apply(lambda obj:obj['resignation_info__last_working_day'].strftime("%d-%m-%Y") if obj['resignation_info__last_working_day'] else '',axis=1)
            df2['combine'] = df2.apply(lambda obj: f"{obj['work_details__employee_number']}---->{obj['user__username']}---->{obj['roles__name']}---->{obj['work_details__department__name']}---->{obj['resignation_info__last_working_day']}---->{obj['exit_interview_time']}---->{obj['resignation_info__last_working_day']}", axis=1)
            df2 = df2.groupby('hr_man_email').agg({"combine": list,
                                                   "company__company_name":'first',
                                                   'hr_man_emp_code':'first',
                                                   'hr_man_name':'first'
                                                }).reset_index()
            data_dict = df2.to_dict('records')
            for obj in data_dict:   
                try:
                    hr_email = obj['hr_man_email']
                    hr_phone = obj['hr_man_phone']
                    if hr_email:
                        combine_data = obj['combine']
                        company_name = obj['company__company_name']
                        split_data = [item.split('---->') for item in combine_data]
                        name_dep_df = pd.DataFrame(split_data, columns=['emp_id','emp_name', 'role', 'department','last_day', 'time',"date"])
                        name_dep_df1 = name_dep_df.to_dict('records')
                        context = {"recds":name_dep_df1,
                                    "company_name":company_name.title(),
                                    "hr_name":obj['hr_man_name'],
                                    "hr_emp_code_name":obj['hr_man_emp_code']
                                }
                        body = email_render_to_string(
                                    template_name="mails/directory_mails/exit_interview.html", context=context
                                )
                        data={
                            'subject':f"Exit Interview",
                            'body':body,
                            'to_email':[hr_email,'hr@pranathiss.com']
                        }
                        if "commit" in sys.argv:
                            Util.send_email(data, multiple=True, is_content_html=True)
                            try:
                                employee_data = {
                                        'phone_number':hr_phone,
                                        'subject': "Exit Interview",
                                        'body_text1' : "The scheduled exit interviews for employees are in list",
                                        'body_text2' : " ",
                                        'url': f"{hr_domain}",
                                        "company_name": company_name
                                        }
                                WhatsappMessage.whatsapp_message(employee_data)
                            except Exception as e:
                                print('e',e)
                                logger.warning(f"Error while sending Whatsapp notificaton to about Exit interview sheet : {e}")
                except Exception as e:
                    pass
            for emp_data in df1.to_dict('records'):
                emp_name = emp_data['user__username']
                emp_phone = emp_data['phone']
                hr_email = emp_data['hr_man_email']
                company_name = emp_data['company__company_name']
                exit_interview_time = emp_data['exit_interview_time']
                exit_interview_date = emp_data['resignation_info__exit_interview_date']
                emp_email = emp_data['official_email']
                emp_code = emp_data['work_details__employee_number']
                    
                emp_mail_body = f'''
    Hello {emp_name} [{emp_code}],
    
    Greetings for the day!
    
    The exit interview is scheduled for {exit_interview_date.strftime("%d-%m-%Y")} at {exit_interview_time}. Please ensure your availability for this meeting, 
    
    As your input is highly valued. During the exit interview, you will have the chance to share your thoughts on your overall experience at {company_name}, 
    
    Your reasons for leaving, and any suggestions you may have for us.
            
    Thanks & Regards,
    {company_name.title()}.
                '''
                try:
                    data={
                        'subject':f"Exit Interview Scheduled",
                        'body':emp_mail_body,
                        'to_email':emp_email
                    }
                    if "commit" in sys.argv:
                        Util.send_email(data)
                        try:
                            employee_data = {
                                    'phone_number':emp_phone,
                                    'subject': f"Exit Interview Scheduled",
                                    'body_text1' : f"The exit interview is scheduled for {exit_interview_date.strftime('%d-%m-%Y')} at {exit_interview_time}.",
                                    'body_text2' : " ",
                                    'url': f"{domain}",
                                    "company_name": company_name
                                    }
                            WhatsappMessage.whatsapp_message(employee_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to exit interview: {e}")
                except Exception as e:
                    pass  
                
        # print("Exit Interview mails sent successfully!")
        if "commit" in sys.argv:
            print("Exit Interview mails sent successfully!")
        else:
            print("Dry Run!")
if __name__ == "__main__":
    company_id = 1
    ExitInterview(company_id=company_id).main()

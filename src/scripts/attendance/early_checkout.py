import sys
import os
import django
import pandas as pd
import logging

sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from django.db import models as db_models
from django.conf import settings

from core.utils import timezone_now, get_domain,get_month_weeks
from HRMSApp.utils import Util
from attendance.models import EmployeeCheckInOutDetails
from pss_calendar.models import Holidays
from core.whatsapp import WhatsappMessage
logger = logging.getLogger('django')
class EmplEarlyCheckOutData:

    
    def main(self):
        domain = get_domain(sys.argv[-1], sys.argv[1], 'userAttendancelogs')
        today = timezone_now().date() 
        final_day = today
        td = final_day.strftime("%A").lower()
        
        if Holidays.objects.filter(db_models.Q(holiday_date = today, is_deleted = False)):
            logger.warning("early check out Script can't be run on Holiday") 
            return
        
        q_filter = db_models.Q(employee__work_details__employee_status='Active',
                                date_of_checked_in=timezone_now().date(),
                                is_logged_out=True,
                                time_out__time__lte = db_models.F('employee__assignedattendancerules__attendance_rule__shift_out_time'),
                                employee__employeeworkrulerelation__work_rule__work_rule_choices__week_number=get_month_weeks(today)[today.day],
                                employee__payroll_status=True, is_deleted=False,
                            )
        emps = EmployeeCheckInOutDetails.objects.filter(q_filter).annotate(
            rp_name=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type__manager_type=10, employee__employee__is_deleted=False),
                                            then=db_models.F('employee__employee__manager__user__username')),
                                    default=db_models.Value(''), output_field=db_models.CharField()),
            rp_mail=db_models.Case(db_models.When(db_models.Q(employee__employee__manager_type__manager_type=10, employee__employee__is_deleted=False),
                                            then=db_models.F('employee__employee__manager__user__email')),
                                    default=db_models.Value(''), output_field=db_models.CharField()),
            work_rule_choices_new= db_models.expressions.Func(
                                db_models.Value('id'), 'employee__employeeworkrulerelation__work_rule__work_rule_choices__id',
                                db_models.Value('work_rule'), 'employee__employeeworkrulerelation__work_rule__id',
                                db_models.Value('monday'), 'employee__employeeworkrulerelation__work_rule__work_rule_choices__monday',
                                db_models.Value('tuesday'), 'employee__employeeworkrulerelation__work_rule__work_rule_choices__tuesday',
                                db_models.Value('wednesday'), 'employee__employeeworkrulerelation__work_rule__work_rule_choices__wednesday',
                                db_models.Value('thursday'), 'employee__employeeworkrulerelation__work_rule__work_rule_choices__thursday',
                                db_models.Value('friday'), 'employee__employeeworkrulerelation__work_rule__work_rule_choices__friday',
                                db_models.Value('saturday'), 'employee__employeeworkrulerelation__work_rule__work_rule_choices__saturday',
                                db_models.Value('sunday'), 'employee__employeeworkrulerelation__work_rule__work_rule_choices__sunday',
                                db_models.Value('week_number'), 'employee__employeeworkrulerelation__work_rule__work_rule_choices__week_number',
                                function='jsonb_build_object',
                            output_field=db_models.JSONField())
            ).values("rp_mail","rp_name",'employee__assignedattendancerules__attendance_rule__shift_out_time',
                     'employee__user__username','employee__official_email','time_out__time','employee__company__company_name',
                     'employee__work_details__employee_number','work_rule_choices_new','employee__user__phone')
        
        df = pd.DataFrame(emps,columns=['work_rule_choices_new',"rp_mail","rp_name",'employee__assignedattendancerules__attendance_rule__shift_out_time',
                                        'employee__user__username','employee__official_email','time_out__time',
                                        'employee__company__company_name','employee__work_details__employee_number','employee__user__phone'])
        df['status'] = df.apply(lambda obj :('wo' if obj['work_rule_choices_new'].get(td) == 0 else 'p') if obj['work_rule_choices_new'] else 'wo' , axis=1)
        df = df[df['status'] != 'wo']

        empls = df.to_dict('records')

        if "commit" in sys.argv:  
            print(" Notification sending in progress")
        else:
            print("Dry Run")
        
        if empls:
            for obj in empls:
                emp_email = obj['employee__official_email']
                emp_name = obj['employee__user__username'].title()
                rep_name = obj['rp_name']
                rep_official_email = obj['rp_mail']
                company_name = obj['employee__company__company_name'].title()
                emp_number = obj['employee__work_details__employee_number']
                user_phone = obj['employee__user__phone']
                tag = emp_number if emp_number else "-"
                try:
                    body = f'''
        Hello {emp_name} [{tag}],

        It appears that you have Check-Out early today. Kindly Provide the reason to your manager {rep_name}.

        If you encounter any difficulties or have questions, please don't hesitate to contact the HR department for assistance.

        Thank you for your prompt attention to this matter .
        
        Please refer the link for more information {domain}.

        Thanks & Regards,
        {company_name}.  
        '''
                    data = {
                        "subject": "Gentle Reminder: HRMS Check-Out for Today",
                        "body": body,
                        "to_email": emp_email,
                        "cc" : [rep_official_email]
                        
                    }

                    if "commit" in sys.argv: 
                        Util.send_email(data)

                except:
                    pass
                
                # employee Whatsapp notifications
                if user_phone and rep_name:
                    try:
                        whatsapp_data = {
                                'phone_number': user_phone,
                                'subject': "Gentle Reminder: HRMS Check-Out for Today",
                                "body_text1":"It appears that you have Check-Out early today",
                                'body_text2': f"Kindly provide the reason to your manager {rep_name}",
                                'url': f"{domain}",
                                "company_name":company_name.title()
                                }
                        if "commit" in sys.argv:
                            WhatsappMessage.whatsapp_message(whatsapp_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {emp_name} in early checkout employee: {e}") 
    
    #early checkout 
if __name__ == "__main__":
    EmplEarlyCheckOutData().main()
    
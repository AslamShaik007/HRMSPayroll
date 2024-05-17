import sys
import os
import json
import django
import re
import datetime
import pandas as pd
from io import BytesIO

from django.db import models as db_models
from deepdiff import DeepDiff
sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from core.utils import timezone_now, SplitPart, get_domain
from directory.models import Employee
from HRMSApp.utils import Util
from company_profile.models import LoggingRecord
from HRMSApp.models import CompanyDetails

import logging
logger = logging.getLogger("django")
from core.whatsapp import WhatsappMessage

class AuditReportMails:
    
    def __init__(self,company_id):
        self.company_id = company_id
        
    def clean_list(self,list_data):
        try:
            keys_to_remove = ["id", "is_deleted","created_at", "updated_at", "created_by_id", "updated_by_id","employee_id","company_id"]
            cleaned_list = [{k: v for k, v in item.items() if k not in keys_to_remove} for item in list_data]
            result_string = ', '.join([f"{k}: {v}" for d in cleaned_list for k, v in d.items()])
            return result_string
        except:
            return None
    
    
    def parse_json(self, x):
        try:
            return json.loads(x)
        except:
            return None
    
    def generate_old_new_data(self, changes, key_type):
        try:
            key_val = f'{key_type}_value' 
            op_str = ""
            if 'values_changed' in changes:
                op_str += ", ".join([f"""{i.split("['")[1].split("']")[0]}:  {changes['values_changed'][i][key_val]}""" for i in changes['values_changed']])
            if 'type_changes' in changes:
                tp_changes = ", ".join([f"""{i.split("['")[1].split("']")[0]}:  {changes['type_changes'][i][key_val]}""" for i in changes['type_changes']])
                op_str = op_str+','+tp_changes
            return "Nothing Updated" if re.sub(r'updated_at:[^,]+', '', op_str)=="" else op_str
        except Exception as e:
            return None
    def remove_keys(self,data_string):
        try:
            pairs = [pair.strip() for pair in data_string.split(',')]
            if not ':' in pairs[0]:
                return data_string
            data_dict = {}
            for pair in pairs:
                key, value = pair.split(':', 1)
                data_dict[key.strip()] = value.strip()
            try:
                if 'updated_at' in data_dict:
                    timestamp_obj = datetime.datetime.strptime(data_dict['updated_at'], "%Y-%m-%d %H:%M:%S.%f%z")
                    formatted_timestamp = timestamp_obj.strftime("%Y-%m-%d %I:%M:%S %p")
                    data_dict['updated_at']=formatted_timestamp
            except Exception as e:
                pass   
            if 'updated_by_id' in data_dict:
                del data_dict['updated_by_id']
                
            modified_data_string = ", ".join([f"{key}: {value}" for key, value in data_dict.items()])
            return modified_data_string
        except Exception as e:
            pass
        
    def main(self):
        admin_emails = list(Employee.objects.filter(roles__name = 'ADMIN', company_id=self.company_id, work_details__employee_status='Active'
                                                    ).values('official_email','user__username','work_details__employee_number','phone'))
        
        from_date = to_date = timezone_now().date()
        company_name = CompanyDetails.objects.first().company_name
        q_filter = db_models.Q(created_at__date__range=[from_date, to_date], method__in=["PUT","PATCH","POST"])
        domain = get_domain(sys.argv[-1], sys.argv[1], 'auditreports')
        data = LoggingRecord.objects.filter(q_filter).annotate(
            changed_data_at=SplitPart(db_models.F('end_point'), db_models.Value(':82'), db_models.Value(2)),
            module_name=db_models.Case(
                db_models.When(end_point__icontains='api/user/', then=db_models.Value('Login')),
                db_models.When(end_point__icontains='api/roles/', then=db_models.Value('Settings')),
                db_models.When(end_point__icontains='api/company/', then=db_models.Value('Company Profile')),
                db_models.When(end_point__icontains='api/directory/', then=db_models.Value('Employee Management')),
                db_models.When(end_point__icontains='api/pss_calendar/', then=db_models.Value('Calendar')),
                db_models.When(end_point__icontains='api/leave/', then=db_models.Value('Leave')),
                db_models.When(end_point__icontains='api/attendance/', then=db_models.Value('Attendance')),
                db_models.When(end_point__icontains='api/performance_management/', then=db_models.Value('Performance Review')),
                db_models.When(end_point__icontains='api/investment_declaration/', then=db_models.Value('Saving Declaration')),
                db_models.When(end_point__icontains='api/payroll/', then=db_models.Value('Payroll')),
                default=db_models.Value('-'),
                output_field=db_models.CharField()
            ),
            action = db_models.Case(
                db_models.When(method='PUT', then=db_models.Value('Updated')),
                db_models.When(method ='PATCH', then=db_models.Value('Updated')),
                db_models.When(method ='POST', then=db_models.Value('Created')),
                db_models.When(method ='DELETE', then=db_models.Value('Deleted')),
                default=db_models.Value('-'),
                output_field=db_models.CharField()
            )
        ).values(
            "id","user__username", "user_name", "end_point","ip_address","payload","old_data",
            "method","error_details","is_success_entry","company_name","module_name","created_at__date","action", "changed_data_at","model_name"
        ).order_by('-created_at')
            
        data_df = pd.DataFrame(data, columns=["id","user__username", "user_name", "end_point","ip_address","payload","old_data",
            "method","error_details","is_success_entry","company_name","module_name","created_at__date","action", "changed_data_at","model_name"])
        data_df.old_data = data_df.old_data.apply(lambda x: self.parse_json(x))
        data_df.payload = data_df.payload.apply(lambda x: self.parse_json(x))
        data_df['changes'] = data_df.apply(lambda x: DeepDiff(x['old_data'], x['payload']), axis=1)
        data_df['old_data'] = data_df.apply(lambda obj : self.generate_old_new_data(obj['changes'], 'old') if obj["method"] != "POST" else self.clean_list(obj['old_data']), axis=1)
        data_df['payload'] = data_df.apply(lambda obj : self.generate_old_new_data(obj['changes'], 'new') if obj["method"] != "POST" else self.clean_list(obj['payload']), axis=1)
        data_df['action'] = data_df.apply(lambda obj: 'logged in' if obj['module_name'] == 'Login' else obj['action'],axis=1)
        data_df['old_data'] = data_df.apply(lambda obj: self.remove_keys(obj["old_data"]) if obj["old_data"] else None,axis=1)
        data_df['payload'] = data_df.apply(lambda obj: self.remove_keys(obj["payload"]) if obj["payload"] else None,axis=1)
        data_df['old_data'] = data_df.apply(lambda obj: 'logged in' if obj['module_name'] == 'Login' else obj['old_data'],axis=1)
        data_df['old_data'] = data_df.apply(lambda obj: ('Check Out' if obj['model_name'] == 'Attendance History' and 'time_out' in obj['payload'] else 'Check In') 
                                                if (obj['payload'] and obj['model_name'] == 'Attendance History') else obj['old_data'],axis=1)
        data_df.drop(['changes'], axis=1, inplace=True)
        data_df = data_df.loc[(data_df['payload'] != 'Nothing Updated') | (data_df['old_data'] != 'Nothing Updated')]
        data_df.old_data = data_df.old_data.fillna('No Records Found')
        if not data_df.empty:
            data_df['created_at__date'] = data_df.apply(lambda obj: obj['created_at__date'].strftime('%d-%m-%Y') if obj['created_at__date'] else obj['created_at__date'], axis=1)
            columns_to_drop = ['id', 'error_details', 'changed_data_at', 'user_name', 'method', 'is_success_entry', 'company_name', 'end_point']
            data_df.drop(columns_to_drop, axis=1, inplace=True)

            data_df = data_df.rename(columns = {'user__username':'Host By', 'payload':'New Data', 
                                                'created_at__date':'Date', 'model_name':'Module Name',
                                                'ip_address':'Ip Address', 'module_name':'Field', 'action':'Action',
                                                'old_data':'Old Data'
                                                })
            new_order = ['Date', 'Ip Address', 'Host By', 'Field', 'Action', 'Module Name', 'Old Data', 'New Data']
            data_df = data_df.reindex(columns=new_order)
            data_df['S.NO'] = range(1, len(data_df) + 1)
            data_df.set_index('S.NO', inplace=True) 
        
        
        if not data_df.empty:  
            excel_file = BytesIO()
            writer = pd.ExcelWriter(excel_file, engine='xlsxwriter')
            data_df.to_excel(writer, sheet_name='Sheet1')  
            writer.save()
            excel_file.seek(0)

            if admin_emails:
                for data in admin_emails:
                    admin_email = data['official_email']
                    admin_name = data['user__username'].title()
                    admin_emp_number = data['work_details__employee_number']
                    # gender = data['gender']
                    tag = admin_emp_number if admin_emp_number else "-"
                    try:
                        body = f""" 
                
    Hello {admin_name} [{tag}],

    Kindly take a moment to review the attached detailed report for a comprehensive overview. 
    
    We are pleased to share the Daily Audit Report Log for {from_date.strftime('%d-%m-%Y')} , 
    
    Please refer the link for more information {domain}

    Thanks & Regards,
    {company_name.title()}.
                """
                        data = {
                            "subject": f"Daily Audit Report Log - {from_date.strftime('%d-%m-%Y')}",
                            "body": body,
                            "to_email": admin_email
                        }
                        if "commit" in sys.argv:
                            Util.send_email(data, xl_file=excel_file, file_name=f"Daily Audit Report Log - {from_date}")
                            try:
                                employee_data = {
                                        'phone_number':data['phone'],
                                        'subject': f"Daily Audit Report Log - {from_date.strftime('%d-%m-%Y')}",
                                        'body_text1' : f"We are pleased to share the Daily Audit Report Log for {from_date.strftime('%d-%m-%Y')} ",
                                        'body_text2' : " ",
                                        'url': f"{domain}",
                                        "company_name": company_name
                                        }
                                WhatsappMessage.whatsapp_message(employee_data)
                            except Exception as e:
                                logger.warning(f"Error while sending Whatsapp notificaton to {admin_name} about saving declaration : {e}")
                    except Exception as e:
                        print(f"exception in sending mail to {admin_email}:",e)
                print("Audit Report Mails sent successfully!")

        else:
            print("Dry Run!")
        

if __name__ == "__main__":
    company_id = 1
    AuditReportMails(company_id=company_id).main()

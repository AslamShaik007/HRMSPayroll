import sys
import os
import django
import logging

import pandas as pd
import numpy as np
from django.db import models as db_models
from io import BytesIO

sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]
    
from HRMSApp.utils import Util
from core.utils import timezone_now, get_domain
from directory.models import Employee, DocumentsTypes
from HRMSApp.models import Roles
from company_profile.models import CompanyDetails
from directory.models import EmployeeReportingManager

logger = logging.getLogger("django")
from core.whatsapp import WhatsappMessage


class EmployeeEmptyInfoToAdmin:
    
    def __init__(self,company_id):
        self.company_id = company_id
        
    def main(self):
        domain = get_domain(sys.argv[-1], sys.argv[1], 'directory')
        today = timezone_now().date()
        current_year = timezone_now().year
        # admin_emails = Roles.objects.filter(name="ADMIN",roles_employees__company_id = self.company_id, roles_employees__work_details__employee_status="Active").values("roles_employees__official_email","roles_employees__user__username")
        # to_email_list = [email[0] for email in admin_emails]
        company_name = CompanyDetails.objects.filter(id= 1).values("company_name").first()
        q_filters = db_models.Q(is_deleted = False,company_id = 1,
                                work_details__employee_status__in = ["Active","YetToJoin"],
                                )
        data = Employee.objects.filter(q_filters &
                        (db_models.Q(employeeworkrulerelation__isnull=True) | db_models.Q(employeeleaverulerelation__isnull=True) | db_models.Q(assignedattendancerules__isnull=True)  | 
                         db_models.Q(official_email__isnull=True) | db_models.Q(work_details__work_location__isnull=True) | db_models.Q(first_name__isnull=True) | 
                         db_models.Q(last_name__isnull=True) | db_models.Q(phone__isnull=True) | db_models.Q(date_of_join__isnull=True) |  db_models.Q(work_details__department__isnull=True) | db_models.Q(work_details__sub_department__isnull=True) |
                         db_models.Q(work_details__designation__isnull=True) | db_models.Q(employee__isnull=True) | db_models.Q(salary_details__ctc__isnull=True) | 
                         db_models.Q(salary_details__account_holder_name__isnull=True) | db_models.Q(salary_details__account_number__isnull=True) |
                         db_models.Q(salary_details__bank_name__isnull=True) | db_models.Q(salary_details__branch_name__isnull=True) | db_models.Q(salary_details__city__isnull=True) |
                         db_models.Q(salary_details__ifsc_code__isnull=True) | db_models.Q(salary_details__account_type__isnull=True) | db_models.Q(emp_compliance_detail__uan_num__isnull=True) | 
                         ~db_models.Q(employee_document_ids__document_type__document_type=20, employee_document_ids__is_deleted=False) | ~db_models.Q(employee_document_ids__document_type__document_type=10, employee_document_ids__is_deleted=False)
                        )).annotate(
            work_rule = db_models.Case(
                                    db_models.When(employeeworkrulerelation__isnull=True, then=db_models.Value("Not Assigned")),
                                    default=db_models.Value("Assigned"), output_field=db_models.CharField()
                                ),
            leave_rule = db_models.Case(
                        db_models.When(db_models.Q(employeeleaverulerelation__isnull=False, employeeleaverulerelation__is_deleted=False, 
                                                   employeeleaverulerelation__session_year__session_year=current_year), then=db_models.Value("Assigned")),
                        default=db_models.Value("Not Assigned"), output_field=db_models.CharField()
                    ),
            attendance_rule = db_models.Case(
                        db_models.When(assignedattendancerules__isnull=True, then=db_models.Value("Not Assigned")),
                        default=db_models.Value("Assigned"), output_field=db_models.CharField()
                    ),
            email = db_models.Case(
                        db_models.When(official_email__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            work_location = db_models.Case(
                        db_models.When(work_details__work_location__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            emp_first_name = db_models.Case(
                        db_models.When(first_name__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            emp_last_name = db_models.Case(
                        db_models.When(last_name__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            emp_phone = db_models.Case(
                        db_models.When(phone__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            joined_date = db_models.Case(
                        db_models.When(date_of_join__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            # grade = db_models.Case(
            #             db_models.When(work_details__employee_grade__isnull=True, then=db_models.Value("No")),
            #             default=db_models.Value("Yes"), output_field=db_models.CharField()
            #         ),
            dept = db_models.Case(
                        db_models.When(work_details__department__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            sub_dept = db_models.Case(
                        db_models.When(work_details__sub_department__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            emp_designation = db_models.Case(
                        db_models.When(work_details__designation__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            manager_info = db_models.Case(
                        db_models.When(employee__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            emp_aadhar = db_models.Case(
                        db_models.When(db_models.Q(employee_document_ids__document_type__document_type=20, employee_document_ids__is_deleted=False), then=db_models.Value("Yes")),
                        default=db_models.Value("No"), output_field=db_models.CharField()
                    ),
            emp_pan = db_models.Case(
                        db_models.When(db_models.Q(employee_document_ids__document_type__document_type=10, employee_document_ids__is_deleted=False), then=db_models.Value("Yes")),
                        default=db_models.Value("No"), output_field=db_models.CharField()
                    ),
            salary_ctc = db_models.Case(
                        db_models.When(salary_details__ctc__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            # monthly_ctc = db_models.Case(
            #             db_models.When(salary_details__salary__isnull=True, then=db_models.Value("No")),
            #             default=db_models.Value("Yes"), output_field=db_models.CharField()
            #         ),
            account_name = db_models.Case(
                        db_models.When(salary_details__account_holder_name__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            acc_number = db_models.Case(
                        db_models.When(salary_details__account_number__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            bank_acc_name = db_models.Case(
                        db_models.When(salary_details__bank_name__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            bank_branch_name = db_models.Case(
                        db_models.When(salary_details__branch_name__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            bank_city = db_models.Case(
                        db_models.When(salary_details__city__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            bank_ifsc_code = db_models.Case(
                        db_models.When(salary_details__ifsc_code__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            bank_account_type = db_models.Case(
                        db_models.When(salary_details__account_type__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            # emp_fixed_salry = db_models.Case(
            #             db_models.When(salary_details__fixed_salary__isnull=True, then=db_models.Value("No")),
            #             default=db_models.Value("Yes"), output_field=db_models.CharField()
            #         ),
            # emp_variable_pay = db_models.Case(
            #             db_models.When(salary_details__variable_pay__isnull=True, then=db_models.Value("No")),
            #             default=db_models.Value("Yes"), output_field=db_models.CharField()
            #         ),

            emp_uan_num = db_models.Case(
                        db_models.When(emp_compliance_detail__uan_num__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
        )
        objs = data
        if "commit" in sys.argv and objs.exists():
            managers = EmployeeReportingManager.objects.filter(is_deleted=False,manager__work_details__employee_status="Active").values('manager_id', 'manager__official_email', 'manager__user__username','manager__work_details__employee_number').distinct()
            for manager in managers:
                m_data = objs.filter(employee__manager_id=manager['manager_id'], employee__is_deleted=False).values(
                    "company_id","user__username","work_details__employee_number","work_details__department__name","work_rule","leave_rule",
                    "attendance_rule","email","work_location","emp_first_name","emp_last_name","emp_phone","joined_date",
                    "dept","sub_dept","emp_designation","manager_info","emp_aadhar","emp_pan","salary_ctc","account_name","acc_number","bank_acc_name","bank_branch_name",
                    "bank_city","bank_ifsc_code","bank_account_type","emp_uan_num",
                )
                df_data = pd.DataFrame(m_data, columns =["company_id","user__username","work_details__employee_number","work_details__department__name",
                                                "work_rule","leave_rule","attendance_rule","email","work_location","emp_first_name","emp_last_name",
                                                "emp_phone","joined_date","dept","sub_dept","emp_designation","manager_info","emp_aadhar","emp_pan","salary_ctc",
                                                "account_name","acc_number","bank_acc_name","bank_branch_name","bank_city","bank_ifsc_code",
                                                "bank_account_type","emp_uan_num"
                                                    ])
                data = df_data.groupby('work_details__employee_number').agg({
                                                    'user__username':'first',
                                                    'work_details__department__name':'first',
                                                    'work_rule':'first',
                                                    'leave_rule': list,
                                                    'attendance_rule':'first',
                                                    'email':'first',
                                                    'work_location':'first',
                                                    'emp_first_name':'first',
                                                    'emp_last_name':'first',
                                                    'emp_phone':'first',
                                                    'joined_date':'first',
                                                    'dept':'first',
                                                    'sub_dept':'first',
                                                    'emp_designation':'first',
                                                    'manager_info':'first',
                                                    'emp_aadhar': list,
                                                    'emp_pan': list,
                                                    'salary_ctc':'first',
                                                    'account_name':'first',
                                                    'acc_number':'first',
                                                    'bank_acc_name':'first',
                                                    'bank_branch_name':'first',
                                                    'bank_city':'first',
                                                    'bank_ifsc_code':'first',
                                                    'bank_account_type':'first',
                                                    'emp_uan_num':'first',
                                                    }).reset_index()
                # op_data = df_data.drop_duplicates().reset_index(drop=True)
                data['leave_rule'] = data.leave_rule.apply(lambda x: 'Assigned' if 'Assigned' in x else 'Not Assigned')
                data['emp_aadhar'] = data.emp_aadhar.apply(lambda x: 'Yes' if 'Yes' in x else 'No')
                data['emp_pan'] = data.emp_pan.apply(lambda x: 'Yes' if 'Yes' in x else 'No')
                data.rename(columns={"work_details__employee_number":"Emp Id","user__username":"Employee Name","work_details__department__name":"Department","work_rule":"Work Week",
                                    "leave_rule":"Leave Rule","attendance_rule":"Attendance Rule","email":"Official Email","emp_first_name":"First Name","emp_last_name":"Last Name",
                                    "emp_phone":"Phone Number","joined_date":"DOJ","dept":"Depatment","sub_dept":"Sub Department","emp_designation":"Designation",
                                    "manager_info":"Reporting Manager","emp_aadhar":"Aadhaar Card","emp_pan":"PAN Card","salary_ctc":"CTC","account_name":"Account Holder's Name","acc_number":"Account Number",
                                    "acc_number":"Account Number","bank_acc_name":"Bank Name","bank_branch_name":"Branch Name","bank_city":"City","bank_ifsc_code":"IFSC Code",
                                    "bank_account_type":"Account Type","emp_uan_num":"UAN Number",
                                    }, inplace=True)
                data['S.NO'] = range(1, len(data) + 1)
                data.set_index('S.NO', inplace=True)
                excel_file = BytesIO()
                writer = pd.ExcelWriter(excel_file, engine='xlsxwriter')
                data.to_excel(writer, sheet_name='Sheet1') 
                print("writer",writer)
                writer.save()
                excel_file.seek(0)
                print(excel_file)
                try:
                    manager_email = manager['manager__official_email']
                    manager_name = manager['manager__user__username'].title()
                    rp_emp_number = manager['manager__work_details__employee_number']
                    tag = rp_emp_number if rp_emp_number else "-"
                    body = f""" 
    Hello {manager_name} [{tag}],

    I wanted to bring to your attention that certain employee information is still missing or incomplete in the HRMS portal.

    Ensuring accuracy in our records is crucial, and I kindly request your assistance in addressing and updating the missing details.

    Thanks & Regards,
    {company_name['company_name'].title()}
                """
                    data = {
                        "subject": "Incomplete Employee Information in HRMS Portal",
                        "body": body,
                        "to_email": manager_email,                         
                    }
                    Util.send_email(data, xl_file=excel_file, file_name=f"Employee Empty Records - {today}")
                    # manager Whatsapp notifications
                    try:
                        employee_data = {
                                'phone_number': manager['manager__phone'],
                                'subject': 'Incomplete Employee Information in HRMS Portal',
                                'body_text1' : "Some employees information is incomplete in the HRMS portal",
                                'body_text2' : "I kindly request your assistance in addressing and updating the missing details.",
                                'url': f"{domain}",
                                "company_name": company_name
                                }
                        WhatsappMessage.whatsapp_message(employee_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {manager_name} for filling employee empty info: {e}")

                except Exception as e:
                    print(f"Exception in sending mails: {e}")
                
            print("Successfully Sent Employee Details!")
        print("Dry Run!") 
            
if __name__ == "__main__":
    company_id = 1
    EmployeeEmptyInfoToAdmin(company_id=company_id).main()
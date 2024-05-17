import traceback
import datetime
import pandas as pd

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db import models as db_models
from django.db.models.functions import Concat
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models as db_models

from directory.models import Employee, EmployeeTypes, RelationshipTypes, QualificationTypes, CourseTypes, CertificationCourseTypes, ManagerType, EmployeeReportingManager, DocumentsTypes
from company_profile.models import BankAccountTypes
from core.utils import excel_converter, error_response, timezone_now


class EmployeeExportViewV2(APIView):

    model = Employee

    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            fields = [item.replace(' ', '_') for item in data.get('fields')]
            employee_ids = data.get('id')
            current_day = timezone_now().date()
            annotations = {
                "ID" : db_models.F('work_details__employee_number'),
                "Employee_Name" : Concat("first_name",db_models.Value(" "),"middle_name",db_models.Value(" "),"last_name", db_models.Value(" ")),
                "Department" : db_models.F('work_details__department__name'),
                "Sub_Department" : db_models.F('work_details__sub_department__name'),
                "Designation" : db_models.F('work_details__designation__name'),
                "Manager" : ArrayAgg(
                        db_models.functions.Concat(
                            db_models.F('employee__manager__first_name'), db_models.Value(" "), db_models.F('employee__manager__last_name'),
                            output_field=db_models.CharField()   
                        ),
                        filter=db_models.Q(employee__isnull=False, employee__manager_type__manager_type=10, employee__is_deleted=False, employee__manager__work_details__employee_status='Active'),
                        distinct=True),
                "Secondary_Managers" : ArrayAgg(
                        db_models.functions.Concat(
                            db_models.F('employee__manager__first_name'), db_models.Value(" "), db_models.F('employee__manager__last_name'),
                            output_field=db_models.CharField()   
                        ),
                        filter=db_models.Q(employee__isnull=False, employee__manager_type__manager_type=20, employee__is_deleted=False, employee__manager__work_details__employee_status='Active'),
                        distinct=True),
                "Job_Title" : db_models.F('work_details__job_title'),
                "Date_of_Joining" : db_models.Func(db_models.F("date_of_join"), db_models.Value("dd-mm-yyyy"), function="to_char", output_field=db_models.CharField()),
                "Work_Location" : db_models.F('work_details__work_location'),
                "HRMS_Status" : db_models.F('work_details__employee_status'),
                "Payroll_Status" : db_models.Case(
                            db_models.When(payroll_status=True, then=db_models.Value("Active")),
                            db_models.When(payroll_status=False, then=db_models.Value("InActive")),
                            default=db_models.Value('Hold')
                        ),
                "Employee_Type" : db_models.Case(
                            *[db_models.When(work_details__employee_type__employee_type=i[0], then=db_models.Value(i[1])) for i in EmployeeTypes.EMPLOYEE_TYPE_CHOICES],
                            default=db_models.Value(''), output_field=db_models.CharField()),
                "Probation_Period_Days" : db_models.F('work_details__probation_period'),
                "Grade" : db_models.F('work_details__employee_grade__grade'),
                "Phone" : db_models.F('phone'),
                "Email" :  db_models.F('official_email'),
                "Personal_Email_ID" : db_models.F('personal_email'),
                "Emergency_Contact_Name" : ArrayAgg(
                        db_models.F('employee_emargency_contact__name'),
                        filter=db_models.Q(employee_emargency_contact__isnull=False, employee_emargency_contact__is_deleted=False),
                        distinct=True),
                "Emergency_Contact_Number" : ArrayAgg(
                        db_models.F('employee_emargency_contact__phone_number'),
                        filter=db_models.Q(employee_emargency_contact__isnull=False, employee_emargency_contact__is_deleted=False),
                        distinct=True),
                "CTC" : db_models.F('salary_details__ctc'),
                "Attendance_Rules" : db_models.F('assignedattendancerules__attendance_rule__name'),
                "Workweek_Rules":db_models.F('employeeworkrulerelation__work_rule__name'),
                "Leave_Rules" : ArrayAgg(db_models.F('employeeleaverulerelation__leave_rule__name'),
                                         filter =db_models.Q(employeeleaverulerelation__leave_rule__isnull=False, employeeleaverulerelation__effective_date__lte=current_day,
                                                             employeeleaverulerelation__session_year__session_year=current_day.year), distinct=True),
                "Role" : ArrayAgg(db_models.F('roles__name'),filter =db_models.Q(roles__isnull =False), distinct=True),
                "Date_of_Birth" : db_models.Func(db_models.F("date_of_birth"), db_models.Value("dd-mm-yyyy"), function="to_char", output_field=db_models.CharField()), 
                
            }
            
            required_annotations = {key: annotations.get(key) for key in fields if key in annotations}
            
            employees = self.model.objects.filter(id__in=employee_ids).annotate(**required_annotations).values(*fields)
            
            employee_df = pd.DataFrame(employees)
            if 'Manager' in employee_df.columns:
                employee_df.Manager = employee_df.Manager.apply(lambda m:', '.join(m) if m else '')   
            if 'Leave_Rules' in employee_df.columns :
                employee_df.Leave_Rules = employee_df.Leave_Rules.apply(lambda m:', '.join(m) if m else '')
            if 'Role' in  employee_df.columns :
                employee_df.Role = employee_df.Role.apply(lambda m:', '.join(m) if m else '')
                
            employee_df = employee_df.rename(columns = {'Sub_Department':'Sub Department','Job_Title':'Job Title',
                                                        'Date_of_Joining':'Date of Joining','Work_Location':'Work Location',
                                                        'Probation_Period':'Probation Period','Emergency_Contact_Name':'Emergency Contact Name',
                                                        'Emergency_Contact_Number':'Emergency Contact Number','Attendance_Rules':'Attendance Rules',
                                                        'Workweek_Rules':'Workweek Rules','Date_of_Birth':'Date of Birth','Leave_Rules':'Leave Rules',
                                                        'Employee_Name':'Name','Employee_Type':'Employee Type','HRMS_Status':'HRMS Status','Payroll_Status':'Payroll Status'})
            
            employee_df['S.NO'] = range(1, len(employee_df) + 1)
            employee_df.set_index('S.NO', inplace=True)  

            file_name = f"employee_data_{timezone_now().date()}.xlsx"
            return excel_converter(employee_df,file_name)
        
        except Exception as e:
            return Response(
                error_response(str(e), 'Some thing went wrong', 400),
                status=status.HTTP_400_BAD_REQUEST
            )
            

class EmployeeDynamicReportView(APIView):
    
    model = Employee
    def post(self, request, *args, **kwargs):
        try:
            user_info = request.user.employee_details.first()
            company_id = user_info.company_id
            employee_id = user_info.id   
            data = request.data
            fields = [item.replace(' ', '_') for item in data.get('fields')]
            q_filter = db_models.Q()
            if employee_ids := data.get('id', ''):
                q_filter &= db_models.Q(id__in=employee_ids, company_id=company_id)
            elif data.get('status',''):
                emp_status = data.get('status')
                q_filter &= db_models.Q(company_id=company_id, work_details__employee_status=emp_status)
            else:
                q_filter &= db_models.Q(company_id=company_id)
            employee_checkd_in = request.user.employee_details.first()
            employee_checkd_in_role = employee_checkd_in.roles.first().name
            if employee_checkd_in_role in ['MANAGER', 'TEAM LEAD']:
                check_ids = list(EmployeeReportingManager.objects.filter(manager_id=employee_checkd_in.id, is_deleted=False).values_list("employee_id", flat=True))
                check_ids.append(employee_checkd_in.id)
                q_filter &= db_models.Q(id__in=check_ids)
            
            annotations = {
                # "Name" : db_models.F('first_name'),
                # "Middle_Name" : db_models.F('middle_name'),
                # "Last_Name" : db_models.F('last_name'),
                "Full_Name" : db_models.F('user__username'),
                "Marriage_Anniversary":db_models.Func(db_models.F("anniversary_date"), db_models.Value("dd-mm-yyyy"), function="to_char", output_field=db_models.CharField()),
                "Date_of_Birth" : db_models.Func(db_models.F("date_of_birth"), db_models.Value("dd-mm-yyyy"), function="to_char", output_field=db_models.CharField()),
                "Gender"  : db_models.F('gender'),
                "Role" : ArrayAgg(db_models.F('roles__name'),filter =db_models.Q(roles__isnull =False), distinct=True),
                "Blood_group" : db_models.F('blood_group'),
                "Marital_Status" : db_models.F('marital_status'),
                "Offical_Email" :  db_models.F('official_email'),
                "Personal_Email" : db_models.F('personal_email'),
                "Phone_No" : db_models.F('phone'),
                "Alternate_No" : db_models.F('alternate_phone'),

                "Employee_ID" : db_models.F('work_details__employee_number'),
                "Employee_Type" : db_models.Case(
                            *[db_models.When(work_details__employee_type__employee_type=i[0], then=db_models.Value(i[1])) for i in EmployeeTypes.EMPLOYEE_TYPE_CHOICES],
                            default=db_models.Value(''), output_field=db_models.CharField()),
                "HRMS_Status" : db_models.F('work_details__employee_status'),
                "Date_of_Joining" : db_models.Func(db_models.F("date_of_join"), db_models.Value("dd-mm-yyyy"), function="to_char", output_field=db_models.CharField()),
                "Work_Location" : db_models.F('work_details__work_location'),
                "Payroll_Status" : db_models.Case(
                            db_models.When(payroll_status=True, then=db_models.Value("Active")),
                            db_models.When(payroll_status=False, then=db_models.Value("InActive")),
                            default=db_models.Value('Hold')
                        ),
                "Work_Entity" : db_models.F('work_entity'),
                "Payroll_Entity" : db_models.F('payroll_entity'),
                "Work_Experience_year" : db_models.F('work_details__experience_in_years'),
                "Work_Experience_months" : db_models.F('work_details__experience_in_months'),
                "Probation_Period_Days" : db_models.F('work_details__probation_period'),

                "Resignation_Date" : db_models.Func(db_models.F("resignation_info__resignation_date"), db_models.Value("dd-mm-yyyy"), function="to_char", output_field=db_models.CharField()),
                "Resignation_Comments" : db_models.F('resignation_info__resignation_status'),
                "Notice_Period" : db_models.F('resignation_info__notice_period'),
                "Last_Working_Date" : db_models.Func(db_models.F("resignation_info__last_working_day"), db_models.Value("dd-mm-yyyy"), function="to_char", output_field=db_models.CharField()), 
                "Primary_Manager" : ArrayAgg('employee__manager__user__username',
                        filter=db_models.Q(employee__isnull=False, employee__is_deleted=False, employee__manager__work_details__employee_status='Active',
                                           employee__manager_type__manager_type=ManagerType.PRIMARY),
                        distinct=True),
                "Secondary_Manager" : ArrayAgg('employee__manager__user__username',
                        filter=db_models.Q(employee__isnull=False, employee__is_deleted=False, employee__manager__work_details__employee_status='Active',
                                           employee__manager_type__manager_type=ManagerType.SECONDARY),
                        distinct=True),
                "Direct_Reports" : ArrayAgg('employee_manager__employee__user__username',
                        filter=db_models.Q(employee_manager__isnull=False, employee_manager__is_deleted=False, employee_manager__employee__work_details__employee_status='Active'),
                        distinct=True),
                "Educational_Info" : ArrayAgg(
                        db_models.expressions.Func(
                            db_models.Value('qualification'), db_models.Case(
                                *[db_models.When(employee_education_details__qualification__qualification_type=i[0], then=db_models.Value(i[1])) for i in QualificationTypes.QUALIFICATION_TYPE_CHOICES],
                                default=db_models.Value(''), output_field=db_models.CharField()),
                            db_models.Value('course_name'), "employee_education_details__course_name",
                            db_models.Value('course_type'), db_models.Case(
                                *[db_models.When(employee_education_details__course_type__course_type=i[0], then=db_models.Value(i[1])) for i in CourseTypes.COURSE_TYPE_CHOICES],
                                default=db_models.Value(''), output_field=db_models.CharField()),
                            db_models.Value('stream'), "employee_education_details__stream",
                            db_models.Value('course_start_date'), db_models.Func(db_models.F("employee_education_details__course_start_date"), 
                                                                                 db_models.Value("dd-mm-yyyy"), 
                                                                                 function="to_char", 
                                                                                 output_field=db_models.CharField()),
                            db_models.Value('course_end_date'), db_models.Func(db_models.F("employee_education_details__course_end_date"), 
                                                                                 db_models.Value("dd-mm-yyyy"), 
                                                                                 function="to_char", 
                                                                                 output_field=db_models.CharField()),
                            db_models.Value('college_name'), "employee_education_details__college_name",
                            db_models.Value('university_name'), "employee_education_details__university_name",
                            function="jsonb_build_object",
                            output_field=db_models.JSONField()
                        ),
                            distinct=True,
                            filter = db_models.Q(
                                employee_education_details__isnull=False, employee_education_details__is_deleted=False)
                        ),
                
                "Educational_Documents" : ArrayAgg(
                        db_models.expressions.Func(
                            db_models.Value('course_type'), db_models.Case(
                                *[db_models.When(employee_certification__course_type__course_type=i[0], then=db_models.Value(i[1])) for i in CertificationCourseTypes.CERTIFICATION_TYPE_CHOICES],
                                default=db_models.Value(''), output_field=db_models.CharField()),
                            db_models.Value('certification_title'), "employee_certification__certification_title",
                            db_models.Value('is_verified'), "employee_certification__is_verified",
                            db_models.Value('updated_by'), "employee_certification__updated_by__username",
                            function="jsonb_build_object",
                            output_field=db_models.JSONField()
                        ),
                            distinct=True,
                            filter = db_models.Q(
                                employee_certification__isnull=False,employee_certification__is_deleted=False)
                        ),
                "Family_Details" : ArrayAgg(
                        db_models.expressions.Func(
                            db_models.Value('relationship'), db_models.Case(
                                *[db_models.When(employee_family_details__relationship__relationship_type=i[0], then=db_models.Value(i[1])) for i in RelationshipTypes.RELATIONSHIP_TYPE_CHOICES],
                                default=db_models.Value(''), output_field=db_models.CharField()),
                            db_models.Value('Family_Member_Name'), "employee_family_details__name",
                            db_models.Value('date_of_birth'), db_models.Func(db_models.F("employee_family_details__date_of_birth"), 
                                                                                 db_models.Value("dd-mm-yyyy"), 
                                                                                 function="to_char", 
                                                                                 output_field=db_models.CharField()),
                            db_models.Value('dependent'), "employee_family_details__dependent",
                            db_models.Value('updated_by'), "employee_family_details__updated_by__username",
                            function="jsonb_build_object",
                            output_field=db_models.JSONField()
                        ),
                            distinct=True,
                            filter = db_models.Q(
                                employee_family_details__isnull=False, employee_family_details__is_deleted=False)
                        ),
                "Emergency_Contact" : ArrayAgg(
                        db_models.expressions.Func(
                            db_models.Value('relationship'), db_models.Case(
                                *[db_models.When(employee_emargency_contact__relationship__relationship_type=i[0], then=db_models.Value(i[1])) for i in RelationshipTypes.RELATIONSHIP_TYPE_CHOICES],
                                default=db_models.Value(''), output_field=db_models.CharField()),
                            db_models.Value('Emargency_Contact_Name'), "employee_emargency_contact__name",
                            db_models.Value('phone_number'), "employee_emargency_contact__phone_number",
                            function="jsonb_build_object",
                            output_field=db_models.JSONField()
                        ),
                            distinct=True,
                            filter = db_models.Q(
                                employee_emargency_contact__isnull=False, employee_emargency_contact__is_deleted=False)
                        ),
                "Attendance_Rules" : db_models.F('assignedattendancerules__attendance_rule__name'),
                "Workweek_Rules":db_models.F('employeeworkrulerelation__work_rule__name'),
                "Leave_Rules" : ArrayAgg(db_models.F('employeeleaverulerelation__leave_rule__name'),filter =db_models.Q(employeeleaverulerelation__leave_rule__isnull = False), distinct=True),
                "Current_Address":    db_models.expressions.Func(
                        db_models.Value('address'), Concat("address_details__current_address_line1",db_models.Value(" "),"address_details__current_address_line2"),
                        db_models.Value('country'), "address_details__current_country",
                        db_models.Value('state'), "address_details__current_state",
                        db_models.Value('city'), "address_details__current_city",
                        db_models.Value('pincode'), "address_details__current_pincode",
                        db_models.Value('house_type'), "address_details__current_house_type",
                        db_models.Value('statying_since'), "address_details__current_staying_since",
                        db_models.Value('living_in_current_city_since'), "address_details__living_in_current_city_since",
                        db_models.Value('other_house_type'), "address_details__other_house_type",
                        function="jsonb_build_object",
                        output_field=db_models.JSONField()
                    ),
                "Permanent_Address":    db_models.expressions.Func(
                        db_models.Value('address'), Concat("address_details__permanent_address_line1",db_models.Value(" "),"address_details__permanent_address_line2"),
                        db_models.Value('country'), "address_details__permanent_country",
                        db_models.Value('state'), "address_details__permanent_state",
                        db_models.Value('city'), "address_details__permanent_city",
                        db_models.Value('pincode'), "address_details__permanent_pincode",
                        function="jsonb_build_object",
                        output_field=db_models.JSONField()
                    ),
                "Department" : db_models.F('work_details__department__name'),
                "Sub_Department" : db_models.F('work_details__sub_department__name'),
                "Designation" : db_models.F('work_details__designation__name'),
                "Job_Title" : db_models.F('work_details__job_title'), 
                "PF_Details":db_models.expressions.Func(
                        db_models.Value('PF_Number'), "emp_compliance_detail__pf_num",
                        db_models.Value('UAN_Number'), "emp_compliance_detail__uan_num",
                        db_models.Value('ESI_Number'), "emp_compliance_detail__esi_num",
                        db_models.Value('Nominee_Name'), "emp_compliance_detail__nominee_name",
                        db_models.Value('Nominee_Relation'), "emp_compliance_detail__nominee_rel",
                        db_models.Value('Nominee_DOB'), "emp_compliance_detail__nominee_dob",
                        function="jsonb_build_object",
                        output_field=db_models.JSONField()
                    ),
                       
                "Salary_Bank_Info":    db_models.expressions.Func(
                        db_models.Value('Account_Holder_Name'), "salary_details__account_holder_name",
                        db_models.Value('Bank_Name'), "salary_details__bank_name",
                        db_models.Value('Bank_City'), "salary_details__city",
                        db_models.Value('Branch_Name'), "salary_details__branch_name",
                        db_models.Value('IFSC_Code'), "salary_details__ifsc_code",
                        db_models.Value('Account_Number'), "salary_details__account_number",
                        db_models.Value('Account_Type'), db_models.Case(
                            *[db_models.When(salary_details__account_type__account_type=i[0], then=db_models.Value(i[1])) for i in BankAccountTypes.ACCOUNT_TYPE_CHOICES],
                            default=db_models.Value(''), output_field=db_models.CharField()),
                        db_models.Value('Fixed_Salary'), "salary_details__fixed_salary",
                        db_models.Value('Variable_Pay'), "salary_details__variable_pay",
                        function="jsonb_build_object",
                        output_field=db_models.JSONField()
                    ),
                "Signed_In" : db_models.Case(
                    db_models.When(is_sign_up=True, then=db_models.Value("Yes")),
                    db_models.When(is_sign_up=False, then=db_models.Value("No")),
                    default = db_models.Value('No'),output_field=db_models.CharField()
                ),
                "Work_Docs": ArrayAgg(
                        db_models.expressions.Func(
                        db_models.Value('name'), "employee_documentation_work__document_title",
                        db_models.Value('uploaded by'), "employee_documentation_work__created_by__username",
                        db_models.Value('document_description'), "employee_documentation_work__document_description",
                        function="jsonb_build_object",
                        output_field=db_models.JSONField(),
                        ),
                            distinct=True,
                            filter = db_models.Q(
                                employee_documentation_work__isnull=False, employee_documentation_work__is_deleted=False)
                        ),
                "Uploaded_Documents" : ArrayAgg(
                        db_models.expressions.Func(
                        db_models.Value('type'), db_models.Case(
                            *[db_models.When(employee_document_ids__document_type__document_type=i[0], then=db_models.Value(i[1])) for i in DocumentsTypes.DOCUMENT_TYPE_CHOICES],
                            default=db_models.Value(''), output_field=db_models.CharField()),
                        db_models.Value('verification'), db_models.Case(
                                        db_models.When(employee_document_ids__is_verified=True, then=db_models.Value("Verified")),
                                        db_models.When(employee_document_ids__is_verified=False, then=db_models.Value("Not Verified")),
                                        default = db_models.Value('Not Verified'),output_field=db_models.CharField()
                        ),
                        db_models.Value('id'), "employee_document_ids__document_number",
                        db_models.Value('uploaded by'), "employee_document_ids__created_by__username",
                        # db_models.Value('photo_id'), "employee_document_ids__photo_id",
                        # db_models.Value('date_of_birth'), "employee_document_ids__date_of_birth",
                        # db_models.Value('current_address'), "employee_document_ids__current_address",
                        # db_models.Value('parmanent_address'), "employee_document_ids__parmanent_address",
                        # db_models.Value('document_description'), "employee_document_ids__document_description",
                        # db_models.Value('document_submission_date'), "employee_document_ids__document_submission_date",
                        function="jsonb_build_object",
                        output_field=db_models.JSONField(),
                        ),
                            distinct=True,
                            filter = db_models.Q(
                                employee_document_ids__isnull=False, employee_document_ids__is_deleted=False)
                        ),
                "CTC" : db_models.F('salary_details__ctc')
                
            }


            

            required_annotations = {key: annotations.get(key) for key in fields if key in annotations}
            employees = self.model.objects.filter(q_filter).annotate(**required_annotations).values(*fields)
            
            employee_df = pd.DataFrame(employees)
            if 'Primary_Manager' in employee_df.columns:
                employee_df.Primary_Manager = employee_df.Primary_Manager.apply(lambda m:', '.join(m) if m else '')   
            if 'Secondary_Manager' in employee_df.columns:
                employee_df.Secondary_Manager = employee_df.Secondary_Manager.apply(lambda m:', '.join(m) if m else '')   
            if 'Leave_Rules' in employee_df.columns :
                employee_df.Leave_Rules = employee_df.Leave_Rules.apply(lambda m:', '.join(m) if m else '')
            if 'Role' in  employee_df.columns :
                employee_df.Role = employee_df.Role.apply(lambda m:', '.join(m) if m else '')
            if 'Direct_Reports' in  employee_df.columns :
                employee_df.Direct_Reports = employee_df.Direct_Reports.apply(lambda m:', '.join(m) if m else '')
            employee_df['S.NO'] = range(1, len(employee_df) + 1)
            employee_df.set_index('S.NO', inplace=True)  

            file_name = f"employee_dynamic_data_{timezone_now().date()}.xlsx"
            return excel_converter(employee_df,file_name)
        
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing Went wrong", 400),
                status=status.HTTP_400_BAD_REQUEST
            )

class EmployerDynamicReportView(APIView):
    
    model = Employee
    def post(self, request, *args, **kwargs):
        try:
            user_info = request.user.employee_details.first()
            company_id = user_info.company_id  
            data = request.data
            fields = [item.replace(' ', '_') for item in data.get('fields')]
            reports = ['Checked_In']
            if not any(i in fields for i in reports):
                ms = "Please Select at Least One Report"
                return Response(
                    error_response(ms, ms, 400),
                    status=status.HTTP_400_BAD_REQUEST
                )
            emp_status = data.get('status','Active')
            q_filter = db_models.Q(company_id=company_id, work_details__employee_status=emp_status)
            if data.get('date',''):
                check_in_date = datetime.datetime.strptime(data.get('date'), "%Y-%m-%d").date()
            employee_checkd_in = request.user.employee_details.first()
            employee_checkd_in_role = employee_checkd_in.roles.first().name
            if employee_checkd_in_role in ['MANAGER', 'TEAM LEAD']:
                check_ids = list(EmployeeReportingManager.objects.filter(manager_id=employee_checkd_in.id, is_deleted=False).values_list("employee_id", flat=True))
                check_ids.append(employee_checkd_in.id)
                q_filter &= db_models.Q(id__in=check_ids)
            
            annotations = {
                        "Full_Name" : db_models.F('user__username'),
                        "Gender"  : db_models.F('gender'),
                        "Employee_ID" : db_models.F('work_details__employee_number'),
                        "Department" : db_models.F('work_details__department__name'),
                        "Designation" : db_models.F('work_details__designation__name'),
                        "Primary_Manager" : ArrayAgg('employee__manager__user__username',
                                    filter=db_models.Q(employee__isnull=False, employee__is_deleted=False, employee__manager__work_details__employee_status='Active',
                                                    employee__manager_type__manager_type=ManagerType.PRIMARY),
                                    distinct=True),
                        "Secondary_Manager" : ArrayAgg('employee__manager__user__username',
                                    filter=db_models.Q(employee__isnull=False, employee__is_deleted=False, employee__manager__work_details__employee_status='Active',
                                                    employee__manager_type__manager_type=ManagerType.SECONDARY),
                                    distinct=True),
                        "Checked_In":ArrayAgg(
                                db_models.expressions.Func(
                                db_models.Value('checked_in_date'), "clock_details__date_of_checked_in",
                                function="jsonb_build_object",
                                output_field=db_models.JSONField(),
                                ),
                                    distinct=True,
                                    filter = db_models.Q(
                                        clock_details__date_of_checked_in=check_in_date, clock_details__is_deleted=False)
                                ),
                        
                    }
            required_annotations = {key: annotations.get(key) for key in fields if key in annotations}
            employee_query = self.model.objects.filter(q_filter).annotate(**required_annotations).values(*fields)
            employee_df = pd.DataFrame(employee_query)
            if 'Primary_Manager' in employee_df.columns:
                employee_df.Primary_Manager = employee_df.Primary_Manager.apply(lambda m:', '.join(m) if m else '')   
            if 'Secondary_Manager' in employee_df.columns:
                employee_df.Secondary_Manager = employee_df.Secondary_Manager.apply(lambda m:', '.join(m) if m else '')  
            if 'Checked_In' in employee_df.columns:
                employee_df.Checked_In = employee_df.Checked_In.apply(lambda m:"Yes" if m else "No")  
                  
            employee_df['S.NO'] = range(1, len(employee_df) + 1)
            employee_df.set_index('S.NO', inplace=True) 
            
            file_name = f"employer_dynamic_data_{timezone_now().date()}.xlsx"
            return excel_converter(employee_df,file_name)
        
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing Went wrong", 400),
                status=status.HTTP_400_BAD_REQUEST
            )
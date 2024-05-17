import pandas as pd
import re
import datetime
import traceback
import django
import os
import logging

from django.db import models as db_models
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db.models.functions import Coalesce, Concat

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import (success_response, error_response, excel_converter, search_filter_decode, timezone_now, add_employee_ats, get_ats_permission,
                        TimestampToIST, TimestampToStrDateTime, TimestampToStr)
from core.custom_paginations import CustomPagePagination
from HRMSProject.multitenant_setup import MultitenantSetup

from .models import (
    Employee, EmployeeTypes, EmployeeDocuments, DocumentsTypes,
    EmployeeEducationDetails, QualificationTypes, CourseTypes,
    EmployeeCertifications, CertificationCourseTypes, EmployeeFamilyDetails, RelationshipTypes,
    EmployeeEmergencyContact, EmployeeDocumentationWork, EmployeeReportingManager, ManagerType, 
    EmployeeSalaryDetails, EmployeeWorkDetails, CompanyGrades, EmployeeWorkHistoryDetails, EmployeeResignationDetails,EmployeePreBoardingDetails
)
from core.models import Utils as model_utils
from company_profile.models import Departments, SubDepartments, Designations , CompanyPolicyDocuments, CompanyPolicyTypes
from directory.serializers import EmployeeSerialzer , CompanyPolicySerializer
from payroll.models import EmployeeComplianceNumbers
from HRMSApp.models import MultiTenantCompanies
from django.db import connection

logger = logging.getLogger('django')
class EmployeeDetailsAPIViewV2(APIView):
    model = Employee
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        company_id = kwargs.get("company_id")
        params = request.query_params
        # print(request.headers)
        if not company_id:
            try:
                company_id = request.user.employee_details.first().company_id
            except Exception as e:
                return Response(
                    error_response(e, 'Some thing went wrong', 404),
                    status=status.HTTP_404_NOT_FOUND
                )
        MultitenantSetup().create_to_connection(request)
        try:
            q_filters = db_models.Q(company_id=company_id, is_deleted=False)
                            
            if "department_id" in params:
                q_filters &= db_models.Q(work_details__department_id__in=params.get('department_id').split(','))
            if "sub_department_id" in params:
                q_filters &= db_models.Q(work_details__sub_department_id__in=params.get('sub_department_id').split(','))
            if "status" in params:
                # q_filters &= db_models.Q(work_details__employee_status=params.get('status'))
                q_filters &= db_models.Q(work_details__employee_status__in=params.get('status').split(','))
            if "payroll_status" in params:
                # if params.get("payroll_status") == 'hold':
                #     q_filters &= db_models.Q(payroll_status__isnull=True)
                # else:
                #     q_filters &= db_models.Q(payroll_status=params.get("payroll_status"))
                st = params.get("payroll_status").split(',')
                if 'hold' in st:
                    st.remove('hold')
                    q_filters &= (db_models.Q(payroll_status__in=st) | db_models.Q(payroll_status__isnull=True))
                else:
                    q_filters &= db_models.Q(payroll_status__in=st)   
            if "search_filter" in params:
                q_filters &= (
                    db_models.Q(user__username__icontains=search_filter_decode(params.get("search_filter"))) |
                    db_models.Q(official_email__icontains=search_filter_decode(params.get("search_filter"))) | 
                    db_models.Q(work_details__employee_number__icontains=search_filter_decode(params.get("search_filter"))) 
                )
            if "month" in params:
                q_filters &= db_models.Q(date_of_join__month = params.get("month"))
            if "year" in params:
                q_filters &= db_models.Q(date_of_join__year = params.get("year"))
            if "payroll_status" not in params and "status" not in params:
                q_filters &= db_models.Q(work_details__employee_status__in=['Active','YetToJoin'])
            paginator = self.pagination_class()
            today = timezone_now().date()
            qs = Employee.objects.filter(q_filters).select_related(
                    'work_details', 'user', 'work_details__employee_type', 
                ).prefetch_related(
                    'employee', 'roles', 'assignedattendancerules_set', 'employeeworkrulerelation_set',
                    'assignedattendancerules_set__attendance_rule', 'employeeworkrulerelation_set__work_rule',
                    'employeeleaverulerelation_set__leave_rule', 'employeeleaverulerelation_set'
                ).annotate(
                emp_distinct_id=db_models.F('id'),
                emp_name=db_models.F('user__username'),
                name=db_models.F('user__username'),
                number=db_models.F('work_details__employee_number'),
                department=db_models.F('work_details__department__name'),
                department_id = db_models.F('work_details__department_id'),
                sub_department=db_models.F('work_details__sub_department__name'),
                sub_department_id=db_models.F('work_details__sub_department_id'),
                designation=db_models.F('work_details__designation__name'),
                designation_id=db_models.F('work_details__designation_id'),
                work_location=db_models.F('work_details__work_location'),
                employee_type=db_models.Case(
                    db_models.When(work_details__employee_type__employee_type=10, then=db_models.Value("Full Time")),
                    db_models.When(work_details__employee_type__employee_type=20, then=db_models.Value("Part Time")),
                    db_models.When(work_details__employee_type__employee_type=30, then=db_models.Value("Intern")),
                    db_models.When(work_details__employee_type__employee_type=40, then=db_models.Value("On Contract")),
                    db_models.When(work_details__employee_type__employee_type=50, then=db_models.Value("Others")),
                    default=db_models.Value(""), output_field=db_models.CharField()
                ),
                employee_status=db_models.F('work_details__employee_status'),
                employee_grade=db_models.F("work_details__employee_grade__grade"),
                # reporting_manager = db_models.Case(
                #     db_models.When(
                #         employee__is_multitenant=True,
                #         then = ArrayAgg("employee__multitenant_manager_name",
                #                         filter = db_models.Q(
                #                             employee__isnull=False,
                #                             employee__manager_type__manager_type=10,
                #                             employee__is_deleted=False,),
                #                         distinct=True
                #         )
                # ),
                # default= ArrayAgg("employee__manager__user__username",
                #                         filter = db_models.Q(
                #                             employee__isnull=False,
                #                             employee__manager_type__manager_type=10,
                #                             employee__is_deleted=False,),
                #                         distinct=True
                #     )
                # ),
                reporting_manager_id=ArrayAgg(
                    db_models.F('employee__manager_id'),
                    filter=db_models.Q(employee__isnull=False, employee__manager_type__manager_type=10, employee__is_deleted=False, employee__manager__work_details__employee_status='Active'),
                    distinct=True
                ),
                attendance_rules=db_models.expressions.Case(
                            db_models.When(assignedattendancerules__effective_date__lte = today,
                                then = db_models.expressions.Func(
                                db_models.Value('name'), 'assignedattendancerules__attendance_rule__name',
                                db_models.Value('enableOverTime'), 'assignedattendancerules__attendance_rule__enable_over_time',
                                db_models.Value('orgInTime'), 'assignedattendancerules__attendance_rule__shift_in_time',
                                db_models.Value('orgOutTime'), 'assignedattendancerules__attendance_rule__shift_out_time',
                                db_models.Value('autoClockOut'), 'assignedattendancerules__attendance_rule__auto_clock_out',
                                db_models.Value('shiftInTime'), TimestampToStr(db_models.F('assignedattendancerules__attendance_rule__shift_in_time')),
                                db_models.Value('shiftOutTime'), TimestampToStr(db_models.F('assignedattendancerules__attendance_rule__shift_out_time')),
                                function='jsonb_build_object',
                                output_field=db_models.JSONField()
                            ),
                        ),
                            db_models.When(assignedattendancerules__effective_date__gt = today,
                                then = db_models.expressions.Func(
                                db_models.Value('name'), db_models.Value(None),
                                db_models.Value('enableOverTime'), db_models.Value(None),
                                db_models.Value('orgInTime'), db_models.Value(None),
                                db_models.Value('orgOutTime'), db_models.Value(None),
                                db_models.Value('autoClockOut'), db_models.Value(None),
                                function='jsonb_build_object',
                                output_field=db_models.JSONField()
                            ),
                        ),
                            db_models.When(assignedattendancerules__isnull = True,
                                then = db_models.expressions.Func(
                                db_models.Value('name'), db_models.Value(None),
                                db_models.Value('enableOverTime'), db_models.Value(None),
                                db_models.Value('orgInTime'), db_models.Value(None),
                                db_models.Value('orgOutTime'), db_models.Value(None),
                                db_models.Value('autoClockOut'), db_models.Value(None),
                                function='jsonb_build_object',
                                output_field=db_models.JSONField()
                            ),
                        ),
                        default=db_models.Value(None),
                        output_field=db_models.JSONField()
                ),
                workweek_rule=db_models.expressions.Case(
                            db_models.When(employeeworkrulerelation__effective_date__lte = today,
                                then=db_models.expressions.Func(
                                db_models.Value('name'), 'employeeworkrulerelation__work_rule__name',
                                function='jsonb_build_object',
                                output_field=db_models.JSONField()
                            ),
                        ),
                            db_models.When(employeeworkrulerelation__effective_date__gt=today,
                                then=db_models.expressions.Func(
                                db_models.Value('name'), db_models.Value(None),
                                function='jsonb_build_object',
                                output_field=db_models.JSONField()
                            ),
                        ),
                            db_models.When(employeeworkrulerelation__isnull=True,
                                then=db_models.expressions.Func(
                                db_models.Value('name'), db_models.Value(None),
                                function='jsonb_build_object',
                                output_field=db_models.JSONField()
                            ),
                        ),
                        default=db_models.Value(None),
                        output_field=db_models.JSONField()
                ),
                employee_role=db_models.F('roles__name'),
                leave_rules=db_models.expressions.Func(
                    db_models.Value('name'), ArrayAgg('employeeleaverulerelation__leave_rule__name',
                                                    filter = db_models.Q(employeeleaverulerelation__effective_date__lte=today,
                                                                        employeeleaverulerelation__session_year__session_year=today.year), distinct=True), 
                    # ArrayAgg('employeeleaverulerelation__leave_rule__name', distinct=True),
                    function='jsonb_build_object',
                    output_field=db_models.JSONField()
                ),
                onboarding_status=db_models.Case(
                    db_models.When(completed_onboard__is_deleted=True, then=db_models.Value("Not Assigned")),
                    db_models.When(completed_onboard__is_deleted=False, then=db_models.Value("Assigned")),
                    default=db_models.Value("Not Assigned"), output_field=db_models.CharField()
                ),
       
            ).values(
                'id', 'name', 'emp_name', 'employee_image',  "official_email", "phone", "number", "department", "sub_department", "designation",
                "date_of_birth", "date_of_join", "gender", "first_name", "middle_name", "last_name", "work_location", "blood_group",
                "marital_status", "anniversary_date", "personal_email", "alternate_phone", "pre_onboarding", "employee_type", "employee_grade",
                "linkedin_profile", "facebook_profile", "twitter_profile", "is_rehire", "attendance_rules", "workweek_rule",
                "employee_role", "leave_rules", "employee_status","is_sign_up", "payroll_status", "payroll_entity", "work_entity","onboarding_status",
                "department_id","sub_department_id", "designation_id","reporting_manager_id","bio"
                ).order_by('work_details__employee_status','-id')


            # print(Employee.objects.first().company)
            
            # df = pd.DataFrame(qs).drop_duplicates('id').reset_index(drop=True).to_dict('records')
            
            if request.query_params.get('tag') and request.query_params.get('tag').lower() == 'all':
                data = {
                    "next": None,
                    "previous": None,
                    "count": None,
                    "limit": None,
                    'current_page': None,
                    'total_pages': None,
                    "results": qs,
                }
                response = success_response(
                    data, "Successfully fetched Employee Data", 200
                )
            else:
                page = paginator.paginate_queryset(qs, request)
                response = success_response(
                        paginator.get_paginated_response(page), "Successfully fetched Employee Data", 200
                    )
            # del df
            MultitenantSetup().go_to_old_connection(request)
            return Response(
                response,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.critical(f"Employee Management GET employees list Came to Exception, error :{e}")
            MultitenantSetup().go_to_old_connection(request)
            return Response(
                [],
                status=status.HTTP_200_OK
            )

class EmployeeRetriveAPIViewV2(APIView):
    model = Employee
    
    def get(self, request, *args,**kwargs):
        MultitenantSetup().create_to_connection(request)
        employee_id = kwargs.get("id")
        obj = Employee.objects.filter(id=employee_id)
        if not obj.exists():
            return Response(
                error_response("Employee Not exists", "Employee Not exists", 404),
                status=status.HTTP_404_NOT_FOUND
            )
        data = obj.prefetch_related(
            "work_details", "salary_details", "address_details", "resignation_info"
        ).select_related(
            "user"
        ).annotate(
            probation_p_left = db_models.ExpressionWrapper(
            (db_models.F('date_of_join') + db_models.functions.Cast(Coalesce(db_models.F('work_details__probation_period'), db_models.Value(180)), output_field=db_models.IntegerField())) - timezone_now().date(),
            output_field=db_models.IntegerField())
        ).annotate(
            work_info=db_models.expressions.Func(
                db_models.Value('id'), 'work_details__id',
                db_models.Value('is_deleted'), 'work_details__is_deleted',
                db_models.Value('employee_number'), 'work_details__employee_number',
                db_models.Value('department'), db_models.expressions.Func(
                    db_models.Value('id'), 'work_details__department_id',
                    db_models.Value('is_deleted'), 'work_details__department__is_deleted',
                    db_models.Value('name'), 'work_details__department__name',
                    function='jsonb_build_object',
                    output_field=db_models.JSONField()
                ),
                db_models.Value('sub_department'), db_models.expressions.Func(
                    db_models.Value('id'), 'work_details__sub_department_id',
                    db_models.Value('is_deleted'), 'work_details__sub_department__is_deleted',
                    db_models.Value('name'), 'work_details__sub_department__name',
                    function='jsonb_build_object',
                    output_field=db_models.JSONField()
                ),
                db_models.Value('designation'), db_models.expressions.Func(
                    db_models.Value('id'), 'work_details__designation_id',
                    db_models.Value('is_deleted'), 'work_details__designation__is_deleted',
                    db_models.Value('name'), 'work_details__designation__name',
                    function='jsonb_build_object',
                    output_field=db_models.JSONField()
                ),
                db_models.Value('job_title'), 'work_details__job_title',
                db_models.Value('work_location'), 'work_details__work_location',
                db_models.Value('employee_grade'), db_models.expressions.Func(
                    db_models.Value('id'), 'work_details__employee_grade_id',
                    db_models.Value('is_deleted'), 'work_details__employee_grade__is_deleted',
                    db_models.Value('grade'), 'work_details__employee_grade__grade',
                    function='jsonb_build_object',
                    output_field=db_models.JSONField()
                ),
                db_models.Value('employee_type'), db_models.expressions.Func(
                    db_models.Value('id'), 'work_details__employee_type_id',
                    db_models.Value('employee_type'), 'work_details__employee_type__employee_type',
                    db_models.Value('value'), db_models.Case(
                        *[db_models.When(work_details__employee_type__employee_type=i[0], then=db_models.Value(i[1])) for i in EmployeeTypes.EMPLOYEE_TYPE_CHOICES],
                        default=db_models.Value(""), output_field=db_models.CharField()
                    ),
                    function='jsonb_build_object',
                    output_field=db_models.JSONField()
                ),
                db_models.Value('employee_status'), 'work_details__employee_status',
                db_models.Value('experience_in_years'), 'work_details__experience_in_years',
                db_models.Value('experience_in_months'), 'work_details__experience_in_months',
                db_models.Value('probation_period'), 'work_details__probation_period',
                db_models.Value('probation_period_left'), db_models.Case(
                            db_models.When(db_models.Q(
                                    db_models.Q(probation_p_left__lte=0) | db_models.Q(probation_p_left__isnull=True)
                                    ), then = db_models.Value(0)),
                            
                            default=db_models.F('probation_p_left'), output_field=db_models.IntegerField()),
                                    function='jsonb_build_object',
                                    output_field=db_models.JSONField()
                                ),
            salary_info=db_models.expressions.Func(
                db_models.Value('id'), 'salary_details__id',
                db_models.Value('is_deleted'), 'salary_details__is_deleted',
                db_models.Value('ctc'), 'salary_details__ctc',
                db_models.Value('salary'), 'salary_details__salary',
                db_models.Value('account_holder_name'), 'salary_details__account_holder_name',
                db_models.Value('account_number'), 'salary_details__account_number',
                db_models.Value('bank_name'), 'salary_details__bank_name',
                db_models.Value('branch_name'), 'salary_details__branch_name',
                db_models.Value('city'), 'salary_details__city',
                db_models.Value('ifsc_code'), 'salary_details__ifsc_code',
                db_models.Value('account_type'), 'salary_details__account_type',
                db_models.Value('fixed_salary'), 'salary_details__fixed_salary',
                db_models.Value('variable_pay'), 'salary_details__variable_pay',
                # db_models.Value('previus_income'), 'salary_details__previous_income',
                # db_models.Value('previous_tds'), 'salary_details__previous_tds',
                db_models.Value('previus_income'), db_models.Case(
                    db_models.When(salary_details__previous_income__isnull=True, then=db_models.Value(0)),
                    default=db_models.F('salary_details__previous_income'),output_field=db_models.DecimalField()
                            ),
                db_models.Value('previous_tds'), db_models.Case(
                    db_models.When(salary_details__previous_tds__isnull=True, then=db_models.Value(0)),
                    default=db_models.F('salary_details__previous_tds'), output_field=db_models.DecimalField()
                            ),
                function="jsonb_build_object",
                output_field=db_models.JSONField()
            ),
            addressDetails=db_models.expressions.Func(
                db_models.Value('id'), 'address_details__id',
                db_models.Value('current_address_line1'), 'address_details__current_address_line1',
                db_models.Value('is_deleted'), 'address_details__is_deleted',
                db_models.Value('created_at'), 'address_details__created_at',
                db_models.Value('updated_at'), 'address_details__updated_at',
                db_models.Value('created_by'), 'address_details__created_by',
                db_models.Value('updated_by'), 'address_details__updated_by',
                db_models.Value('current_address_line2'), 'address_details__current_address_line2',
                db_models.Value('current_country'), 'address_details__current_country',
                db_models.Value('current_state'), 'address_details__current_state',
                db_models.Value('current_city'), 'address_details__current_city',
                db_models.Value('current_pincode'), 'address_details__current_pincode',
                db_models.Value('current_house_type'), 'address_details__current_house_type',
                db_models.Value('current_staying_since'), 'address_details__current_staying_since',
                db_models.Value('living_in_current_city_since'), 'address_details__living_in_current_city_since',
                db_models.Value('permanent_address_line1'), 'address_details__permanent_address_line1',
                db_models.Value('permanent_address_line2'), 'address_details__permanent_address_line2',
                db_models.Value('permanent_country'), 'address_details__permanent_country',
                db_models.Value('permanent_state'), 'address_details__permanent_state',
                db_models.Value('permanent_city'), 'address_details__permanent_city',
                db_models.Value('permanent_pincode'), 'address_details__permanent_pincode',
                db_models.Value('permanent_same_as_current_address'), 'address_details__permanent_same_as_current_address',
                db_models.Value('other_house_type'), 'address_details__other_house_type',
                function="jsonb_build_object",
                output_field=db_models.JSONField()
            ),
            # signed_in=db_models.Case(
            #     db_models.When(user__is_authenticated=True, then=db_models.Value(True)),
            #     default=db_models.Value(False), output_field=db_models.BooleanField()
            # ),
            resignationInfo=db_models.expressions.Func(
                db_models.Value("id"), "resignation_info__id",
                db_models.Value("is_deleted"), "resignation_info__is_deleted",
                db_models.Value("created_at"), "resignation_info__created_at",
                db_models.Value("updated_at"), "resignation_info__updated_at",
                db_models.Value("created_by"), "resignation_info__created_by",
                db_models.Value("updated_by"), "resignation_info__updated_by",
                db_models.Value("resignation_date"), "resignation_info__resignation_date",
                db_models.Value("last_working_day"), "resignation_info__last_working_day",
                db_models.Value("resignation_status"), "resignation_info__resignation_status",
                db_models.Value("notice_period"), "resignation_info__notice_period",
                db_models.Value("termination_date"), "resignation_info__termination_date",
                db_models.Value("exit_interview_date"), "resignation_info__exit_interview_date",
                db_models.Value("exit_interview_time"), "resignation_info__exit_interview_time",
                db_models.Value("reason_of_leaving"), "resignation_info__reason_of_leaving",
                function="jsonb_build_object",
                output_field=db_models.JSONField()
            ),
            reporting_manager = db_models.Case(
                    db_models.When(
                        employee__is_multitenant=True,
                        then = ArrayAgg("employee__multitenant_manager_name",
                                        filter = db_models.Q(
                                            employee__isnull=False,
                                            employee__manager_type__manager_type=10,
                                            employee__is_deleted=False,),
                                        distinct=True
                        )
                ),
                default= ArrayAgg("employee__manager__user__username",
                                        filter = db_models.Q(
                                            employee__isnull=False,
                                            employee__manager_type__manager_type=10,
                                            employee__is_deleted=False,),
                                        distinct=True
                    )
                ),
            attendance_rules=db_models.expressions.Case(
                            db_models.When(assignedattendancerules__effective_date__lte = timezone_now().date(),
                                then = db_models.expressions.Func(
                                db_models.Value('name'), 'assignedattendancerules__attendance_rule__name',
                                db_models.Value('enableOverTime'), 'assignedattendancerules__attendance_rule__enable_over_time',
                                db_models.Value('orgInTime'), 'assignedattendancerules__attendance_rule__shift_in_time',
                                db_models.Value('orgOutTime'), 'assignedattendancerules__attendance_rule__shift_out_time',
                                db_models.Value('autoClockOut'), 'assignedattendancerules__attendance_rule__auto_clock_out',
                                db_models.Value('shiftInTime'), TimestampToStr(db_models.F('assignedattendancerules__attendance_rule__shift_in_time')),
                                db_models.Value('shiftOutTime'), TimestampToStr(db_models.F('assignedattendancerules__attendance_rule__shift_out_time')),
                                function='jsonb_build_object',
                                output_field=db_models.JSONField()
                            ),
                        ),
                            db_models.When(assignedattendancerules__effective_date__gt = timezone_now().date(),
                                then = db_models.expressions.Func(
                                db_models.Value('name'), db_models.Value(None),
                                db_models.Value('enableOverTime'), db_models.Value(None),
                                db_models.Value('orgInTime'), db_models.Value(None),
                                db_models.Value('orgOutTime'), db_models.Value(None),
                                db_models.Value('autoClockOut'), db_models.Value(None),
                                function='jsonb_build_object',
                                output_field=db_models.JSONField()
                            ),
                        ),
                            db_models.When(assignedattendancerules__isnull = True,
                                then = db_models.expressions.Func(
                                db_models.Value('name'), db_models.Value(None),
                                db_models.Value('enableOverTime'), db_models.Value(None),
                                db_models.Value('orgInTime'), db_models.Value(None),
                                db_models.Value('orgOutTime'), db_models.Value(None),
                                db_models.Value('autoClockOut'), db_models.Value(None),
                                function='jsonb_build_object',
                                output_field=db_models.JSONField()
                            ),
                        ),
                        default=db_models.Value(None),
                        output_field=db_models.JSONField()
                ),
            # company_logo = db_models.Case(
            #         db_models.When(db_models.Q(
            #                     ~db_models.Q(db_models.Q(company__company_image__isnull=True) | db_models.Q(company__company_image='')),
            #                     ), 
            #                        then=Concat(
            #                         db_models.Value('https://bharatpayroll.s3.amazonaws.com/media/public/'),
            #                         db_models.F('company__company_image')
            #                     )),
            #         default=db_models.Value(""), output_field=db_models.CharField()
            #     ),
        ).values(
            "id", "company_id", "first_name", "middle_name", "last_name", "employee_image", "official_email", "phone", "date_of_join",
            "date_of_birth", "gender", "blood_group", "marital_status", "anniversary_date", "personal_email", "alternate_phone", 
            "pre_onboarding", "linkedin_profile", "facebook_profile", "twitter_profile", "is_rehire","work_info", "salary_details",
            "salary_info", "addressDetails", "resignationInfo", "payroll_status", "payroll_entity", "work_entity","bio","reporting_manager",
            "attendance_rules","company__company_image"
        )
        MultitenantSetup().go_to_old_connection(request)
        return Response(
            success_response(data.first(), "Successfully Fetched Employee Data", 200),
            status=status.HTTP_200_OK
        )

class EmployeeDocumentsAPIViewV2(APIView):
    model = EmployeeDocuments
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        MultitenantSetup().create_to_connection(request)
        employee_id = kwargs.get("id")
        employee = Employee.objects.filter(id=employee_id)
        if not employee.exists():
            return Response(
                error_response("Employee Not exists", "Employee Not exists", 404),
                status=status.HTTP_404_NOT_FOUND
            )
        paginator = self.pagination_class()
        q_filter = db_models.Q(employee_id=employee_id, is_deleted=False)
        data = self.model.objects.filter(q_filter).select_related(
            'created_by', 'created_by__employee_details', 'document_type'
        ).annotate(
            uploaded_by=db_models.F('created_by__username'),
            # db_models.functions.Concat(
            #     db_models.F('created_by__employee_details__first_name'), db_models.Value(" "), 
            #     db_models.F("created_by__employee_details__last_name"), output_field=db_models.CharField()
            # ),
            documentType=db_models.expressions.Func(
                db_models.Value('id'), 'document_type_id',
                db_models.Value('documentType'), 'document_type__document_type',
                db_models.Value('value'), db_models.Case(
                    *[db_models.When(document_type__document_type=i[0], then=db_models.Value(i[1])) for i in DocumentsTypes.DOCUMENT_TYPE_CHOICES],
                    default=db_models.Value(""), output_field=db_models.CharField()
                ),
                function="jsonb_build_object",
                output_field=db_models.JSONField()
            )
        ).values(
            "id", "employee", "documentType", "document_number", "photo_id", "date_of_birth", "current_address",
            "parmanent_address", "is_verified", "select_file", "created_by", "uploaded_by", "is_deleted",
        )
        page = paginator.paginate_queryset(list(data), request)
        MultitenantSetup().go_to_old_connection(request)
        return Response(
            success_response(paginator.get_paginated_response(page), "Successfully Fetched Employee Document Data", 200),
            status=status.HTTP_200_OK
        )

class EmployeeEducationDetailsAPIViewV2(APIView):
    model = EmployeeEducationDetails
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        employee_id = kwargs.get("id")
        employee = Employee.objects.filter(id=employee_id)
        if not employee.exists():
            return Response(
                error_response("Employee Not exists", "Employee Not exists", 404),
                status=status.HTTP_404_NOT_FOUND
            )
        paginator = self.pagination_class()
        q_filter = db_models.Q(employee_id=employee_id, is_deleted=False)
        data = self.model.objects.filter(q_filter).select_related(
            'qualification', 'course_type'
        ).annotate(
            qualification_details=db_models.expressions.Func(
                db_models.Value("id"), 'qualification_id',
                db_models.Value("qualification_type"), 'qualification__qualification_type',
                db_models.Value("value"), db_models.Case(
                    *[db_models.When(qualification__qualification_type=i[0], then=db_models.Value(i[1])) for i in QualificationTypes.QUALIFICATION_TYPE_CHOICES]
                ),
                function="jsonb_build_object",
                output_field=db_models.JSONField()
            ),
            courseType=db_models.expressions.Func(
                db_models.Value("id"), 'course_type_id',
                db_models.Value("course_type"), 'course_type__course_type',
                db_models.Value("value"), db_models.Case(
                    *[db_models.When(course_type__course_type=i[0], then=db_models.Value(i[1])) for i in CourseTypes.COURSE_TYPE_CHOICES]
                ),
                function="jsonb_build_object",
                output_field=db_models.JSONField()
            )
        ).values(
            "id", "employee", "qualification_details", "course_name", "courseType", "stream",
            "course_start_date", "course_end_date", "college_name", "university_name", "is_deleted",
        )
        page = paginator.paginate_queryset(data, request)
        return Response(
            success_response(paginator.get_paginated_response(page), "Successfully Fetched Employee Education Data", 200),
            status=status.HTTP_200_OK
        )

class EmployeeCertificationsAPIViewV2(APIView):
    model = EmployeeCertifications
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        employee_id = kwargs.get("id")
        employee = Employee.objects.filter(id=employee_id)
        if not employee.exists():
            return Response(
                error_response("Employee Not exists", "Employee Not exists", 404),
                status=status.HTTP_404_NOT_FOUND
            )
        paginator = self.pagination_class()
        q_filter = db_models.Q(employee_id=employee_id, is_deleted=False)
        data = self.model.objects.filter(q_filter).select_related(
            'course_type', 'created_by'
        ).annotate(
            courseType=db_models.expressions.Func(
                db_models.Value("id"), 'course_type_id',
                db_models.Value("course_type"), 'course_type__course_type',
                db_models.Value("value"), db_models.Case(
                    *[db_models.When(course_type__course_type=i[0], then=db_models.Value(i[1])) for i in CertificationCourseTypes.CERTIFICATION_TYPE_CHOICES]
                ),
                function="jsonb_build_object",
                output_field=db_models.JSONField()
            ),
            uploaded_by=db_models.F('created_by__username'),
            # db_models.functions.Concat(
            #     db_models.F('created_by__employee_details__first_name'), db_models.Value(" "), 
            #     db_models.F("created_by__employee_details__last_name"), output_field=db_models.CharField()
            # ),
        ).values(
            "id", "employee", "courseType", "certification_title", "is_verified", "select_file", "created_by", "uploaded_by", "is_deleted",
        )
        page = paginator.paginate_queryset(data, request)
        return Response(
            success_response(paginator.get_paginated_response(page), "Successfully Fetched Employee Certifications Data", 200),
            status=status.HTTP_200_OK
        )

class EmployeeFamilyDetailsAPIViewV2(APIView):
    model = EmployeeFamilyDetails
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        employee_id = kwargs.get("id")
        employee = Employee.objects.filter(id=employee_id)
        if not employee.exists():
            return Response(
                error_response("Employee Not exists", "Employee Not exists", 404),
                status=status.HTTP_404_NOT_FOUND
            )
        paginator = self.pagination_class()
        q_filter = db_models.Q(employee_id=employee_id, is_deleted=False)
        data = self.model.objects.filter(q_filter).select_related(
            'relationship'
        ).annotate(
            relationship_type=db_models.expressions.Func(
                db_models.Value("id"), 'relationship_id',
                db_models.Value("relationship"), 'relationship__relationship_type',
                db_models.Value("value"), db_models.Case(
                    *[db_models.When(relationship__relationship_type=i[0], then=db_models.Value(i[1])) for i in RelationshipTypes.RELATIONSHIP_TYPE_CHOICES]
                ),
                function="jsonb_build_object",
                output_field=db_models.JSONField()
            )
        ).values(
            "id", "employee", "name", "relationship_type", "date_of_birth", "dependent", "is_deleted",
        )
        page = paginator.paginate_queryset(data, request)
        return Response(
            success_response(paginator.get_paginated_response(page), "Successfully Fetched Employee Family Data", 200),
            status=status.HTTP_200_OK
        )

class EmployeeEmergencyContactAPIViewV2(APIView):
    model = EmployeeEmergencyContact
    
    def get(self, request, *args, **kwargs):
        employee_id = kwargs.get("id")
        employee = Employee.objects.filter(id=employee_id)
        if not employee.exists():
            return Response(
                error_response("Employee Not exists", "Employee Not exists", 404),
                status=status.HTTP_404_NOT_FOUND
            )
        q_filter = db_models.Q(employee_id=employee_id, is_deleted=False)
        data = self.model.objects.filter(q_filter).select_related(
            'relationship',
        ).annotate(
            relationship_type=db_models.expressions.Func(
                db_models.Value("id"), 'relationship_id',
                db_models.Value("relationship"), 'relationship__relationship_type',
                db_models.Value("value"), db_models.Case(
                    *[db_models.When(relationship__relationship_type=i[0], then=db_models.Value(i[1])) for i in RelationshipTypes.RELATIONSHIP_TYPE_CHOICES]
                ),
                function="jsonb_build_object",
                output_field=db_models.JSONField()
            ),
            uploaded_by=db_models.F('created_by__username'),
            # db_models.functions.Concat(
            #     db_models.F('created_by__employee_details__first_name'), db_models.Value(" "), 
            #     db_models.F("created_by__employee_details__last_name"), output_field=db_models.CharField()
            # ),
        ).values(
            "id", "employee", "name", "relationship_type", "phone_number", "is_deleted",
        )
        return Response(
            success_response(data, "Successfully Fetched Employee Emergency Contact Data", 200),
            status=status.HTTP_200_OK
        )

class EmployeeDocumentationWorkAPIViewV2(APIView):
    model = EmployeeDocumentationWork
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        MultitenantSetup().create_to_connection(request)
        employee_id = kwargs.get("id")
        employee = Employee.objects.filter(id=employee_id)
        if not employee.exists():
            return Response(
                error_response("Employee Not exists", "Employee Not exists", 404),
                status=status.HTTP_404_NOT_FOUND
            )
        paginator = self.pagination_class()
        q_filter = db_models.Q(employee_id=employee_id, is_deleted=False)
        data = self.model.objects.filter(q_filter).annotate(
        uploaded_by=db_models.F('created_by__username'),
        # db_models.functions.Concat(
        #         db_models.F('created_by__employee_details__first_name'), db_models.Value(" "), 
        #         db_models.F("created_by__employee_details__last_name"), output_field=db_models.CharField()
        #     ),
        ).values(
            "id", "employee", "document_title", "document_description", "select_file", "created_by", "is_deleted",
            "uploaded_by", "created_at"
        )
        page = paginator.paginate_queryset(list(data), request)
        MultitenantSetup().go_to_old_connection(request)
        return Response(
            success_response(paginator.get_paginated_response(page), "Successfully Fetched Employee Family Data", 200),
            status=status.HTTP_200_OK
        )

class ManagerEmployeeDetailsV2(APIView):
    model = EmployeeReportingManager
    pagination_class = CustomPagePagination
    
    def get(self, request):
        manager_id = request.query_params.get('id')
        mul_key = request.query_params.get('mul_key')
        paginator = self.pagination_class()
        headers = request.headers
        current_db_name = connection.settings_dict['NAME']
        current_domain = current_db_name.split("_")[0]
        MultitenantSetup().create_to_connection(request)
        final_data = []
        single_q_filter =  db_models.Q(
            employee__work_details__employee_number=manager_id,
            is_deleted=False,
            employee__work_details__employee_status='Active')
        
        multi_q_filter = db_models.Q(
                        multitenant_manager_emp_id=manager_id,
                        is_deleted=False,
                        employee__work_details__employee_status='Active')

        department_id = request.query_params.get('department_id')
        if department_id:
            single_q_filter &= db_models.Q(employee__work_details__department_id=department_id)
            multi_q_filter &= db_models.Q(employee__work_details__department_id=department_id)
        qs = list(self.model.objects.filter(single_q_filter).select_related('employee', 'manager_type').annotate(
                employee_name=db_models.F('employee__user__username'),
                            type_of_manager=db_models.Case(
                                db_models.When(manager_type__manager_type=10, then=db_models.Value('Primary Manager')),
                                db_models.When(manager_type__manager_type=20, then=db_models.Value('Secondary Manager')),
                                default=db_models.Value(''),
                                output_field=db_models.CharField()
                            )
                    ).values('employee_name', 'type_of_manager',
                            'employee__work_details__department__name', 
                            'employee__work_details__designation__name',
                            'employee__employee_image',
                            'employee__work_details__department_id'
                    )
        )
        if qs:
            final_data.extend(qs)
        linked_companies = list(MultiTenantCompanies.objects.using("master_db").filter(
                    db_models.Q(mul_key = mul_key),
                    ~db_models.Q(subdomain = current_domain)
        ).values_list("subdomain", flat=True))
        logger.critical(f"pss {linked_companies}")
        if linked_companies:
            for linked_company in linked_companies:
                try:
                    MultitenantSetup().get_domain_connection(request,linked_company)
                except Exception as e:
                    logger.critical("pss exception")
                    logger.critical(e)
                    logger.critical("pss end")
                    continue
                logger.critical(multi_q_filter)
                qs = list(self.model.objects.filter(multi_q_filter).select_related('employee', 'manager_type').annotate(
                        employee_name=db_models.F('employee__user__username'),
                        type_of_manager=db_models.Case(
                            db_models.When(manager_type__manager_type=10, then=db_models.Value('Primary Manager')),
                            db_models.When(manager_type__manager_type=20, then=db_models.Value('Secondary Manager')),
                            default=db_models.Value(''),
                            output_field=db_models.CharField()
                        )
                ).values('employee_name', 'type_of_manager',
                        'employee__work_details__department__name', 
                        'employee__work_details__designation__name',
                        'employee__employee_image',
                        'employee__work_details__department_id'
                )
                )
                logger.critical("qas")
                logger.critical(qs)
                if qs:
                    final_data.extend(qs)
            MultitenantSetup().get_domain_connection(current_domain,request)
        page = paginator.paginate_queryset(final_data, request)
        data = success_response(paginator.get_paginated_response({
                "is_manager": True if final_data else False,
                "data": page
            }), "Successfully Fetched Employee Family Data", 200)
        MultitenantSetup().go_to_old_connection(request)
        return Response(
            data,
            status=status.HTTP_200_OK
        )

class EmployeeReportingManagerAPIViewV2(APIView):
    model = EmployeeReportingManager
    pagination_class = CustomPagePagination
    
    
    
    def get(self, request, *args, **kwargs):
        # MultitenantSetup().create_to_connection(request)
        employee_id = kwargs.get("id")
        employee = Employee.objects.filter(id=employee_id)
        if not employee.exists():
            return Response(
                error_response("Employee Not exists", "Employee Not exists", 404),
                status=status.HTTP_404_NOT_FOUND
            )
        paginator = self.pagination_class()
        q_filter = db_models.Q(
            employee_id=employee_id,
            is_deleted=False,
        ) & (
            db_models.Q(manager__work_details__employee_status='Active') | 
            db_models.Q(is_multitenant=True)
        )
        data = EmployeeReportingManager.objects.filter(q_filter).annotate(
            managerType=db_models.expressions.Func(
                db_models.Value('id'), 'manager_type',
                db_models.Value('managerType'), 'manager_type__manager_type',
                db_models.Value('value'), db_models.Case(
                    *[db_models.When(manager_type__manager_type=i[0], then=db_models.Value(i[1])) for i in ManagerType.MANAGER_TYPE_CHOICES]
                ),
                
                function="jsonb_build_object",
                output_field=db_models.JSONField()
            ),
            manager_details=db_models.Case(
                db_models.When(
                    is_multitenant=False,
                    then=db_models.expressions.Func(                        
                        db_models.Value("id"), 'manager__id',
                        db_models.Value("name"), db_models.F('manager__user__username'),
                        # db_models.functions.Concat(
                        #     db_models.F('manager__first_name'), db_models.Value(" "), db_models.F('manager__middle_name'), db_models.Value(" "), db_models.F('manager__last_name'),
                        #     output_field=db_models.CharField()    
                        # ),                  
                        db_models.Value("company_name"), 'manager__company__company_name',                            
                        db_models.Value("department"), 'manager__work_details__department__name',
                        db_models.Value("designation"), 'manager__work_details__designation__name',
                        function="jsonb_build_object",
                        output_field=db_models.JSONField()
                    ),
                ),
                db_models.When(
                    is_multitenant__isnull=True,
                    then=db_models.expressions.Func(                        
                        db_models.Value("id"), 'manager__id',
                        db_models.Value("name"), db_models.F('manager__user__username'),
                        # db_models.functions.Concat(
                        #     db_models.F('manager__first_name'), db_models.Value(" "), db_models.F('manager__middle_name'), db_models.Value(" "), db_models.F('manager__last_name'),
                        #     output_field=db_models.CharField()    
                        # ),
                        db_models.Value("company_name"), 'manager__company__company_name',
                        db_models.Value("department"), 'manager__work_details__department__name',
                        db_models.Value("designation"), 'manager__work_details__designation__name',
                        function="jsonb_build_object",
                        output_field=db_models.JSONField()
                    ),
                ),
                default=db_models.expressions.Func(
                    db_models.Value("name"), db_models.F('multitenant_manager_name'),
                    db_models.Value("id"), db_models.F('multitenant_manager_emp_id'),
                    function="jsonb_build_object",
                    output_field=db_models.JSONField()
                )
            )
        ).values(
            "id", "managerType", "employee", 
            "manager_details", 
            "is_deleted", "is_multitenant",
            "multitenant_manager_emp_id", "multitenant_manager_company_domain","multitenant_manager_company"
        )
        for i in data:
            if i.get("is_multitenant"):
                try:
                    MultitenantSetup().get_domain_connection(request,i["multitenant_manager_company_domain"])
                    manager_data = Employee.objects.filter(
                        work_details__employee_number = i["multitenant_manager_emp_id"]
                    ).annotate(
                        # id = db_models.F("id"),
                        name = db_models.F("user__username"),
                        department =  db_models.F("work_details__department__name"),
                        designation = db_models.F("work_details__designation__name"),
                        company_name = db_models.F("company__company_name")
                    ).values(
                        "id", "name", "department",
                        "designation","company_name"
                    )
                    i["manager_details"] = manager_data[0]
                except Exception as e:
                    manager_data = {
                        "id" : "",
                        "name" : "",
                        "department" : "",
                        "designation" : "",
                    }
                    i["manager_details"] = manager_data
                    MultitenantSetup().go_to_old_connection(request)
        page = paginator.paginate_queryset(data, request)
        return Response(
            success_response(paginator.get_paginated_response(page), "Successfully Fetched Employee Family Data", 200),
            status=status.HTTP_200_OK
        )
class EmployeeImportViewV2(APIView):
    serializer_class = EmployeeSerialzer
    model = Employee
            
    def doj_func(self, date_of_join):
        date_formats = ["%d/%m/%Y", "%d-%m-%Y", "%d:%m:%Y", "%Y-%m-%d", "%Y:%m:%d", "%Y/%m/%d" ]

        for date_format in date_formats:
            try:
                return datetime.datetime.strptime(str(date_of_join), date_format).date()
            except Exception as e:
                pass  
        return timezone_now().date()
    
    def dob_func(self, date_of_birth, emp_id):
        date_formats = ["%d/%m/%Y", "%d-%m-%Y", "%d:%m:%Y", "%Y-%m-%d", "%Y:%m:%d", "%Y/%m/%d" ]
        dob = None
        for date_format in date_formats:
            try:
                dob = datetime.datetime.strptime(str(date_of_birth), date_format).date()
                break
            except Exception as e:
                pass
        if dob is not None:
            Employee.objects.filter(id=emp_id).update(date_of_birth=dob)
        
    def emp_salary_details(self, obj):
        print("obj",obj['ctc'], "t", type(obj['ctc']))
        if not obj['ctc']:
            obj['ctc']=0
        instance, created = EmployeeSalaryDetails.objects.get_or_create(employee_id =obj['employee'], ctc = obj['ctc'],account_holder_name = obj['first_name'],account_number = obj['account_no'],bank_name = obj['Bank'],city = obj['City'],branch_name = obj['Branch'],ifsc_code = obj['IFSC'])
   
        if obj['IFSC']:
            if str(obj['IFSC']).strip().lower().startswith('icic'):
                instance.fund_transfer_type = "I"
            else:
                instance.fund_transfer_type = "N"
        instance.save()


    def post(self, request, *args, **kwargs):
        try:
            file = self.request.FILES["employee_file"]
            company_id = self.request.data.get('company')
            df = pd.read_excel(file, keep_default_na=False, skiprows=1, usecols="A:AB")
            df['status'] = False
            df['company'] = company_id
            df['message'] = ''
            
            required_columns = ['First Name (Mandatory, if not already in the system)', 
                                'Middle Name', 'Last Name (Mandatory, if not already in the system)',
                                'Official Email ID (Mandatory, if not already in the system or Contact Number is not set)',
                                'Date of Joining(DD/MM/YYYY) (Mandatory, if not already in the system)',
                                'Contact Number (Mandatory, if not already in the system or Official Email ID is not set)','Gender',
                                'DOB(DD/MM/YYYY)','Work Location','Department','Sub Department','Designation','Employee Status','Employee Type',
                                'Probation Period','Grade','Reporting Manager(Emp ID/ Email ID)','Annual CTC','Aadhaar Card','Pan Card',
                                'Emergency Contact Name','Emergency Contact Number','Relation','Bank','Branch','City','IFSC','Account Number'
                                ]
            # if any(column not in df.columns for column in required_columns):
            if not all(column in df.columns for column in required_columns):
                return Response(
                        error_response('please provide a correct file', 'please provide a correct file', 400),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            df['Employee Id'] = ''
            df = df.rename(columns={'Contact Number (Mandatory, if not already in the system or Official Email ID is not set)': 'phone',
                                    'First Name (Mandatory, if not already in the system)':'first_name',
                                    'Middle Name':'middle_name',
                                    'Last Name (Mandatory, if not already in the system)':'last_name',
                                    'Official Email ID (Mandatory, if not already in the system or Contact Number is not set)':'official_email',
                                    'Date of Joining(DD/MM/YYYY) (Mandatory, if not already in the system)':'date_of_join',
                                    'Reporting Manager(Emp ID/ Email ID)':'reporting_manager_mail',
                                    'DOB(DD/MM/YYYY)':'date_of_birth',
                                    'Gender':'gender','Annual CTC':'ctc','Aadhaar Card':'aadhar','Pan Card':'pan',
                                    'Emergency Contact Name':'emergency_contact_name','Relation':'relation','Emergency Contact Number':'emergency_contact_number',
                                    'Account Number':'account_no','Employee Status':'employee_status',
                                    'Work Location':'work_location','Sub Department':'sub_department','Employee Type':'employee_type','Probation Period':'probation_period',
                                    'Employee Id' : 'unique_emp_id'
                                    })
            
            df.status[df.loc[df['first_name'] == ""].index] = True
            df.message[df.loc[df["first_name"] == ""].index] = df.message[df.loc[df["first_name"] == ""].index] + "First Name is mandatory"
            
            df.status[df.loc[df['last_name'] == ""].index] = True
            df.message[df.loc[df["last_name"] == ""].index] = df.message[df.loc[df["last_name"] == ""].index] +','+ "Last Name is mandatory"
            
            df.status[df.loc[df['official_email'] == ""].index] = True
            df.message[df.loc[df["official_email"] == ""].index] = df.message[df.loc[df["official_email"] == ""].index] +','+ "Official Email ID is mandatory"
            
            df.status[df.loc[df['date_of_join'] == ""].index] = True
            df.message[df.loc[df["date_of_join"] == ""].index] = df.message[df.loc[df["date_of_join"] == ""].index] +','+ "Date of Joining is mandatory"
            
            df.status[df.loc[df['phone'] == ""].index] = True
            df.message[df.loc[df["phone"] == ""].index] = df.message[df.loc[df["phone"] == ""].index] +','+ "Contact Number is mandatory"
            
            # df.status[df.loc[df['date_of_birth'] == ""].index] = True
            # df.message[df.loc[df["date_of_birth"] == ""].index] = df.message[df.loc[df["date_of_birth"] == ""].index] + "DOB(DD/MM/YYYY) is mandatory"
            
            valid_genders = ['MALE', 'FEMALE', 'TRANSGENDER']
            df.gender = df.gender.apply(lambda gender: str(gender).strip().upper() if gender else '')
            # df['status'] = df['gender'].apply(lambda gender: False if (gender and gender in valid_genders) else True)
            df['status'] = df.apply(
                lambda obj:True if obj['status'] else(False if (obj['gender'] and obj['gender'] in valid_genders) else True), axis=1)
            
            df['message'] = df.apply(
                lambda obj:obj['message'] if (obj['gender'] and obj['gender'] in valid_genders) else obj['message'] + ','+ 'Please Provide Proper Gender', axis=1)
            
            df['status'] = df.apply(
                lambda obj: True if obj['status'] else (False if re.match(r'^\d{10}$', str(obj['phone'])) else True), axis=1)
            
            df['message'] = df.apply(
                lambda obj: obj['message'] + ','+ 'Invalid phone number. It should have exactly 10 digits only' if not re.match(r'^\d{10}$', str(obj['phone'])) else obj['message'], axis=1)
            
            df.employee_status = df.employee_status.apply(
                lambda a : 'Active' if a and str(a).strip().lower()  == 'active' else a)
            df.employee_status = df.employee_status.apply(
                lambda a : 'Inactive' if a and str(a).strip().lower() in ['inactive','in active'] else a)
            df.employee_status = df.employee_status.apply(
                lambda a : 'YetToJoin' if a and str(a).strip().lower() in ['yettojoin','yet to join'] else a)
            df.employee_status = df.employee_status.apply(
                lambda a : a if a and str(a).strip().lower() in ['active','inactive','in active','yettojoin','yet to join'] else "YetToJoin")
            
            # df['status'] = df.apply(lambda row: False if row['date_of_join'] and datetime.datetime.strptime(row['date_of_join'], "%d/%m/%Y") else True, axis=1)
            # df['status'] = df.apply(lambda row: False if row['date_of_birth'] and datetime.datetime.strptime(row['date_of_birth'], "%d/%m/%Y") else True, axis=1)

            true_status_df = df[df['status'] == True]
            false_status_df = df[df['status'] == False]
            false_status_df.date_of_join = false_status_df.date_of_join.apply(lambda a : self.doj_func(a))
            if len(false_status_df) == 0:
                file_name = "failed employees list.xlsx"
                return excel_converter(true_status_df,file_name)
            try:
                list_of_objects = false_status_df.apply(lambda obj: {
                                                'company': obj['company'], 'first_name': obj['first_name'],
                                                'middle_name':obj['middle_name'],'last_name':obj['last_name'],
                                                'official_email':obj['official_email'],'phone':obj['phone'],
                                                'date_of_join':obj['date_of_join'], 'gender':obj['gender'],
                                                'work_details': {'employee_status': obj['employee_status'], 
                                                                 'probation_period': obj['probation_period'] or 180}
                                            }, axis=1).tolist()
                serializer = EmployeeSerialzer(data = list_of_objects,many=True)
                final_status_df = false_status_df
                if not serializer.is_valid():
                    for index, error in enumerate(serializer.errors):
                        if error:
                            false_status_df.loc[index, 'message'] = false_status_df.loc[index, 'message'] + str(error).split("[ErrorDetail(string='")[1].split("', code=")[0]
                            false_status_df.loc[index, 'status'] = True
                    file_name = "failed employees list.xlsx"
                    final_status_df = false_status_df[false_status_df['status'] == False]
                    
                if len(final_status_df) == 0 :
                    final_df = pd.concat([true_status_df, false_status_df], ignore_index=True)
                    return excel_converter(final_df,file_name)
                elif len(false_status_df) == len(final_status_df) :
                    serializer.save()
                else:
                    list_of_new_objects = final_status_df.apply(lambda obj: {
                                                    'company': obj['company'], 'first_name': obj['first_name'],
                                                    'middle_name':obj['middle_name'],'last_name':obj['last_name'],
                                                    'official_email':obj['official_email'],'phone':obj['phone'],
                                                    'date_of_join':obj['date_of_join'], 'gender':obj['gender'],
                                                    'work_details': {'employee_status': obj['employee_status'], 
                                                                     'probation_period': obj['probation_period'] or 180}}, axis=1).tolist()
                    serializer_1 = EmployeeSerialzer(data = list_of_new_objects,many=True)
                    if serializer_1.is_valid():
                        serializer_1.save()
                    else:
                        Error  = ''
                        for i, error in enumerate(serializer_1.errors):
                            Error  += str(serializer_1.errors.get(error)).split("[ErrorDetail(string='")[1].split("', code=")[0]
                        response = error_response(Error,'something went wrong', 400)
                        return Response(response, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing Went wrong", 400),
                status=status.HTTP_400_BAD_REQUEST
            )
            print("with no errros")
            final_status_df['employee']  = final_status_df.official_email.apply(lambda k: Employee.objects.get(official_email = k).id)
            
            final_status_df['relation_type_id']  = final_status_df.apply(
                            lambda obj: RelationshipTypes.objects.filter(relationship_type=model_utils.get_relation_types(obj['relation']),is_deleted=False).first().id 
                            if RelationshipTypes.objects.filter(relationship_type=model_utils.get_relation_types(obj['relation']),is_deleted=False).exists() else '',axis=1)
            
            final_status_df['department_id']  = final_status_df.apply(
                            lambda obj: Departments.objects.filter(company_id = obj['company'],is_deleted=False,name=obj['Department']).first().id
                                if Departments.objects.filter(company_id = obj['company'],is_deleted=False,name=obj['Department']).exists() else '',axis=1)
            
            final_status_df['sub_department_id']  = final_status_df.apply(
                            lambda obj: SubDepartments.objects.filter(department_id = (obj['department_id']),
                                                        name=obj['sub_department'],is_deleted=False).first().id 
                                if obj['department_id'] and SubDepartments.objects.filter(
                                                        department_id = (obj['department_id']),name=obj['sub_department'],is_deleted=False).exists() 
                                else '',axis=1)
            
            final_status_df['reporting_man_id']  = final_status_df.apply(
                            lambda obj: Employee.objects.filter(company_id=obj['company'],official_email = obj['reporting_manager_mail'],is_deleted=False).first().id 
                                if Employee.objects.filter(company_id=obj['company'],official_email = obj['reporting_manager_mail'],is_deleted=False).exists() 
                                else '',axis=1)
            
            final_status_df['designation_id']  = final_status_df.apply(
                            lambda obj: Designations.objects.filter(company_id = obj['company'],name=obj['Designation'],
                                                            is_deleted=False).first().id 
                                if obj['department_id'] and Designations.objects.filter(
                                                            company_id = obj['company'],name=obj['Designation'],
                                                            is_deleted=False).exists() else '',axis=1)
            
            final_status_df['manager_type_id']  = final_status_df.apply(
                            lambda obj: ManagerType.objects.filter(manager_type=10,is_deleted=False).first().id 
                                        if obj['reporting_man_id'] else '',axis=1)
            
            final_status_df['company_grade_id']  = final_status_df.apply(
                            lambda obj: CompanyGrades.objects.filter(company_id=obj['company'],grade = obj['Grade'],is_deleted=False).first().id 
                                        if obj['Grade'] and CompanyGrades.objects.filter(company_id=obj['company'],grade = obj['Grade'],is_deleted=False) else '',axis=1)
            
            final_status_df.employee_type = final_status_df.employee_type.apply(
                lambda k: k.replace(' ','-').lower() if k else ''
                )
            
            final_status_df['employee_type_id']  = final_status_df.apply(
                            lambda obj: EmployeeTypes.objects.filter(slug =obj['employee_type'],is_deleted=False).first().id 
                                if EmployeeTypes.objects.filter(slug = obj['employee_type'],is_deleted=False).exists() 
                                else '',axis=1)
            
            aadhar_doc_type = DocumentsTypes.objects.filter(document_type=20).first()
            pan_doc_type = DocumentsTypes.objects.filter(document_type=10).first()
            final_status_df.apply(lambda obj: EmployeeDocuments.objects.get_or_create(employee_id =obj['employee'],
                                                                    document_type=aadhar_doc_type,
                                                                    document_number = obj['aadhar']) if obj['aadhar'] else '',axis=1)

            final_status_df.apply(lambda obj: EmployeeDocuments.objects.get_or_create(employee_id =obj['employee'],
                                                                    document_type=pan_doc_type,
                                                                    document_number = obj['pan']) if obj['pan'] else '',axis=1)

            final_status_df.apply(lambda obj: EmployeeEmergencyContact.objects.get_or_create(employee_id =obj['employee'],
                                                                    name = obj['emergency_contact_name'],
                                                                    relationship_id = obj['relation_type_id'],
                                                                    phone_number = obj['emergency_contact_number']
                                                                    ) if obj['relation_type_id'] else '',axis=1)
            
            final_status_df.apply(lambda obj: self.emp_salary_details(obj), axis=1)

            final_status_df.apply(lambda obj: EmployeeWorkDetails.objects.filter(employee_id = obj['employee']).update(
                                                                    employee_type_id =obj['employee_type_id'],
                                                                    work_location = obj['work_location'],
                                                                    department_id = obj['department_id'],
                                                                    sub_department_id = obj['sub_department_id'],
                                                                    designation_id = obj['designation_id'],
                                                                    employee_grade_id = obj['company_grade_id']
                                                                    ) ,axis=1)

            final_status_df.apply(lambda obj: EmployeeWorkDetails.objects.filter(employee_id = obj['employee']
                                                                    ).update(employee_number = str(obj['unique_emp_id']).strip()) 
                                  if obj['unique_emp_id'] and not EmployeeWorkDetails.objects.filter(
                                                                        employee_number = str(obj['unique_emp_id']).strip()).exists() else None,axis=1)
            final_status_df.apply(lambda obj: EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['employee'], work_to__isnull=True).update(work_to=timezone_now()) if obj['reporting_man_id'] else '',axis=1)
            final_status_df.apply(lambda obj: EmployeeWorkHistoryDetails.objects.get_or_create(employee_id=obj['employee'],department_id=obj['department_id'],work_from=timezone_now())
                                                                                               if obj['department_id'] else '', axis=1)
            final_status_df.apply(lambda obj: EmployeeWorkHistoryDetails.objects.get_or_create(employee_id=obj['employee'],manager_id=obj['reporting_man_id'],work_from=timezone_now())
                                                                                               if obj['reporting_man_id'] else '', axis=1)
            final_status_df.apply(lambda obj:EmployeeReportingManager.objects.filter(employee_id = obj['employee']).delete() if obj['reporting_man_id'] else '',axis=1)
            final_status_df.apply(lambda obj:
                EmployeeReportingManager.objects.create(
                                                        manager_type_id = obj['manager_type_id'],
                                                        employee_id = obj['employee'],
                                                        manager_id = obj['reporting_man_id']) if obj['reporting_man_id'] else '',axis=1)
            final_status_df.apply(lambda obj : self.dob_func(obj['date_of_birth'],obj['employee']), axis=1)
            error_df =  false_status_df[false_status_df['status'] == True]     
            if not final_status_df.empty:
                final_data_dict = final_status_df.to_dict('records')
                for obj in final_data_dict:
                    employee = Employee.objects.filter(id=obj['employee']).first()
                    payload = {
                        'company_id':obj['company'],
                        'emp_code': employee.work_details.employee_number,
                        'emp_first_name': obj['first_name'] ,
                        'emp_middle_name': obj['middle_name'] if obj['middle_name'] else 'Null',
                        'emp_last_name': obj['last_name'],
                        'dept_id': employee.work_details.department_id if employee.work_details.department_id else 'Null',
                        'designation_id': employee.work_details.designation_id if employee.work_details.designation_id else 'Null',
                        'pernonal_email': 'Null',
                        'office_email':employee.official_email
                    }
                    add_employee_ats(payload)
                     
            if len(true_status_df) != 0 or len(error_df) != 0:
                final_df = pd.concat([true_status_df, error_df], ignore_index=True)
                file_name = "failed employees list.xlsx"
                return excel_converter(final_df,file_name)
            return Response(
                status=status.HTTP_201_CREATED,
                data={
                    "status": status.HTTP_201_CREATED,
                    "message": "Employees successfully created",
                    "data": [],
                },
            )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing Went wrong", 400),
                status=status.HTTP_400_BAD_REQUEST
            )

class EmployeeComplianceNumbersAPIViewV2(APIView):

    model = EmployeeComplianceNumbers
    pagination_class = CustomPagePagination

    def post(self, request, *args, **kwargs):
        try:
            EmployeeComplianceNumbers.objects.create(
                employee_id=request.data.get("employee"),
                pf_num=request.data.get("pf_number"),
                uan_num=request.data.get("uan_number"),
                esi_num=request.data.get("esi_number"),
                nominee_name=request.data.get("nominee_name"),
                nominee_rel=request.data.get("nominee_rel"),
                nominee_dob=request.data.get("nominee_dob"),
                )
            return Response(
                success_response("Employee Compliance Numbers created Succesfully", "Employee Compliance Numbers created Succesfully", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
    
    def get(self, request, *args, **kwargs):

        params = request.query_params
        try:
            if "employee" not in params:
                return Response(
                    error_response("Employee ID is required", "Employee ID is required", 400),
                    status=status.HTTP_400_BAD_REQUEST
                )
            q_filter = db_models.Q(employee_id = params.get("employee"), is_deleted = False)
            paginator = self.pagination_class()
            data = EmployeeComplianceNumbers.objects.filter(q_filter).values(
                "id","employee","pf_num","uan_num","esi_num","nominee_name","nominee_rel","nominee_dob","health_insurence","insurence_date","insurence_file",
                "created_at",
            )
            page = paginator.paginate_queryset(data, request)
            return Response(
                success_response(paginator.get_paginated_response(page), "Successfully fetched employee compliance numbers", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
    
    def patch(self, request, *args, **kwargs):

        params = request.query_params
        try:
            if "id" not in params:
                return Response(
                    error_response("ID is required", "ID is required", 400),
                    status=status.HTTP_400_BAD_REQUEST
                )
            obj = EmployeeComplianceNumbers.objects.get(id = params.get("id"))
            obj.pf_num = request.data.get("pf_number")
            obj.uan_num = request.data.get("uan_number")
            obj.esi_num = request.data.get("esi_number")
            obj.nominee_name = request.data.get("nominee_name")
            obj.nominee_rel = request.data.get("nominee_rel")
            obj.nominee_dob = request.data.get("nominee_dob")
            obj.health_insurence=request.data.get("health_insurence",None)
            obj.insurence_date=request.data.get("insurence_date",None)
            obj.insurence_file=request.data.get("insurence_file",None)

            obj.save()
            return Response(
                success_response("Employee Compliance Numbers Updated Successfully", "Employee Compliance Numbers Updated Successfully", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

class EmployeeSoftDelete(APIView):
    
    model = Employee
    
    def put(self, request, *args, **kwargs):
        emp_id = self.kwargs.get('employee_id', None)
        if not emp_id:
            return Response(
                error_response("Employee ID Cant be None", "Employee ID Cant be None", 400),
                status=status.HTTP_400_BAD_REQUEST
            )
        emps = self.model.objects.filter(id=emp_id, is_deleted=False)
        if not emps.exists():
            return Response(
                error_response("Employee Not Present", "Employee Not Present", 400),
                status=status.HTTP_400_BAD_REQUEST
            )
        # Update Emps to soft delete
        emp = emps.first()
        user = emp.user
        emps.update(is_deleted=True)

        user.is_active = False
        user.save()
        
        return Response(
            success_response("Employee Deleted Successfully", "Employee Deleted Successfully", 200),
            status=status.HTTP_200_OK
        )

class DeptEmployeeAPIView(APIView):
    model = Employee
    
    def get(self, request, *args, **kwargs):
        params = request.query_params
        company_id = params.get("company_id")
        
        if not company_id:
            try:
                company_id = request.user.employee_details.first().company_id
            except Exception as e:
                return Response(
                    error_response(e, 'Some thing went wrong', 404),
                    status=status.HTTP_404_NOT_FOUND
                )
        q_filters = db_models.Q(company_id=company_id, is_deleted=False, work_details__employee_status='Active')
        if "department_id" in params:
            q_filters &= db_models.Q(work_details__department_id__in=params.get('department_id').split(','))
            
        data = self.model.objects.filter(q_filters).values('id','user__username','work_details__employee_number')
        
        return Response(
            success_response(data, "Employee Data Fetched Successfully", 200),
            status=status.HTTP_200_OK
        )
class GetResignationInfo(APIView):
    model = Employee
    
    def get(self, request, *args, **kwargs):
        user_info = request.user.employee_details.first()
        role = user_info.roles.values_list('name',flat=True).first()
        tag=True
        if role == 'EMPLOYEE':
            if not EmployeeResignationDetails.objects.filter(employee_id=user_info.id, is_deleted=False).exists():
                tag = False
                
        context = {"enable":tag}
        return Response(
            success_response(context, "Employee Data Fetched Successfully", 200),
            status=status.HTTP_200_OK
        )
        
class CompanyPolicyView(APIView):
    model = CompanyPolicyDocuments
    serializer_class = CompanyPolicySerializer
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        company_id = self.kwargs.get('id',1)
        user_info = request.user.employee_details.first()
        role_ids = user_info.roles.values_list('id', flat=True)
        role_names = user_info.roles.values_list('name', flat=True)
        q_filter = db_models.Q(company_id=company_id, is_deleted=False)
        if 'ADMIN' not in role_names:
            q_filter &= (db_models.Q(roles__in=role_ids) | db_models.Q(visibility='VISIBLE_TO_ALL'))
            q_filter &= (db_models.Q(status="ACTIVE"))
        paginator = self.pagination_class()
        query = self.model.objects.filter(q_filter).annotate(
            role = ArrayAgg('roles__id', filter = db_models.Q(roles__isnull = False))
            ).order_by('-id').values('id','title', 'policy_type__policy_name', 'description', 
                                     'visibility', 'status', 'policy_file', 'role', "created_at", 'policy_type')
        page = paginator.paginate_queryset(query, request)
        response = success_response(
                paginator.get_paginated_response(page), "Successfully fetched Employee Data", 200
            )
        return Response(response,status=status.HTTP_201_CREATED)
    
    def post(self, request, *args, **kwargs):
        try:
            request_data = request.data
            request_data = request_data.dict()
            roles = request_data.pop("roles",[])
            title = request_data.get('title') 
            policy_type = request_data.get('policy_type')
            if  CompanyPolicyDocuments.objects.filter(
                title=title,policy_type = policy_type
            ).exists():
                    return Response(
                error_response("Title Alredy exists", 400),
                status=status.HTTP_400_BAD_REQUEST
            )
            
            if roles:
                request_data['roles'] = roles.split(',')
            serializer = self.serializer_class(data=request_data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
            response = success_response(serializer.data, 'Company Policy Added Successfully', 200)
            return Response(response,status=status.HTTP_201_CREATED)
        except Exception as e:
            response = error_response(f'{str(e)} Error: {traceback.format_exc()}', 400)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
    def patch(self, request, *args, **kwargs):
        try:
            request_data = request.data
            request_data = request_data.dict()
            title = request_data.get('title') 
            policy_type = request_data.get('policy_type')
            obj = self.model.objects.get(id=self.kwargs.get('id'))
            if 'is_deleted' in request_data:
                obj.is_deleted=True
                obj.save()
                response = success_response([], 'Company Policy Updated Successfully', 200)
                return Response(response,status=status.HTTP_200_OK)
            
            if  CompanyPolicyDocuments.objects.filter(
                title=title,policy_type = policy_type
            ).exclude(id=self.kwargs.get('id')).exists():
                    return Response(
                error_response("Title Alredy exists", 400),
                status=status.HTTP_400_BAD_REQUEST
            )
            
            roles = request_data.pop("roles",[])
            if roles == 'null':
                obj.roles.clear()
            elif roles:
                request_data['roles'] = roles.split(',')
            if request_data.get('policy_file','') == 'null':
                obj.policy_file = None
            obj.save()
            serializer = self.serializer_class(obj, data=request_data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
            response = success_response(serializer.data, 'Company Policy Updated Successfully', 200)
            return Response(response,status=status.HTTP_200_OK)
        except Exception as e:
            response = error_response(f'{str(e)} Error: {traceback.format_exc()}',400)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        #['Title name alredy exists']
        
class CompanyPolicyTypesDetails(APIView):
    model = Employee
    
    def get(self, request, *args, **kwargs):
        choices = ("Recruitment and Hiring", "Onboarding", "Performance and Development", "Compensation and Benefits",
            "Employee Relations","Legal and Compliance", "Termination and Exit", "Miscellaneous")
        
        for choice in choices:
            CompanyPolicyTypes.objects.get_or_create(policy_name=choice)
            
        query = CompanyPolicyTypes.objects.filter(is_deleted=False).values()
        return Response(
                success_response(query, "Successfully Fetched Company Policy Types", 200),
                status=status.HTTP_200_OK
            )
        
class CompanyPolicyStatusChoices(APIView):
    model = Employee
    
    def get(self, request, *args, **kwargs):
        data = {
            choice[1]: choice[0]
            for choice in CompanyPolicyDocuments.StatusChoices.choices
        }
        return Response(
                success_response(data, "Successfully Fetched Company Status Choices", 200),
                status=status.HTTP_200_OK
            )

class CompanyPolicyVisibilityChoices(APIView):
    model = Employee
    
    def get(self, request, *args, **kwargs):
        data = {
            choice[1]: choice[0]
            for choice in CompanyPolicyDocuments.VisibilityChoices.choices
        }
        return Response(
                success_response(data, "Successfully Fetched Company Visibility Choices", 200),
                status=status.HTTP_200_OK
            )
        
class ATSPermissionView(APIView):
    model = Employee
    
    def get(self, request, *args, **kwargs):
        data = {'enable':get_ats_permission()}
        return Response(
                success_response(data, "Successfully Fetched ATS Permissions", 200),
                status=status.HTTP_200_OK
            )


class EmployeePreBoardingDetailsAPIView(APIView):
    model = EmployeePreBoardingDetails
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        company_id = kwargs.get("company_id")
        params = request.query_params
        if not company_id:
            try:
                company_id = request.user.employee_details.first().company_id
            except Exception as e:
                return Response(
                    error_response(e, 'Some thing went wrong', 404),
                    status=status.HTTP_404_NOT_FOUND
                )
        MultitenantSetup().create_to_connection(request)
        try:
            q_filters = db_models.Q(employee__company_id=company_id, is_deleted=False, is_welcome_mail_sent=False)
            
            if 'onboard_rejected' in params:
                q_filters &= (db_models.Q(conditional_offer_letter_status='Rejected') |
                                db_models.Q(appointment_letter_status='Rejected') |
                                db_models.Q(is_bgv_complted='Rejected') |
                                db_models.Q(is_responding=False)
                                )
            else:
                q_filters &= ~(db_models.Q(conditional_offer_letter_status='Rejected') |
                                db_models.Q(appointment_letter_status='Rejected') |
                                db_models.Q(is_bgv_complted='Rejected') |
                                db_models.Q(is_responding=False)
                                )
                
            paginator = self.pagination_class()
            today = timezone_now().date()
            qs = self.model.objects.filter(q_filters).annotate(
                                onboard_restriction_date=db_models.ExpressionWrapper(
                                        db_models.F('employee__date_of_join') + datetime.timedelta(days=30),
                                        output_field=db_models.DurationField()),
                                ).filter(onboard_restriction_date__gte = timezone_now().date()
                        ).annotate(
                                emp_name=db_models.F('employee__user__username'),
                                name=db_models.F('employee__user__username'),
                                first_name=db_models.F('employee__first_name'),
                                middle_name=db_models.F('employee__middle_name'),
                                last_name=db_models.F('employee__last_name'),
                                number=db_models.F('employee__work_details__employee_number'),
                                official_email = db_models.F('employee__official_email') ,
                                phone = db_models.F('employee__user__phone'),
                                date_of_join = db_models.F('employee__date_of_join'),
                                gender = db_models.F('employee__gender'),
                                personal_email = db_models.F('employee__personal_email'),
                                is_sign_up = db_models.F('employee__is_sign_up'),
                                department=db_models.F('employee__work_details__department__name'),
                                department_id = db_models.F('employee__work_details__department_id'),
                                sub_department=db_models.F('employee__work_details__sub_department__name'),
                                sub_department_id=db_models.F('employee__work_details__sub_department_id'),
                                designation=db_models.F('employee__work_details__designation__name'),
                                designation_id=db_models.F('employee__work_details__designation_id'),
                                work_location=db_models.F('employee__work_details__work_location'),
                                employee_type=db_models.Case(
                                    db_models.When(employee__work_details__employee_type__employee_type=10, then=db_models.Value("Full Time")),
                                    db_models.When(employee__work_details__employee_type__employee_type=20, then=db_models.Value("Part Time")),
                                    db_models.When(employee__work_details__employee_type__employee_type=30, then=db_models.Value("Intern")),
                                    db_models.When(employee__work_details__employee_type__employee_type=40, then=db_models.Value("On Contract")),
                                    db_models.When(employee__work_details__employee_type__employee_type=50, then=db_models.Value("Others")),
                                    default=db_models.Value(""), output_field=db_models.CharField()
                                ),
                                employee_status=db_models.F('employee__work_details__employee_status'),
                                employee_grade=db_models.F("employee__work_details__employee_grade__grade"),
                                employee_role=db_models.F('employee__roles__name'),
                                al_date_of_updated = db_models.functions.Cast(TimestampToStrDateTime(TimestampToIST(db_models.F('al_date_of_update'), 'Asia/Kolkata')), db_models.CharField()),
                                col_date_of_updated = db_models.functions.Cast(TimestampToStrDateTime(TimestampToIST(db_models.F('col_date_of_update'), 'Asia/Kolkata')), db_models.CharField()),
                                al_signature=db_models.Value(''),
                                col_signature=db_models.Value(''), 
                                rejected_status=db_models.expressions.Case(
                                            db_models.When(conditional_offer_letter_status = "Rejected",
                                                then=db_models.Value("Conditional offer letter"),
                                        ),
                                            db_models.When(appointment_letter_status="Rejected",
                                                then=db_models.Value("Appointment Letter"),
                                        ),
                                            db_models.When(is_bgv_complted="Rejected",
                                                then=db_models.Value("BVC")
                                        ),
                                        default=db_models.Value("Not Responding"),
                                        output_field=db_models.JSONField()
                                    ),
                                reporting_manager_id=ArrayAgg(
                                        db_models.F('employee__employee__manager_id'),
                                        filter=db_models.Q(employee__employee__isnull=False, employee__employee__manager_type__manager_type=ManagerType.PRIMARY, 
                                                           employee__employee__is_deleted=False, employee__employee__manager__work_details__employee_status='Active'),
                                        distinct=True
                                    ),
                                attendance_rules=db_models.expressions.Case(
                                        db_models.When(employee__assignedattendancerules__effective_date__lte = today,
                                            then = db_models.expressions.Func(
                                            db_models.Value('id'), 'employee__assignedattendancerules__id',
                                            db_models.Value('attendance_rule_id'), 'employee__assignedattendancerules__attendance_rule_id',
                                            db_models.Value('name'), 'employee__assignedattendancerules__attendance_rule__name',
                                            db_models.Value('enableOverTime'), 'employee__assignedattendancerules__attendance_rule__enable_over_time',
                                            db_models.Value('orgInTime'), 'employee__assignedattendancerules__attendance_rule__shift_in_time',
                                            db_models.Value('orgOutTime'), 'employee__assignedattendancerules__attendance_rule__shift_out_time',
                                            db_models.Value('autoClockOut'), 'employee__assignedattendancerules__attendance_rule__auto_clock_out',
                                            db_models.Value('shiftInTime'), TimestampToStr(db_models.F('employee__assignedattendancerules__attendance_rule__shift_in_time')),
                                            db_models.Value('shiftOutTime'), TimestampToStr(db_models.F('employee__assignedattendancerules__attendance_rule__shift_out_time')),
                                            function='jsonb_build_object',
                                            output_field=db_models.JSONField()
                                        ),
                                    ),
                                        db_models.When(employee__assignedattendancerules__effective_date__gt = today,
                                            then = db_models.expressions.Func(
                                            db_models.Value('id'), db_models.Value(None),
                                            db_models.Value('attendance_rule_id'), db_models.Value(None),
                                            db_models.Value('name'), db_models.Value(None),
                                            db_models.Value('enableOverTime'), db_models.Value(None),
                                            db_models.Value('orgInTime'), db_models.Value(None),
                                            db_models.Value('orgOutTime'), db_models.Value(None),
                                            db_models.Value('autoClockOut'), db_models.Value(None),
                                            function='jsonb_build_object',
                                            output_field=db_models.JSONField()
                                        ),
                                    ),
                                        db_models.When(employee__assignedattendancerules__isnull = True,
                                            then = db_models.expressions.Func(
                                            db_models.Value('id'), db_models.Value(None),
                                            db_models.Value('attendance_rule_id'), db_models.Value(None),
                                            db_models.Value('name'), db_models.Value(None),
                                            db_models.Value('enableOverTime'), db_models.Value(None),
                                            db_models.Value('orgInTime'), db_models.Value(None),
                                            db_models.Value('orgOutTime'), db_models.Value(None),
                                            db_models.Value('autoClockOut'), db_models.Value(None),
                                            function='jsonb_build_object',
                                            output_field=db_models.JSONField()
                                        ),
                                    ),
                                    default=db_models.Value(None),
                                    output_field=db_models.JSONField()
                                ),
                        ).values(
                            'id',"first_name","middle_name","last_name","employee_id",'name', 'emp_name',  "official_email", "phone", "number", "department", "sub_department", "designation",
                            "date_of_join", "gender", "work_location", "employee_type", "employee_grade","personal_email",
                            "employee_role", "employee_status","is_sign_up","reporting_manager_id",
                            "department_id","sub_department_id", "designation_id",
                            "is_conditional_offer_letter_sent","conditional_offer_letter_status","conditional_offer_letter","conditional_offer_letter_content",
                            "is_appointment_letter_sent","appointment_letter_status","appointment_letter","appointment_letter_content","is_bgv_complted",
                            "is_responding", "col_date_of_updated", "col_ip_address", "al_date_of_updated", "al_ip_address", "al_digital_sign", "col_digital_sign",
                            "is_welcome_mail_sent", "appointment_letter_pdf_content", "conditional_offer_letter_pdf_content",
                            "col_sign","al_sign","rejection_comments","al_signature","col_signature","rejected_status","attendance_rules"
                        ).order_by('-id')


            page = paginator.paginate_queryset(qs, request)
            response = success_response(
                    paginator.get_paginated_response(page), "Successfully fetched Employee Data", 200
                )
            MultitenantSetup().go_to_old_connection(request)
            return Response(
                response,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.critical(f"Employee Pre Boarding GET employees list Came to Exception, error :{e}")
            MultitenantSetup().go_to_old_connection(request)
            return Response(
                [],
                status=status.HTTP_200_OK
            )

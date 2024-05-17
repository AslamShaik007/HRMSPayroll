import pandas as pd
import traceback
import datetime

from django.db import models as db_models
from django.contrib.postgres.aggregates import ArrayAgg, JSONBAgg
from django.contrib.postgres.fields import ArrayField
from django.db import transaction

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from core.utils import timezone_now, get_paycycle_dates

from core.utils import success_response, error_response, search_filter_decode, excel_converter
from core.custom_paginations import CustomPagePagination

from directory.models import (Employee, EmployeeTypes, EmployeeReportingManager)

from .models import (
    LeaveRules, LeavesHistory, EmployeeLeaveRuleRelation, EmployeeWorkRuleRelation, WorkRules, LeaveRuleSettings
)
from attendance.models import AttendanceRuleSettings
from HRMSProject.multitenant_setup import MultitenantSetup

class LeaveRulesAPIViewV2(APIView):
    model = LeaveRules
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        company_id = kwargs.get("company_id")
        paginator = self.pagination_class()
        q_filters = db_models.Q(company_id=company_id, is_deleted=False)
        qs = self.model.objects.filter(q_filters).annotate(
            authorName = db_models.F('created_by__username'),           
            no_of_employees=db_models.Count('employeeleaverulerelation', filter=db_models.Q(employeeleaverulerelation__is_deleted=False, 
                                                                                            employeeleaverulerelation__employee__work_details__employee_status='Active',
                                                                                            employeeleaverulerelation__session_year__session_year=timezone_now().year), distinct=True)
        ).values(
            "id", "company", "name", "no_of_employees", "description", 
            "leaves_allowed_in_year", "weekends_between_leave", "holidays_between_leave",
            "creditable_on_accrual_basis", "accrual_frequency", "accruel_period", "allowed_under_probation",
            "carry_forward_enabled", "all_remaining_leaves", "max_leaves_to_carryforward", "continuous_leaves_allowed",
            "max_leaves_allowed_in_month", "allow_backdated_leaves", "no_of_employees", "is_deleted","is_leave_encashment_enabled",
            "all_remaining_leaves_for_encash","max_leaves_to_encash", "authorName", "valid_from", "valid_to", "includes_check_in_leave"
        )
        page = paginator.paginate_queryset(qs, request)
        return Response(
            success_response(
                paginator.get_paginated_response(page), "Successfully fetched Company Leave Rules", 200
            ),
            status=status.HTTP_200_OK
        )

class LeaveRuleDetailsGetUpdateAPIViewV2(APIView):
    model = LeaveRules
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        rule_id = kwargs.get("id")
        q_filters = db_models.Q(id=rule_id, is_deleted=False)
        qs = self.model.objects.filter(q_filters).annotate(
            no_of_employees=db_models.Count('employeeleaverulerelation', filter=db_models.Q(employeeleaverulerelation__is_deleted=False), distinct=True)
        ).values(
            "id", "company", "name", "no_of_employees", "description", 
            "leaves_allowed_in_year", "weekends_between_leave", "holidays_between_leave",
            "creditable_on_accrual_basis", "accrual_frequency", "accruel_period", "allowed_under_probation",
            "carry_forward_enabled", "all_remaining_leaves", "max_leaves_to_carryforward", "continuous_leaves_allowed",
            "max_leaves_allowed_in_month", "allow_backdated_leaves", "no_of_employees", "is_deleted","is_leave_encashment_enabled",
            "all_remaining_leaves_for_encash","max_leaves_to_encash", "valid_from", "valid_to", "includes_check_in_leave"
        )

        return Response(
            success_response(
                qs.first(), "Successfully fetched Leave Rule Data", 200
            ),
            status=status.HTTP_200_OK
        )

class EmployeeLeaveRuleRelationAPIViewV2(APIView):
    model = EmployeeLeaveRuleRelation
    pagination_class = CustomPagePagination
    
    def get_manager_employees(self,man_id):
        emp_id = man_id
        my_list = []
        tag = True
        while tag:
            query = EmployeeReportingManager.objects.filter(manager_id__in=emp_id,
                                                            manager__work_details__employee_status='Active',
                                                            is_deleted=False)
            if not query.exists():
                break
            my_list.extend(list(query.values_list('employee_id',flat=True)))
            emp_id = list(query.values_list('employee_id',flat=True))
        return my_list
    
    def get(self, request, *args, **kwargs):
        company_id = kwargs.get("company_id")
        params = request.query_params
        paginator = self.pagination_class()
        current_year = params.get('session_year', timezone_now().date().year) #timezone_now().date().year
        q_filters = db_models.Q(company_id=company_id, is_deleted=False, work_details__employee_status='Active')
        if "is_export" in params:
            qs = EmployeeLeaveRuleRelation.objects.filter(
                    employee__company_id=1, is_deleted=False, employee__work_details__employee_status='Active'
                ).values(
                    'employee__work_details__employee_number', 'employee__user__username', 
                    'employee__work_details__department__name', 'effective_date', 'employee__work_details__work_location',
                    'employee__work_details__employee_type', 'leave_rule'
                )
            data = pd.DataFrame(qs,columns=['employee__work_details__employee_number', 'employee__user__username', 
                    'employee__work_details__department__name', 'effective_date', 'employee__work_details__work_location',
                    'employee__work_details__employee_type', 'leave_rule__name'])
            data.rename(columns={'employee__work_details__employee_number':'EmpId','employee__user__username':'Employee Name',
                                         'employee__work_details__department__name':'Department','effective_date':'Effective Date','employee__work_details__work_location':'Work Location',
                                         'employee__work_details__employee_type':'Employee Type','leave_rule__name':'leave Rule'
                                         }, inplace=True)
            file_name = f"export_{timezone_now().date()}.xlsx"
            return excel_converter(data,file_name)
        if "search_filter" in params:
            q_filters &= (
            db_models.Q(user__username__icontains=search_filter_decode(params.get("search_filter"))) |
            db_models.Q(official_email__icontains=search_filter_decode(params.get("search_filter"))) | 
            db_models.Q(work_details__employee_number__icontains=search_filter_decode(params['search_filter']))
            )
        employee_checkd_in = request.user.employee_details.first()
        employee_checkd_in_role = employee_checkd_in.roles.first().name
        if employee_checkd_in_role in ['TEAM LEAD']:
            check_ids = list(EmployeeReportingManager.objects.filter(manager_id=employee_checkd_in.id, is_deleted=False).values_list("employee_id", flat=True))
            # check_ids.append(employee_checkd_in.id)
            q_filters &= db_models.Q(id__in=check_ids)
        if employee_checkd_in_role in ['MANAGER']:
            q_filters &= db_models.Q(id__in=self.get_manager_employees([employee_checkd_in]))
        qs = Employee.objects.filter(q_filters).annotate(
            employee_data=db_models.expressions.Func(
                db_models.Value("id"), "id",
                db_models.Value("name"), 'user__username',
                db_models.Value('gender'), 'gender',
                db_models.Value('emp_id'), 'work_details__employee_number',
                db_models.Value('department'), 'work_details__department__name',
                db_models.Value('sub_department'), 'work_details__sub_department__name',
                db_models.Value('designation'), 'work_details__designation__name',
                db_models.Value('location'), 'work_details__work_location',
                db_models.Value('date_of_joining'), 'date_of_join',
                db_models.Value('type'), db_models.Case(
                    *[db_models.When(work_details__employee_type__employee_type=i[0], then=db_models.Value(i[1])) for i in EmployeeTypes.EMPLOYEE_TYPE_CHOICES],
                    default=db_models.Value(""), output_field=db_models.CharField()   
                ),
                function="jsonb_build_object",
                output_field=db_models.JSONField()
            ),
            leave_rule_data=ArrayAgg(
                db_models.expressions.Func(
                    db_models.Value('rel_id'), "employeeleaverulerelation__id",
                    db_models.Value('leave_rule_id'), "employeeleaverulerelation__leave_rule_id",
                    db_models.Value('name'), "employeeleaverulerelation__leave_rule__name",
                    db_models.Value('remaining_leaves'), "employeeleaverulerelation__remaining_leaves",
                    db_models.Value('earned_leaves'), "employeeleaverulerelation__earned_leaves",
                    db_models.Value('used_leaves'), "employeeleaverulerelation__used_so_far",
                    function="jsonb_build_object",
                    output_field=db_models.JSONField()
                ),
                distinct=True,
                filter=db_models.Q(
                    employeeleaverulerelation__is_deleted=False, employeeleaverulerelation__session_year__session_year=current_year 
                )
            ),
            reporting_manager=ArrayAgg(
                # db_models.functions.Concat(
                #     db_models.F('employee__manager__first_name'), db_models.Value(" "), db_models.F('employee__manager__last_name'),
                #     output_field=db_models.CharField()   
                # ),
                db_models.F('employee__manager__user__username'),
                filter=db_models.Q(employee__isnull=False, employee__manager_type__manager_type=10, employee__is_deleted=False, employee__manager__work_details__employee_status='Active'),
                distinct=True
            ),
        ).values(
            "employee_data", "leave_rule_data", "reporting_manager"
        )
        
        page = paginator.paginate_queryset(qs, request)
        return Response(
            success_response(
                paginator.get_paginated_response(page), "Successfully fetched Employee Leave Relations", 200
            ),
            status=status.HTTP_200_OK
        )

class LeavesHistoryRetrieveViewV2(APIView):
    model = LeavesHistory
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        employee_id = kwargs.get("employee_id")
        paginator = self.pagination_class()
        params = request.query_params
        assigned_leave_rules = EmployeeLeaveRuleRelation.objects.filter(
            employee_id=employee_id, is_deleted=False
        ).only('leave_rule_id').values_list("leave_rule_id", flat=True)
        q_filters = db_models.Q(employee_id=employee_id, is_deleted=False, leave_rule_id__in=assigned_leave_rules)
        if 'search_filter' in params:
            q_filters &= (
                db_models.Q(employee__user__username__icontains=search_filter_decode(params.get("search_filter"))) |
                db_models.Q(leave_rule__name__icontains=search_filter_decode(params.get("search_filter"))) |
                db_models.Q(employee__work_details__employee_number__icontains=search_filter_decode(params.get("search_filter")))
            )
        qs = self.model.objects.filter(q_filters).annotate(
            leave_approved_by=db_models.functions.Concat(
                db_models.F('approved_by__first_name'), db_models.Value(" "), db_models.F("approved_by__last_name"),
                output_field=db_models.CharField()
            ),
            balance=ArrayAgg(
                "leave_rule__employeeleaverulerelation__remaining_leaves",
                filter=db_models.Q(leave_rule__employeeleaverulerelation__employee_id=db_models.F('employee_id'), leave_rule__employeeleaverulerelation__leave_rule_id=db_models.F('leave_rule_id'))
            ),
            department=db_models.F('employee__work_details__department__name'),
            designation=db_models.F('employee__work_details__designation__name'),
            employee_name=db_models.functions.Concat(
                db_models.F('employee__first_name'), db_models.Value(" "), db_models.F("employee__last_name"),
                output_field=db_models.CharField()
            ),
            employee_number=db_models.F("employee__work_details__employee_number"),
            leave_rule_name=db_models.F('leave_rule__name'),
            status_display=db_models.Case(
                # *[db_models.When(status=i[0], then=db_models.Value(i[1])) for i in self.model.STATUS_CHOICES],
                db_models.When(db_models.Q(status=10, is_revoked=False), then=db_models.Value("Approved")),
                db_models.When(db_models.Q(status=10, is_revoked=True), then=db_models.Value("Revoke Rejected")),
                db_models.When(db_models.Q(status=20, is_revoked=False), then=db_models.Value("Pending")),
                db_models.When(db_models.Q(status=20, is_revoked=True), then=db_models.Value("Revoke Pending")),
                db_models.When(db_models.Q(status=30, is_revoked=False), then=db_models.Value("Cancelled")),
                db_models.When(db_models.Q(status=30, is_revoked=True), then=db_models.Value("Revoke Approved")),
                db_models.When(db_models.Q(status=40, is_revoked=False), then=db_models.Value("Rejected")),
                db_models.When(db_models.Q(status=40, is_revoked=True), then=db_models.Value("Revoke Rejected")),
                db_models.When(db_models.Q(status=50), then=db_models.Value("Revoke")),
                default=db_models.Value(""),
                output_field=db_models.CharField()
            ),
            end_day_session_display=db_models.Case(
                *[db_models.When(end_day_session=i[0], then=db_models.Value(i[1])) for i in self.model.DAY_SESSION_CHOICES],
                    default=db_models.Value(""), output_field=db_models.CharField()
            ),
            start_day_session_display=db_models.Case(
                *[db_models.When(start_day_session=i[0], then=db_models.Value(i[1])) for i in self.model.DAY_SESSION_CHOICES],
                    default=db_models.Value(""), output_field=db_models.CharField()
            ),
        ).values(
            "id", "employee", "employee_name", "employee_number", "leave_rule_name", "department", "designation",
            "start_date", "start_day_session", "end_date", "end_day_session", "reason", "reason_for_rejection",
            "approved_on", "approved_by", "reason_for_rejection", "status", "status_display",
            "no_of_leaves_applied", "balance", "created_at", "attachment","backdated_approval_reason"
        ).order_by("-created_at")
        page = paginator.paginate_queryset(qs, request)
        return Response(
            success_response(
                paginator.get_paginated_response(page), "Successfully fetched Employee Leave Relations", 200
            ),
            status=status.HTTP_200_OK
        )

class LeavesHistoryCompanyRetrieveViewV2(APIView):
    model = LeavesHistory
    pagination_class = CustomPagePagination
    
    def get_tenant_employees(self,man_id, headers):
        emp_id = man_id
        my_list = []
        tag = True
        while tag:
            query = EmployeeReportingManager.objects.filter(
                                        multitenant_manager_emp_id=emp_id,
                                        # manager__work_details__employee_status='Active',
                                        is_deleted=False
                                        )
            if not query.exists():
                break
            my_list.extend(list(query.values_list('employee_id',flat=True)))
            emp_id = list(query.values_list('employee_id',flat=True))
        return my_list
    
    def get_manager_employees(self,man_id, headers):
        emp_id = man_id
        my_list = []
        tag = True
        while tag:
            if headers.get('X-CURRENT-COMPANY') == headers.get('X-SELECTED-COMPANY'):
                query = EmployeeReportingManager.objects.filter(
                    manager_id__in=emp_id,
                    manager__work_details__employee_status='Active',
                                                                is_deleted=False)
            else:
                query = EmployeeReportingManager.objects.filter(
                                            multitenant_manager_emp_id=emp_id,
                                            # manager__work_details__employee_status='Active',
                                            is_deleted=False
                                            )
            if not query.exists():
                break
            my_list.extend(list(query.values_list('employee_id',flat=True)))
            emp_id = list(query.values_list('employee_id',flat=True))
        return my_list
    
    
    
    def get(self, request, *args, **kwargs):
        employee_checkd_in = request.user.employee_details.first()
        employee_checkd_in_role = employee_checkd_in.roles.first().name
        headers = request.headers
        e_number = employee_checkd_in.work_details.employee_number
        if headers.get('X-CURRENT-COMPANY') == headers.get('X-SELECTED-COMPANY'):
            primary_manager_query = """ArrayAgg(db_models.Case(
                                    db_models.When(db_models.Q(status__in=[10,40]), then=db_models.F('updated_by__username')),
                                    db_models.When(db_models.Q(employee__employee__isnull=False, employee__employee__is_deleted=False, 
                                                                employee__employee__manager__work_details__employee_status='Active',
                                                                employee__employee__manager_type__manager_type=10), 
                                                            then=db_models.F('employee__employee__manager__user__username')),
                                    default=db_models.Value(''), output_field=db_models.CharField()),
                                    filter=db_models.Q(employee__employee__isnull=False, employee__employee__manager_type__manager_type=10, 
                                    employee__employee__is_deleted=False, employee__employee__manager__work_details__employee_status='Active'),
                                    distinct=True)"""
            m_list = self.get_manager_employees([employee_checkd_in], request.headers)
        else:
            MultitenantSetup().create_to_connection(request)
            primary_manager_query = """ArrayAgg(db_models.Case(
                                    db_models.When(db_models.Q(status__in=[10,40]), then=db_models.F('updated_by__username')),
                                    db_models.When(db_models.Q(
                                        employee__employee__isnull=False, 
                                        employee__employee__is_deleted=False, 
                                        # employee__employee__work_details__employee_status='Active',
                                        employee__employee__manager_type__manager_type=10
                                    ), 
                                    then=db_models.F('employee__employee__multitenant_manager_name')),
                                    default=db_models.Value(''), output_field=db_models.CharField()),
                                    filter=db_models.Q(employee__employee__isnull=False, employee__employee__manager_type__manager_type=10, 
                                    employee__employee__is_deleted=False, employee__employee__manager__work_details__employee_status='Active'),
                                    distinct=True)"""
            m_list = self.get_tenant_employees(e_number, request.headers)
        company_id = kwargs.get("company_id")
        paginator = self.pagination_class()
        params = request.query_params
        q_filters = db_models.Q(employee__company_id=company_id, is_deleted=False)
        if employee_checkd_in_role in ['TEAM LEAD']:
            # check_ids = list(EmployeeReportingManager.objects.filter(manager_id=employee_checkd_in.id).values_list("employee_id", flat=True))
            # check_ids.append(employee_checkd_in.id)
            q_filters &= db_models.Q(employee_id__in=EmployeeReportingManager.objects.filter(manager_id=employee_checkd_in.id, is_deleted=False).values_list("employee_id", flat=True))
        if employee_checkd_in_role in ['MANAGER']:
            q_filters &= db_models.Q(employee_id__in=m_list)
        if 'search_filter' in params:
            q_filters &= db_models.Q(
                db_models.Q(employee__user__username__icontains=search_filter_decode(params.get("search_filter"))) |
                db_models.Q(leave_rule__name__icontains=search_filter_decode(params.get("search_filter"))) |
                db_models.Q(employee__work_details__employee_number__icontains=search_filter_decode(params.get("search_filter")))
            )
        if 'department_id' in params:
            q_filters &= db_models.Q(employee__work_details__department_id__in=params['department_id'].split(','))
            
        if 'employee_id' in params:
            q_filters &= db_models.Q(employee_id__in=params.get('employee_id').split(','))
            
        if 'leave_type' in params:
            q_filters &= db_models.Q(leave_rule_id__in=params.get('leave_type').split(','))
            
        if 'session_year' in params:
            q_filters &= db_models.Q(leave_rule__employeeleaverulerelation__session_year__session_year__in=params.get('session_year').split(','))
              
        if 'start_date' in params and 'end_date' in params:
            # q_filters &= db_models.Q(
            #     db_models.Q(start_date__range=(params['start_date'], params['end_date'])) |
            #     db_models.Q(end_date__range=(params['start_date'], params['end_date'])))
            q_filters &= db_models.Q(start_date__lte = params['end_date'],end_date__gte = params['start_date'])
        # else:
        #     att_sett_data = AttendanceRuleSettings.objects.filter(company_id=company_id)
        #     psc_from_date =  att_sett_data.first().attendance_input_cycle_from
        #     psc_to_date   =  att_sett_data.first().attendance_input_cycle_to
        #     pay_cycle_from_date,pay_cycle_to_date,current_payout_date = get_paycycle_dates(timezone_now(),psc_from_date,psc_to_date)
        #     q_filters &= db_models.Q(start_date__lte=timezone_now().date(),end_date__gte=pay_cycle_from_date.date())
        #     start_date = pay_cycle_from_date.date().strftime('%Y-%m-%d')
        if 'status' in params:
            if params['status'] in ['10','20','30','40']:
                q_filters &= db_models.Q(status=params['status'])

        qs = list(self.model.objects.filter(q_filters).annotate(
            #     emp_leave_rule_relations=db_models.functions.Cast(ArrayAgg('employee__employeeleaverulerelation__leave_rule_id', distinct=True), ArrayField(db_models.IntegerField()))
            # ).annotate(
            leave_approved_by=db_models.F('approved_by__user__username'),
            leave_rejected_by=db_models.Case(
                db_models.When(status=40, then=db_models.F('updated_by__username')),
                default=db_models.Value(""), output_field=db_models.CharField()
            ),
            balance=ArrayAgg(
                "leave_rule__employeeleaverulerelation__remaining_leaves",
                filter=db_models.Q(leave_rule__employeeleaverulerelation__employee_id=db_models.F('employee_id'), leave_rule__employeeleaverulerelation__leave_rule_id=db_models.F('leave_rule_id'))
            ),
            department=db_models.F('employee__work_details__department__name'),
            designation=db_models.F('employee__work_details__designation__name'),
            employee_name=db_models.F('employee__user__username'),
            employee_number=db_models.F("employee__work_details__employee_number"),
            leave_rule_name=db_models.F('leave_rule__name'),
            status_display=db_models.Case(
                # *[db_models.When(status=i[0], then=db_models.Value(i[1])) for i in self.model.STATUS_CHOICES],
                db_models.When(db_models.Q(status=10, is_revoked=False), then=db_models.Value("Approved")),
                db_models.When(db_models.Q(status=10, is_revoked=True), then=db_models.Value("Revoke Rejected")),
                db_models.When(db_models.Q(status=20, is_revoked=False), then=db_models.Value("Pending")),
                db_models.When(db_models.Q(status=20, is_revoked=True), then=db_models.Value("Revoke Pending")),
                db_models.When(db_models.Q(status=30, is_revoked=False), then=db_models.Value("Cancelled")),
                db_models.When(db_models.Q(status=30, is_revoked=True), then=db_models.Value("Revoke Approved")),
                db_models.When(db_models.Q(status=40, is_revoked=False), then=db_models.Value("Rejected")),
                db_models.When(db_models.Q(status=40, is_revoked=True), then=db_models.Value("Revoke Rejected")),
                db_models.When(db_models.Q(status=50), then=db_models.Value("Revoke")),
                default=db_models.Value(""),
                output_field=db_models.CharField()
            ),
            end_day_session_display=db_models.Case(
                *[db_models.When(end_day_session=i[0], then=db_models.Value(i[1])) for i in self.model.DAY_SESSION_CHOICES],
                    default=db_models.Value(""), output_field=db_models.CharField()
            ),
            start_day_session_display=db_models.Case(
                *[db_models.When(start_day_session=i[0], then=db_models.Value(i[1])) for i in self.model.DAY_SESSION_CHOICES],
                    default=db_models.Value(""), output_field=db_models.CharField()
            ),
            date_of_join=db_models.F('employee__date_of_join'),
            # primary_manager = ArrayAgg('employee__employee__manager__user__username',
            #             filter=db_models.Q(employee__employee__isnull=False, employee__employee__is_deleted=False, employee__employee__manager__work_details__employee_status='Active',
            #                                employee__employee__manager_type__manager_type=10),
            #             distinct=True)
            primary_manager=eval(primary_manager_query),
        ).filter(
            # ~db_models.Q(primary_manager="")    
        ).values(
            "id", "employee", "employee_name", "employee_number", "leave_rule_name", "department", "designation",
            "start_date", "start_day_session", "end_date", "end_day_session", "reason", "reason_for_rejection",
            "approved_on", "approved_by", "reason_for_rejection", "status", "status_display",
            "no_of_leaves_applied", "balance", "created_at__date", "leave_approved_by",
            "leave_rejected_by", "attachment","is_backdated","date_of_join","primary_manager","backdated_approval_reason"
        ).order_by("-updated_at")
        )
        
        if "is_export" in params:
            data_df = pd.DataFrame(qs,columns=["employee_number","employee_name","department","leave_rule_name",
                                               "start_date","end_date","no_of_leaves_applied","created_at__date","status_display",
                                               "date_of_join","primary_manager"])
            if data_df.empty:
                return Response(
                    error_response('No Data Found To Export', "No Data Found To Export", 404),
                    status=status.HTTP_404_NOT_FOUND
                )
            # if 'primary_manager' in data_df.columns:
            #     data_df.primary_manager = data_df.primary_manager.apply(lambda m:', '.join(m) if m else '') 
                
            data_df['start_date'] = data_df.apply(lambda obj : obj['start_date'].strftime("%d-%m-%Y"), axis=1)
            data_df['end_date'] = data_df.apply(lambda obj : obj['end_date'].strftime("%d-%m-%Y"), axis=1)
            data_df['created_at__date'] = data_df.apply(lambda obj : obj['created_at__date'].strftime("%d-%m-%Y"), axis=1)
            data_df['date_of_join'] = data_df.apply(lambda obj : obj['date_of_join'].strftime("%d-%m-%Y"), axis=1)
            data_df.rename(columns={"employee_number":"ID","employee_name":"Employee Name","date_of_join":"DOJ","department":"Department",
                                    "primary_manager":"Reporting Manager", "leave_rule_name":"Leave Rule",""
                                    "created_at__date":"Created Date","start_date":"Start Date","end_date":"End Date","no_of_leaves_applied":"No Of Leaves Applied",
                                    "status_display":"Status"},inplace=True)

            file_name = f"export_leave_history_{timezone_now().date()}.xlsx"
            MultitenantSetup().go_to_old_connection(request)
            return excel_converter(data_df,file_name)
        MultitenantSetup().go_to_old_connection(request)  
        page = paginator.paginate_queryset(qs, request)
        return Response(
            success_response(
                paginator.get_paginated_response(page), "Successfully fetched Company Employee Leave Relations", 200
            ),
            status=status.HTTP_200_OK
        )

class EmployeeLeaveRuleRelationRetrieveViewV2(APIView):
    model = EmployeeLeaveRuleRelation
    
    
    def get(self, request, *args, **kwargs):
        today = timezone_now()
        employee_id = kwargs.get("employee_id")
        current_year = request.query_params.get('session_year', timezone_now().date().year)
        q_filters = db_models.Q(employee_id=employee_id, is_deleted=False,
                                effective_date__lte = today, session_year__session_year=current_year)
        params = request.query_params
        if 'exclude_lop' in params:
            q_filters &= ~db_models.Q(leave_rule__name='Loss Of Pay')
        qs = self.model.objects.filter(q_filters).annotate(
            leave_rule_details=db_models.expressions.Func(
                db_models.Value("id"), "leave_rule_id",
                db_models.Value("name"), "leave_rule__name",
                db_models.Value("description"), "leave_rule__description",
                db_models.Value("is_backdated"), "leave_rule__allow_backdated_leaves",
                function='jsonb_build_object',
                output_field=db_models.JSONField()
            )
        ).values(
            "id", "employee", "effective_date", "remaining_leaves", "earned_leaves", "used_so_far",
            "penalty_deduction", "used_lop_leaves", "leave_rule", "leave_rule_details"
        )
        return Response(
            success_response(
                qs, "Successfully fetched Employee Leave Relations", 200
            ),
            status=status.HTTP_200_OK
        )

class EmpGetEmployeeWorkRuleRelationRetrieveViewV2(APIView):
    model = EmployeeWorkRuleRelation
    
    def get(self, request, *args, **kwargs):
        try:
            today = timezone_now()
            employee_id = kwargs.get("employee_id")
            q_filters = db_models.Q(employee_id=employee_id, is_deleted=False,effective_date__lte = today)
            
            qs = self.model.objects.filter(q_filters).annotate(
                work_rule_details=db_models.expressions.Func(
                    db_models.Value("id"), "work_rule_id",
                    db_models.Value("company"), "work_rule__company",
                    db_models.Value("name"), "work_rule__name",
                    db_models.Value("description"), "work_rule__description",
                    db_models.Value("is_default"), "work_rule__is_default",
                    db_models.Value("no_of_employees"), db_models.Count(
                        "work_rule__employeeworkrulerelation",
                        filter=db_models.Q(work_rule__employeeworkrulerelation__employee__work_details__employee_status="Active"),
                        distinct=True,    
                    ),
                    db_models.Value("work_rule_choices"), 
                    ArrayAgg(
                        db_models.expressions.Func(
                            db_models.Value("id"), "work_rule__work_rule_choices__id",
                            db_models.Value("work_rule"), "work_rule__work_rule_choices__work_rule",
                            db_models.Value("monday"), "work_rule__work_rule_choices__monday",
                            db_models.Value("tuesday"), "work_rule__work_rule_choices__tuesday",
                            db_models.Value("wednesday"), "work_rule__work_rule_choices__wednesday",
                            db_models.Value("thursday"), "work_rule__work_rule_choices__thursday",
                            db_models.Value("friday"), "work_rule__work_rule_choices__friday",
                            db_models.Value("saturday"), "work_rule__work_rule_choices__saturday",
                            db_models.Value("sunday"), "work_rule__work_rule_choices__sunday",
                            db_models.Value("week_number"), "work_rule__work_rule_choices__week_number",
                            function="jsonb_build_object",
                            output_field=db_models.JSONField()
                        ),
                        distinct=True
                    ),
                    function="jsonb_build_object",
                    output_field=db_models.JSONField()
                )
            ).values(
                "employee",
                "work_rule_details",
                "effective_date",
            )
            return Response(
                success_response(qs, "successfully fetched data", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong", 400),
                status=status.HTTP_400_BAD_REQUEST
            )

class WorkRulesRetrieveViewV2(APIView):
    """
    View to retrieve compnay work rule
    """
    model = WorkRules
    pagination_class = CustomPagePagination
    
    def get(self,request, *args, **kwargs):
        company_id = self.kwargs.get('company_id')
        q_filters= db_models.Q(company_id = company_id, is_deleted = False)
        # if "is_export" in request.query_params:
        #     df = pd.DataFrame(
        #         WorkRules.objects.filter(is_deleted=False).annotate(emp_count=Count('employeeworkrulerelation__employee', filter=db_models.Q(employeeworkrulerelation__employee__work_details__employee_status='Active'))).values('name', 'description', 'emp_count')
        #     )
        #     file_name = f"work_weeks_data_{timezone_now().date()}.xlsx"
        #     return excel_converter(df, file_name)  
        work_rule_query = self.model.objects.filter(q_filters).annotate(
            authorName = db_models.F('created_by__username'),           
            no_of_employees = db_models.Count('employeeworkrulerelation',filter=(db_models.Q(is_deleted=False)),distinct=True),
            work_rule_choices_new=ArrayAgg(db_models.expressions.Func(
                db_models.Value('id'), 'work_rule_choices__id',
                db_models.Value('work_rule'), 'id',
                db_models.Value('monday'), 'work_rule_choices__monday',
                db_models.Value('tuesday'), 'work_rule_choices__tuesday',
                db_models.Value('wednesday'), 'work_rule_choices__wednesday',
                db_models.Value('thursday'), 'work_rule_choices__thursday',
                db_models.Value('friday'), 'work_rule_choices__friday',
                db_models.Value('saturday'), 'work_rule_choices__saturday',
                db_models.Value('sunday'), 'work_rule_choices__sunday',
                db_models.Value('week_number'), 'work_rule_choices__week_number',
                function='jsonb_build_object',
                output_field=db_models.JSONField()
            ),distinct=True)
        ).values('id','company','name','description','is_default','no_of_employees','work_rule_choices_new', 'authorName').order_by('-id')
        
        df = pd.DataFrame(work_rule_query)
        df.rename(columns = {'work_rule_choices_new':'work_rule_choices'}, inplace = True)
        if "is_export" in request.query_params:
            file_name = f"work_weeks_data_{timezone_now().date()}.xlsx"
            return excel_converter(df, file_name)  
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(df.to_dict(orient='records'), request)

        return Response(
            success_response(
                paginator.get_paginated_response(page),
                "Successfully fetched work rules Details", 200
            ),
            status=status.HTTP_200_OK
        )

class EmployeeWorkRuleRelationRetrieveViewV2(APIView):
    """
    View to retrive employee workrule relations
    """
    model = Employee
    pagination_class = CustomPagePagination
    
    def get(self,request, *args, **kwargs):
        company_id = self.kwargs.get('company_id')
        params = request.query_params
        q_filters = db_models.Q(company_id = company_id, is_deleted = False, work_details__employee_status='Active')
        if 'search_filter' in params:
                q_filters &= (
                    db_models.Q(user__username__icontains=search_filter_decode(params.get("search_filter"))) |
                    db_models.Q(employeeworkrulerelation__work_rule__name__icontains = search_filter_decode(params.get("search_filter"))) |
                    db_models.Q(work_details__employee_number__icontains=search_filter_decode(params.get("search_filter")))
                )
    
        work_rule_query = self.model.objects.filter(q_filters
                ).annotate(
                    emp_count = db_models.Count('employeeworkrulerelation__work_rule__employeeworkrulerelation',
                        filter=(db_models.Q(employeeworkrulerelation__work_rule__employeeworkrulerelation__is_deleted=False)),distinct=True),
                    type = db_models.Case(
                        *[db_models.When(work_details__employee_type__employee_type=i[0], then=db_models.Value(i[1])) for i in EmployeeTypes.EMPLOYEE_TYPE_CHOICES],
                        default=db_models.Value(''), output_field=db_models.CharField()),
                ).annotate(
                    work_rule_data=db_models.expressions.Case(
                        db_models.When(employeeworkrulerelation__isnull=True,
                            then=db_models.expressions.Func(
                                db_models.Value(''), db_models.Value(''),
                                function='jsonb_build_object',
                                output_field=db_models.JSONField()
                            ),
                        ),
                        db_models.When(employeeworkrulerelation__isnull=False,
                            then=db_models.expressions.Func(
                                db_models.Value('rel_id'), 'employeeworkrulerelation',
                                db_models.Value('work_rule_id'), 'employeeworkrulerelation__work_rule_id',
                                db_models.Value('name'), 'employeeworkrulerelation__work_rule__name',
                                db_models.Value('no_of_employees'), 'emp_count',
                                db_models.Value('effective_date'),'employeeworkrulerelation__effective_date',
                                function='jsonb_build_object',
                                output_field=db_models.JSONField()
                            ),
                        ),
                        default=db_models.Value(None),  
                        output_field=db_models.JSONField()
                    ),
                    employee_data=db_models.expressions.Func(
                        db_models.Value('id'), 'id',
                        db_models.Value('emp_id'), 'work_details__employee_number',
                        db_models.Value('name'), db_models.functions.Concat("first_name", db_models.Value(" "), "middle_name",db_models.Value(" "), "last_name"),
                        db_models.Value('department'), 'work_details__department__name',
                        db_models.Value('location'), 'work_details__work_location',
                        db_models.Value('type'), 'type',
                        function='jsonb_build_object',
                        output_field=db_models.JSONField()
                    )
                ).values('employee_data','work_rule_data').order_by('-id')
        if "is_export" in params:
            qs = EmployeeWorkRuleRelation.objects.filter(
                    employee__company_id=company_id, is_deleted=False, employee__work_details__employee_status='Active'
                ).values(
                    'employee__work_details__employee_number', 'employee__user__username', 
                    'employee__work_details__department__name', 'effective_date', 'employee__work_details__work_location',
                    'employee__work_details__employee_type', 'work_rule__name'
                )
            data = pd.DataFrame(qs,columns=['employee__work_details__employee_number', 'employee__user__username', 
                    'employee__work_details__department__name', 'effective_date', 'employee__work_details__work_location',
                    'employee__work_details__employee_type', 'work_rule__name'])
            data.rename(columns={'employee__work_details__employee_number':'EmpId','employee__user__username':'Employee Name',
                                         'employee__work_details__department__name':'Department','effective_date':'Effective Date','employee__work_details__work_location':'Work Location',
                                         'employee__work_details__employee_type':'Employee Type','work_rule__name':'Work Rule'
                                         }, inplace=True)
            file_name = f"export_{timezone_now().date()}.xlsx"
            return excel_converter(data,file_name) 
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(work_rule_query, request)

        return Response(
            success_response(
                paginator.get_paginated_response(page),
                "Successfully fetched work rules Details", 200
            ),
            status=status.HTTP_200_OK
        )
        

class EmployeeWorkRuleBulkAPIViewV2(APIView):
    """
    View to Assign Employee Work rule
    """
    model = EmployeeWorkRuleRelation
    
    def patch(self, request, *args, **kwargs):
        try:
            transaction.set_autocommit(autocommit=False)
            request_data = request.data
            effective_date = datetime.datetime.strptime(request_data.get('effective_date'), "%m/%d/%Y").strftime("%Y-%m-%d")
            
            df = pd.DataFrame(request_data)

            df['work_rule_rel_existed'] = df.apply(lambda obj: True if EmployeeWorkRuleRelation.objects.filter(employee_id = int(obj['employee'])).exists() else False,axis=1)
            if True in list(set(df['work_rule_rel_existed'])) and int(effective_date.split('-')[2]) != 1:
                return Response(
                    error_response('Cant change workweek at mid of month', 'Cant change workweek at mid of month', 400),
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            df.apply(lambda obj: 
                (EmployeeWorkRuleRelation.objects.filter(employee_id = int(obj['employee'])
                                ).update(work_rule_id = int(obj['work_rule']), effective_date = effective_date)
                    ) if obj['work_rule_rel_existed'] else 
                (EmployeeWorkRuleRelation.objects.create(
                                                work_rule_id = int(obj['work_rule']), 
                                                effective_date = effective_date,
                                                employee_id = int(obj['employee']))
                ), axis=1
            )
        except Exception as e:
            response = error_response(str(e))
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        massage = 'Work Rule Assigned Successfully'
        response = success_response('', massage, 200)
        transaction.commit()
        return Response(response,status=status.HTTP_201_CREATED)
    
class CompanyLeaveRuleSettingsAPIViewV2(APIView):

    model = LeaveRuleSettings
    pagination_class = CustomPagePagination

    def get(self, request, *args, **kwargs):

        params = request.query_params
        company = params.get("company")
        try:
            if "company" not in params:
                return Response(
                            error_response("CompanyId Required", "CompanyId Required", 400),
                            status=status.HTTP_400_BAD_REQUEST
                        )
            q_filters = db_models.Q(company=company)
            paginator = self.pagination_class()
            data = self.model.objects.filter(q_filters).values(
                "id","company","calendar_type","start_date","end_date","is_calendar_updated","created_at"
            )
            page = paginator.paginate_queryset(data, request)
            return Response(
                    success_response(paginator.get_paginated_response(page), "Successfully fetched company leave settings", 200),
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
            obj = self.model.objects.get(id = params.get("id"))
            obj.calendar_type = request.data.get("calendar_type")
            obj.start_date = request.data.get("start_date")
            obj.end_date = request.data.get("end_date")
            obj.save()
            return Response(
                success_response("Company Calendar Settings Updated Successfully", "Company Calendar Settings Updated Successfully", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )


# lrs = EmployeeLeaveRuleRelation.objects.using(db_con).filter(session_year__session_year=2024).order_by('leave_rule_id').distinct('leave_rule_id').values_list('leave_rule_id', flat=True)
# LeaveRules.objects.filter(id__in=lrs).update(valid_from='2023-12-21', valid_to='2024-12-20')

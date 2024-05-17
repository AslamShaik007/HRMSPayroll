import os
import datetime

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Value, Case, When
from django.db.models.functions import Concat
from django.db import models as db_models

import pandas as pd
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from attendance.models import (
    AnamolyHistory,
    AssignedAttendanceRules,
    EmployeeCheckInOutDetails,
)
from core.utils import generate_random_string, error_response
from directory.models import Employee, EmployeeReportingManager
from HRMSApp.models import CompanyDetails
from leave.models import LeavesHistory, EmployeeLeaveRuleRelation
from reports.models import Report
from reports.services import EmployeeExporter

from .serializers import EmployeeReportSerializer

from core.utils import excel_converter, timezone_now
class EmployeeExportView(APIView):
    """
    Employee Export view

    AJAY, 31.01.2023
    """
    
    model = Employee

    def post(self, request, *args, **kwargs):
        exporter = EmployeeExporter()
        data = request.data
        df = exporter.generate(fields=data["fields"], ids=data["id"])
        file_name = f"employee_data_{timezone_now().date()}.xlsx"
        return excel_converter(df,file_name)
            


class EmployeeReportRetrieveView(ListAPIView):
    """
    This class is a ListAPIView that returns a list of all the reports that are associated with an
    employee

    AJAY, 01.02.2023
    """

    serializer_class = EmployeeReportSerializer

    def get_queryset(self):
        return Report.objects.filter(
            content_type=ContentType.objects.get_for_model(Employee), is_deleted=False
        )


class ExportLeaveHistoryAPIView(APIView):
    """
    View to export employee leave history

    SURESH, 26.04.2023
    """

    http_method_names = ["post"]
    model = CompanyDetails

    def post(self, request):
        data = request.data
        q_filters = db_models.Q()
        if data.get('company'):
            q_filters = db_models.Q(employee__company_id=data.get('company'), is_deleted=False)

        if data.get('from_date') and data.get('to_date'):
            # q_filters &= db_models.Q(
            #     db_models.Q(start_date__range=(data['from_date'], data['to_date'])) |
            #     db_models.Q(end_date__range=(data['from_date'], data['to_date'])))
            q_filters &= db_models.Q(start_date__lte = data['to_date'],end_date__gte = data['from_date'])

        company = CompanyDetails.objects.filter(id=data["company"]).first()
        company_name = company.company_name.replace(" ", "_")
        random_string = generate_random_string()
        data = LeavesHistory.objects.filter(
            q_filters
        ).annotate(
            employee_name = Concat(F('employee__first_name'), Value(' '), F('employee__middle_name'), Value(' '), F('employee__last_name')),
            status_name=Case(
                When(status=10, then=Value('APPROVED')),
                When(status=20, then=Value('PENDING')),
                When(status=30, then=Value('CANCELLED')),
                When(status=40, then=Value('REJECTED')),
                When(status=50, then=Value('REVOKED')),
                default=Value('PENDING')
            ),
            reporting_manager=F('employee__employee__manager__first_name')
        ).values(
            'employee__company__company_name', 'employee__work_details__employee_number',
            'employee_name', 'employee__work_details__department__name',
            'leave_rule__name', 'start_date', 'end_date', 'no_of_leaves_applied', 'status_name',
            'reporting_manager', 'created_at__date', 'approved_on__date', 'approved_by__user__username'
        )
        export_data = pd.DataFrame(data, columns=['employee__company__company_name', 'employee__work_details__employee_number',
            'employee_name', 'employee__work_details__department__name',
            'leave_rule__name', 'start_date', 'end_date', 'no_of_leaves_applied', 'status_name',
            'reporting_manager', 'created_at__date', 'approved_on__date', 'approved_by__user__username'])
        export_data.rename(columns={
            "employee__work_details__department__name": "department_name",
            "employee__work_details__employee_number": "employee_number",
            "employee__company__company_name": "company_name",
            "leave_rule__name": "leave_rule",
            "created_at__date": "leave_applied_at",
            "approved_on__date": "leave_approved_at",
            "approved_by__user__username": "approved_by"
        }, inplace=True)
        file_name = f"export_leave_history/{company_name}{random_string}.xlsx"
        return excel_converter(export_data,file_name)


# Export Of Attendance Logs
class ExportAttendanceAPIView(APIView):
    http_method_names = ["get"]
    model = CompanyDetails

    def get(self, request):
        params = self.request.GET
        filter_query = EmployeeCheckInOutDetails.objects.filter(
            employee_id__company_id=params.get("company"),
            date_of_checked_in__gte=params.get("from_date"),
            date_of_checked_in__lte=params.get("to_date"),
        )
        company = CompanyDetails.objects.filter(id=params.get("company")).first()
        company_name = company.company_name.replace(" ", "_")
        list_data = []
        random_string = generate_random_string()
        for filter_query in filter_query:
            convert = {}
            convert[
                "employee_number"
            ] = filter_query.employee.work_details.employee_number
            convert["department"] = filter_query.employee.work_details.department
            convert["location"] = filter_query.location
            convert["employee_name"] = filter_query.employee.name
            if rule_name := AssignedAttendanceRules.objects.filter(
                employee=filter_query.employee_id
            ).first():
                convert["attendance_shift"] = rule_name.attendance_rule.name
            convert["date"] = str(filter_query.date_of_checked_in)
            convert["status"] = filter_query.status
            convert["in_time"] = str(filter_query.latest_time_in)
            convert["out_time"] = str(filter_query.time_out)
            convert["work_duration"] = filter_query.work_duration
            convert["overtime_duration"] = filter_query.overtime_hours
            convert["break"] = filter_query.breaks
            convert["break_duration"] = filter_query.break_duration
            reporting_manager = EmployeeReportingManager.objects.filter(
                employee=filter_query.employee.id, is_deleted=False
            )
            for reporting in reporting_manager:
                convert["manager"] = reporting.manager
            if anamoly_history := AnamolyHistory.objects.filter(
                clock=filter_query.id
            ).count():
                convert["outstanding_anomalies"] = anamoly_history
            list_data.append(convert)
        export_data = pd.DataFrame(list_data)
        file_name = f"export_attendance_logs/{company_name}{random_string}.xlsx"
        return excel_converter(export_data,file_name)



class ExportLeaveHistoryBalanceAPIView(APIView):

    """
    Export Data Into Excel Leave History balance APIView

    Aslam 15-06-2023
    """

    model = EmployeeLeaveRuleRelation

    def add_data(self, emp_id):
        for l_typ in list(self.df.loc[self.df.employee__work_details__employee_number==emp_id].leave_rule__name):
            self.emp_df.loc[self.emp_df.employee__work_details__employee_number == emp_id, l_typ] = str(list(self.df.loc[self.df.employee__work_details__employee_number==emp_id].loc[self.df.leave_rule__name==l_typ, 'remaining_leaves'])[0]) + '/' +str(
                list(self.df.loc[self.df.employee__work_details__employee_number==emp_id].loc[self.df.leave_rule__name==l_typ, 'earned_leaves'])[0])
    def get(self, request, pk):
        params = request.query_params
        query_params = {
            'employee__company_id': pk,
            'employee__work_details__employee_status':'Active',
            'is_deleted':False
        }
        if 'rule_ids' in params:
            query_params["leave_rule__id__in"] = params.get('rule_ids')[0].split(',')
        if 'employee_id' in params:
            query_params["employee_id__in"] = params.get('employee_id').split(',')
        
        session_year = timezone_now().year
        query_params['session_year__session_year'] = params.get('session_year',session_year)
        random_string = generate_random_string()
        data = EmployeeLeaveRuleRelation.objects.filter(**query_params).select_related('employee', 'employee__work_details').values(
                'employee__work_details__employee_number', 'employee__user__username', 'leave_rule__name',
                'employee__work_details__department__name', 'employee__work_details__work_location', 'remaining_leaves','earned_leaves')
        self.df = pd.DataFrame(data, columns=['employee__work_details__employee_number', 'employee__user__username', 'leave_rule__name',
                'employee__work_details__department__name', 'employee__work_details__work_location', 'remaining_leaves','earned_leaves'])
        self.leave_df = self.df.leave_rule__name.drop_duplicates().reset_index(drop=True)
        self.emp_df = self.df[['employee__work_details__employee_number', 'employee__user__username', 'employee__work_details__department__name']].drop_duplicates().reset_index(drop=True)
        self.emp_df[list(self.leave_df)] = ['_' for _ in list(self.leave_df)]
        self.emp_df.employee__work_details__employee_number.apply(lambda x: self.add_data(x))
        self.emp_df = self.emp_df.rename(columns={'employee__work_details__employee_number':'Emp Id','employee__user__username':'Employee Name',
                                                  'employee__work_details__department__name':'Department'})
        if self.emp_df.empty:
            return Response(
                        error_response("No Data Found", "No Data Found", 404),
                        status=status.HTTP_404_NOT_FOUND
                    ) 
        file_name = f"export_leave_balance/{random_string}.xlsx"
        return excel_converter(self.emp_df,file_name)


class ImportLeaveHistoryBalanceAPIView(APIView):
    """
    Replace The Casual Remaining Leaves In AssignLeaveRuleRelation,
    Throw Import Excel APIView

    Aslam 15-06-2023
    """
    
    model = EmployeeLeaveRuleRelation

    def post(self, request):
        files = request.FILES['files']
        df =pd.read_excel(files, engine='openpyxl')

        for balance in df.values.tolist():
            relations = EmployeeLeaveRuleRelation.objects.filter(employee__first_name = balance[1])
            for relations in relations:
                if relations.employee.work_details.employee_number == balance[0] and relations.leave_rule.name == "Casual Leave":
                    relations.remaining_leaves = balance[2]
                    relations.save()
        return Response({"status": 200})
        
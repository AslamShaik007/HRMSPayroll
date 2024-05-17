from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from directory.models import EmployeeSalaryDetails #dont remove this thinking like not using, using with string model name getting
from django.apps import apps
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from core.utils import success_response, error_response, timezone
import traceback
from rest_framework import permissions, status
from payroll.models import PayrollInformation
from django.db import models as db_models
from attendance.models import EmployeeCheckInOutDetails
from django.contrib.postgres.aggregates import ArrayAgg, StringAgg



class QuckChangeDataApi(APIView):
    """
    this class is used to read and patch the data in various models
    """
    parser_classes = [JSONParser]
    
    app_data = {"EmployeeSalaryDetails":{'app':'directory', 'fields':{'account_holder_name', 'account_number', 'bank_name', 'branch_name', 'ifsc_code', 'account_type'}},
                        "EmployeeWorkDetails":{'app':'directory', 'fields':{'department__name', 'sub_department__name', 'designation__name'}},
                        "EmployeeAddressDetails":{'app':'directory', 'fields' : {'current_address_line1','current_address_line2', 'current_country', 'current_state', 'current_city', 'current_pincode', 'current_house_type', 'current_staying_since', 'living_in_current_city_since', 'permanent_address_line1', 'permanent_address_line2', 'permanent_country', 'permanent_state', 'permanent_city', 'permanent_pincode', 'permanent_same_as_current_address', 'other_house_type'}},        
                }
            
    def get(self, request):
        try:
            emp_email = request.data.get("emp_email", "")
            fetch_data = request.data.get("fetch_data","")
            for model_name in fetch_data:
                if model_name in list(self.app_data.keys()):
                    model = apps.get_model(self.app_data[model_name]['app'], model_name)
                    model_fields = self.app_data[model_name]['fields']
                    fetch_fields = fetch_data[model_name]
                    result = {fetch_field for fetch_field in fetch_fields if fetch_field  in model_fields}
                    if result:
                        fetched_data = model.objects.filter(employee__official_email=emp_email).values(*result) #need to do this filters also dynamically rather than employee id
                    else:
                        fetched_data = "keys are not present"
            return Response(
                success_response(msg="fetched the data", result=fetched_data)
            )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )

    def patch(self, request):
        try:
            emp_email = request.data.get("emp_email", "")
            patch_data= request.data.get("patch_data",  "")
            
            for model_name in patch_data:
                if model_name in list(self.app_data.keys()):
                    model = apps.get_model(self.app_data[model_name]['app'], model_name)
                    model_fields = self.app_data[model_name]['fields']
                    result = {key: value for key, value in patch_data[model_name].items() if key in model_fields}
                    updated_objs = model.objects.filter(employee__official_email=emp_email)
                    updated_objs.update(**result)
                    updated_objs_value = updated_objs.values(*list(result.keys()))
            return Response(
                success_response(msg="updated the data", result=updated_objs_value)
            )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )

class PayrollInfo(APIView):
    def get(self, request):
        try:
            q_filters = db_models.Q(is_processed=True)
            params = request.query_params
            if "month_years" in params:
                q_filters &= db_models.Q(month_year__in=request.query_params.getlist('month_years'))
            if "emp_emails" in params:
                q_filters &=  db_models.Q(employee__official_email__in=request.query_params.getlist('emp_emails'))
            payroll_qs = PayrollInformation.objects.filter(q_filters).values("employee_id", 'employee__official_email','employee__user__username', 'month_year')
            return Response(
                success_response(msg="payroll info data fetched", result=payroll_qs)
            )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )


class AttendanceInfo(APIView):
    """
    this class is used to get the attendance info for all emps b/w the dates for ai ml
    """
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        try:
            
            params = request.query_params
            from_date = params.get('from_date', timezone.now().date())
            to_date = params.get('to_date', timezone.now().date())

            q_filters = db_models.Q(employee__work_details__employee_status='Active', date_of_checked_in__range = [from_date, to_date])

            clock_qs = EmployeeCheckInOutDetails.objects.filter(q_filters).annotate(
                employee_code = StringAgg('employee__work_details__employee_number', delimiter=','),
                employee_name = StringAgg('employee__user__username', delimiter=', '),
                department = StringAgg('employee__work_details__department__name', delimiter=', '),
                designation = StringAgg('employee__work_details__designation__name', delimiter=', ')
                ).values('employee_code', 'employee_name', 'department', 'designation', 'date_of_checked_in', 'time_in', 'latest_time_in', 'time_out', 'work_duration', 'break_duration', 'breaks')
            return Response(clock_qs)

        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
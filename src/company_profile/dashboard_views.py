import traceback
from django.db import models as db_models
from django.contrib.postgres.aggregates import ArrayAgg
import pandas as pd

from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import (
    error_response,
    success_response,
    timezone_now,
    TimestampToIST, 
    TimestampToStrDateTime
)

from company_profile.models import Departments, SubDepartments, Announcements
from directory.models import EmployeeReportingManager, Employee
from core.custom_paginations import CustomPagePagination
from performance_management.models import AppraisalSendForm
from django.db.models import Max
from django.conf import settings
class AdminDepartmentsDetails(APIView):
    
    model = Departments
    def get(self, request, *args, **kwargs):

        try:
            role = request.user.employee_details.first().roles.values_list('name', flat=True).first()
            user_info = request.user.employee_details.first()
            company_id = user_info.company_id
            employee_id = user_info.id           
            q_filters = db_models.Q(is_deleted=False)
            if role == "ADMIN":   
                q_filters &= db_models.Q(company_id=company_id)
            if role == "MANAGER":
                emps_list = EmployeeReportingManager.objects.filter(manager_id = employee_id, is_deleted=False).values_list('employee',flat=True)
                q_filters &= db_models.Q(company__employees__id__in = emps_list)
            data = self.model.objects.filter(q_filters).prefetch_related('sub_departments').annotate(
                no_of_employees=db_models.Count('company__employees__id', filter=db_models.Q(
                    company__employees__is_deleted=False,company__employees__work_details__department_id=db_models.F('id'),company__employees__work_details__employee_status='Active'
                ), distinct=True)
            ).values('id', 'company', 'name', 'no_of_employees').order_by('id')
            
            return Response(
                    success_response(data, "Successfully fetched Depatrments data", 200),
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )

class AdminPendingEmployeeSignups(APIView):

    model = Employee
    def get(self, request, *args, **kwargs):

        try:
            user_info = request.user.employee_details.first()
            company_id = user_info.company_id
            employee_id = user_info.id
            role = request.user.employee_details.first().roles.values_list('name', flat=True).first()
            q_filters = db_models.Q(is_deleted=False)
            if role == "ADMIN":
                q_filters &= db_models.Q(company_id=company_id)
            if role == "MANAGER":
                emps_list = EmployeeReportingManager.objects.filter(manager_id = employee_id, is_deleted=False).values_list('employee',flat=True)
                q_filters &= db_models.Q(id__in = emps_list)
            emp_data = self.model.objects.filter(q_filters).aggregate(
                total_empcount = db_models.Count("id"),
                pending_signups = db_models.Count("id",filter=db_models.Q(is_sign_up=False),distinct=True),
                active_emp_count = db_models.Count("work_details",filter=db_models.Q(work_details__employee_status="Active"),distinct=True),
                inactive_emp_count = db_models.Count("work_details",filter=db_models.Q(work_details__employee_status="Inactive"),distinct=True),
                yettojoin_emp_count = db_models.Count("work_details",filter=db_models.Q(work_details__employee_status="YetToJoin"),distinct=True)
                )
            data = {
                "total_empcount":emp_data.get("total_empcount",0),
                "pending_signups":emp_data.get('pending_signups',0),
                "active_emp_count":emp_data.get('active_emp_count',0),
                "inactive_emp_count":emp_data.get('inactive_emp_count',0),
                "yettojoin_emp_count":emp_data.get('yettojoin_emp_count',0)
            }
            return Response(
                    success_response(data, "Successfully fetched pending Signup data", 200),
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
            
class EmployeeAnnouncementsView(APIView):
    
    permission_classes = [permissions.IsAuthenticated]
    model = Announcements
    def get(self,request):
        try:
            today = timezone_now().date()
            user_info = request.user.employee_details.first()
            company_id = user_info.company_id
            roles = user_info.roles.values_list('name', flat=True)
            q_filters = db_models.Q(company_id=company_id, is_deleted=False, expired_date__gte=timezone_now().date(), announcement_type='ANNOUNCEMENT')
            if 'EMPLOYEE' in roles:
                department_id = user_info.work_details.department_id
                q_filters &= (db_models.Q(departments__in=[department_id]) | db_models.Q(visibility='VISIBLE_TO_ALL'))
            query = Announcements.objects.filter(q_filters).annotate(
                        department = ArrayAgg('departments__id', filter = db_models.Q(departments__isnull = False)),
                        published_by = db_models.F('created_by__username'),
                        created_at_date = TimestampToStrDateTime(TimestampToIST(db_models.F('created_at'), settings.TIME_ZONE)),
                        updated_at_date = TimestampToStrDateTime(TimestampToIST(db_models.F('updated_at'), settings.TIME_ZONE))
                    ).values().order_by('expired_date')
            return Response(
                    success_response(query, "Successfully fetched Announcements data", 200),
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
class BestEmployyeDashboardView(APIView):
      permission_classes = [permissions.IsAuthenticated]
      model = AppraisalSendForm
      def get(self,request):
        try:
            today = timezone_now().date()
            department_id = request.query_params.get('department_id','')
            if not department_id:
                msg = 'Departement is mandatory'
                return Response(
                        error_response(msg,msg,400),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            q_filter = db_models.Q(employee__work_details__department_id=department_id, creation_date__month=today.month,
                                    creation_date__year=today.year,employee__work_details__employee_status='Active')
            score = AppraisalSendForm.objects.filter(q_filter).exclude(score=0.0).aggregate(max_score=Max('score'))['max_score']
            q_filter &= db_models.Q(score=score)
            employes = AppraisalSendForm.objects.filter(q_filter).annotate(
                emp_name = db_models.F('employee__user__username'),
                designation = db_models.F('employee__work_details__designation__name'),
                image = db_models.F('employee__employee_image')
            ).values('emp_name','designation','image')

            return Response(
                    success_response(employes, "Successfully fetched Best employee data", 200),
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )

class EmployeeTickerView(APIView):
    model = Announcements
    def get(self,request):
        try:
            today = timezone_now().date()
            user_info = request.user.employee_details.first()
            company_id = user_info.company_id
            roles = user_info.roles.values_list('name', flat=True)
            q_filters = db_models.Q(company_id=company_id, is_deleted=False, expired_date__gte=timezone_now().date(), announcement_type='TIKKER')
            if 'EMPLOYEE' in roles:
                department_id = user_info.work_details.department_id
                q_filters &= (db_models.Q(departments__in=[department_id]) | db_models.Q(visibility='VISIBLE_TO_ALL'))
            query = Announcements.objects.filter(q_filters).annotate(
                        department = ArrayAgg('departments__id', filter = db_models.Q(departments__isnull = False))
                    ).values().order_by('expired_date')
            return Response(
                    success_response(query, "Successfully fetched Ticker  data", 200),
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
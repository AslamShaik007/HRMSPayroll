import traceback
from django.db import models as db_models
from django.contrib.postgres.aggregates import ArrayAgg

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import success_response, error_response, timezone_now

from .models import EmployeeReportingManager, ManagerType, Employee
from datetime import timedelta, datetime

class EmployeeTeamDetailsView(APIView):
    model = EmployeeReportingManager
    
    def get(self,request):
        user_info = request.user.employee_details.first()
        emp_dep_id = user_info.work_details.department_id
        roles = user_info.roles.values_list('name',flat=True)
        q_filter = db_models.Q(is_deleted=False,id=user_info.id)
        query={}
        if 'EMPLOYEE' in roles:
            query = Employee.objects.filter(q_filter).annotate(
                        employees=ArrayAgg(db_models.expressions.Func(
                                    db_models.Value('emp_name'), 'employee__manager__employee_manager__employee__user__username',
                                    db_models.Value('designation'), 'employee__manager__employee_manager__employee__work_details__designation__name',
                                    db_models.Value('image'), 'employee__manager__employee_manager__employee__employee_image',
                                    function="jsonb_build_object",
                                    output_field=db_models.JSONField()    
                                    ), 
                                    filter=db_models.Q(employee__manager_type__manager_type=ManagerType.PRIMARY,
                                                       employee__manager__employee_manager__employee__work_details__department_id=emp_dep_id,
                                                       employee__manager__employee_manager__employee__work_details__employee_status='Active',
                                                       employee__manager__employee_manager__is_deleted=False
                                                       ), 
                                    distinct=True
                                    ),
                        manager_name = ArrayAgg(db_models.expressions.Func(
                                            db_models.Value('manager_name'), 'employee__manager__user__username',
                                            db_models.Value('designation'), 'employee__manager__work_details__designation__name',
                                            db_models.Value('image'), 'employee__manager__employee_image',
                                            function="jsonb_build_object",
                                            output_field=db_models.JSONField()    
                                            ), 
                                            filter=db_models.Q(employee__manager_type__manager_type=ManagerType.PRIMARY, employee__is_deleted=False), distinct=True),
            ).values('employees','manager_name')
            
        
        return Response(
                success_response(query, "Successfully Fetched Employees Data", 200),
                status=status.HTTP_200_OK
            )
class BirthdayBuddies(APIView):
    model = Employee

    def get(self, request):
        try:
            ''' 
            previous_days = datetime.strptime(request.query_params.get('from_date'), "%d/%m/%Y").date()
            end_date = datetime.strptime(request.query_params.get('to_date'), "%d/%m/%Y").date()
            q_filters = db_models.Q(
                                        is_deleted=False,
                                        work_details__employee_status='Active'
                                    )
            if previous_days == end_date:
                q_filters &= db_models.Q(date_of_birth__month=previous_days.month, date_of_birth__day=previous_days.day)
            elif previous_days.month == end_date.month:
                q_filters &= db_models.Q(date_of_birth__month=previous_days.month, date_of_birth__day__gte=previous_days.day, date_of_birth__day__lte=end_date.day)
            else:
                q_filters &= (
                                db_models.Q(date_of_birth__month=previous_days.month, date_of_birth__day__gte=previous_days.day) |
                                db_models.Q(date_of_birth__month=end_date.month, date_of_birth__day__lte=end_date.day) |
                                db_models.Q(date_of_birth__month__gt=previous_days.month, date_of_birth__month__lt=end_date.month)
                            )
            '''
            today = timezone_now().date()
            q_filters = db_models.Q(
                            is_deleted=False,
                            work_details__employee_status='Active',
                            date_of_birth__day__gte=today.day,
                            date_of_birth__month=today.month
                        )
            
            query = self.model.objects.filter(q_filters).values('id','user__username','employee_image','date_of_birth').order_by('date_of_birth__month','date_of_birth__day')
            return Response(
                    success_response(query, "successfully fetched birthday buddies", 200),
                    status=status.HTTP_200_OK               
                    )   
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
class ServiceYear(APIView):
    model = Employee

    def get(self, request):
        try:
            roles = request.user.employee_details.first().roles.values_list('name',flat=True).first()
            user_info = request.user.employee_details.first()
            employee_id = user_info.id
            q_filters = db_models.Q(date_of_join__month=timezone_now().date().month,
                                    date_of_join__year__lt=timezone_now().date().year,
                                    date_of_join__day__gte=timezone_now().date().day,
                                    is_deleted=False, work_details__employee_status='Active')
            if 'MANAGER' in roles:
                emp_ids = EmployeeReportingManager.objects.filter(manager_id=employee_id, is_deleted=False).values_list('employee_id', flat=True)
                q_filters &= db_models.Q(id__in=emp_ids)
            query = self.model.objects.filter(q_filters).values('id','user__username','employee_image','date_of_join').order_by('date_of_join__month','date_of_join__day')
            return Response(
                    success_response(query, "successfully fetched Service year buddies", 200),
                    status=status.HTTP_200_OK               
                    )

        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
class ManagerDepartments(APIView):
    model = EmployeeReportingManager
    
    def get(self, request, *args, **kwargs):
        user_info = request.user.employee_details.first()
        employee_id = user_info.id
        q_filter = db_models.Q(manager_id=employee_id,employee__work_details__department__isnull=False,employee__work_details__employee_status='Active',is_deleted=False)
        query = self.model.objects.filter(q_filter).annotate(
                        dep_name = db_models.F('employee__work_details__department__name'),
                        dep_id = db_models.F('employee__work_details__department_id')).values(
                            'dep_id','dep_name'
                        ).distinct('dep_id')
        return Response(
                success_response(query, "Successfully Fetched managers department Details", 200),
                status=status.HTTP_200_OK
            )
class OrganizationHierarchy(APIView):
    model = EmployeeReportingManager
    
    def get(self, request, *args, **kwargs):
        
        emp_id = request.user.employee_details.first().id
        my_list = []
        tag = True
        while tag:
            query = EmployeeReportingManager.objects.filter(employee_id=emp_id,manager_type__manager_type=10,
                                                            manager__work_details__employee_status='Active',
                                                            is_deleted=False
                                                        ).annotate(
                                                              image = db_models.F('employee__employee_image'),
                                                              designation = db_models.F('employee__work_details__designation__name'),
                                                              name = db_models.F('employee__user__username'),
                                                              bio = db_models.F('employee__bio')
                                                            ).values('image','designation','name','manager_id', 'bio','employee_id')
            if query.exists():
                my_list.append(query.first())
                emp_id = query.first().get('manager_id')
            else:
                query = EmployeeReportingManager.objects.filter(manager_id=emp_id,manager_type__manager_type=10,
                                                            manager__work_details__employee_status='Active',
                                                            is_deleted=False
                                                        ).annotate(
                                                              image = db_models.F('manager__employee_image'),
                                                              designation = db_models.F('manager__work_details__designation__name'),
                                                              name = db_models.F('manager__user__username'),
                                                              bio = db_models.F('manager__bio')
                                                            ).values('image','designation','name','manager_id','bio','employee_id')
                if query.exists():
                    my_list.append(query.first())
                break
        return Response(
                success_response(my_list, "Successfully Fetched Organization Hierarchy Details", 200),
                status=status.HTTP_200_OK
            )
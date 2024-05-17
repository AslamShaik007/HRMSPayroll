import traceback
from django.db import models as db_models


from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import (
    timezone_now,
    error_response,
    success_response,
    timezone_now
)

from performance_management.models import AppraisalSendForm
from directory.models import EmployeeReportingManager
from attendance.models import AttendanceRuleSettings
from datetime import datetime

class UserKraDetails(APIView):
    model = AppraisalSendForm
    
    def get(self,request):
        try:
            employee_id = request.user.employee_details.first().id
            current_date = timezone_now().date()
            q_filters = db_models.Q(employee_id=employee_id, manager_acknowledgement='COMPLETED', 
                                    creation_date__month=current_date.month, creation_date__year=current_date.year)
            print("q_filters:",q_filters)
            query = self.model.objects.filter(q_filters).annotate(
                name = db_models.F('employee__user__username'),
                image = db_models.F('employee__employee_image'),
            ).values('id','name','score','image')
            return Response(
                        success_response(query, "Successfully fetched Employee KRA data", 200),
                        status=status.HTTP_200_OK
                    )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
            

class AdminPendingKraDetails(APIView):
    model = AppraisalSendForm
    
    def get(self,request):
        try:
            
            roles = request.user.employee_details.first().roles.values_list('name',flat=True)
            user_info = request.user.employee_details.first()
            company_id = user_info.company
            employee_id = user_info.id
            q_filters = db_models.Q(manager_acknowledgement='PENDING',candidate_status='SUBMITTED',
                                    creation_date__month=timezone_now().month,creation_date__year=timezone_now().year)
            if 'ADMIN' in roles:
                q_filters &= db_models.Q(employee__company_id=company_id)
            if 'MANAGER' in roles:
                emp_ids = EmployeeReportingManager.objects.filter(manager_id = employee_id, is_deleted=False).values_list('employee_id',flat=True) 
                q_filters &= db_models.Q(employee_id__in=emp_ids)
                
            query = self.model.objects.filter(q_filters).count()
            data = {'pending_kra_count':query}
            return Response(
                        success_response(data, "Successfully fetched Employee KRA data", 200),
                        status=status.HTTP_200_OK
                    )
            
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
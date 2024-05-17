from datetime import datetime
import traceback

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q
from django.db import models as db_models

from pss_calendar.models import Events, Holidays
from core.utils import success_response, error_response



class CompanyHolidaysDashboardView(APIView):

    model = Holidays
    def get(self, request, *args, **kwargs):
        try:
            params = self.request.query_params
            if 'company_id' not in params:
                message = "company_id is required field"
                return Response(error_response(message,message, 400),status=status.HTTP_400_BAD_REQUEST)
            if 'start_date' not in params:
                message = "start_date is required field"
                return Response(error_response(message,message, 400),status=status.HTTP_400_BAD_REQUEST)
            if 'end_date' not in params:
                message = "end_date is required field"
                return Response(error_response(message,message, 400),status=status.HTTP_400_BAD_REQUEST) 
            
            company_id = params.get('company_id')
            start_date = datetime.strptime(params.get('start_date'), "%Y-%m-%d")    
            end_date = datetime.strptime(params.get('end_date'), "%Y-%m-%d") 
            
            q_filters = db_models.Q(company_id = company_id, is_deleted = False)
            q_filters &= db_models.Q(holiday_date__gte = start_date, holiday_date__lte = end_date)
            
            event_data = Holidays.objects.filter(q_filters).values().order_by('holiday_date')
            message = 'Holidays Data Fetched Successfully'
            response = success_response(event_data, message, 200)
            return Response(response,status=status.HTTP_200_OK)
        except Exception as e:
            response = error_response(f'{str(e)} Error: {traceback.format_exc()}', 400)
            return Response(response,status=status.HTTP_400_BAD_REQUEST)
    
class CompanyEventsDashboardView(APIView):
    model = Events
    def get(self, request, *args, **kwargs):
        try:
            params = self.request.query_params
            if 'company_id' not in params:
                message = "company_id is required field"
                return Response(error_response(message,message, 400),status=status.HTTP_400_BAD_REQUEST)
            if 'start_date' not in params:
                message = "start_date is required field"
                return Response(error_response(message,message, 400),status=status.HTTP_400_BAD_REQUEST)
            if 'end_date' not in params:
                message = "end_date is required field"
                return Response(error_response(message,message, 400),status=status.HTTP_400_BAD_REQUEST) 
             
            company_id = params.get('company_id')
            start_date = datetime.strptime(params.get('start_date'), "%Y-%m-%d")    
            end_date = datetime.strptime(params.get('end_date'), "%Y-%m-%d") 
            
            filter_1 = Q(
                company_id = company_id,
                is_deleted=False
            )
            filter_1 &= db_models.Q(start_date__lte = end_date, end_date__gte = start_date)
            role = self.request.user.employee_details.first().roles.first()
            filter_2 = filter_3 =Q()
            if (role and role.name.lower() == "employee"):
                filter_2 = Q(visibility = 'VISIBLE_TO_ALL')
                if self.request.user.employee_details.first().work_details.department_id:
                    filter_3 = Q(departments__in =  [self.request.user.employee_details.first().work_details.department_id]) 
            event_data = self.model.objects.filter(filter_1 & (filter_2 | filter_3)).annotate(
                department = ArrayAgg('departments__id', filter = Q(departments__isnull = False))
            ).values().order_by('-id')
            message = 'Events Data Fetched Successfully'
            response = success_response(event_data, message, 200)
            return Response(response,status=status.HTTP_200_OK)
        except Exception as e:
            response = error_response(f'{str(e)} Error: {traceback.format_exc()}', 400)
            return Response(response,status=status.HTTP_400_BAD_REQUEST)
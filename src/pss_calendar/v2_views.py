from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q
from django.db import models as db_models

from pss_calendar.models import Events, Holidays
from core.utils import success_response, error_response, timezone_now
import traceback
from core.custom_paginations import CustomPagePagination, LargeResultsSetPagination

class CompanyHolidaysRetrieveViewV2(APIView):

    model = Holidays
    pagination_class = LargeResultsSetPagination

    def get(self, request, *args, **kwargs):
        params = request.query_params
        current_year = timezone_now().year
        year = params.get("year",current_year)
        company_id = self.kwargs.get('company_id')
        paginator = self.pagination_class()
        if current_year < int(year):
            response = error_response("Holidays not found", 400)
            return Response(response,status=status.HTTP_400_BAD_REQUEST)
        q_filters= db_models.Q(company_id = company_id, is_deleted = False,holiday_date__year=year)
        holiday_data = Holidays.objects.filter(q_filters).values().order_by('holiday_date')
        message = 'Holidays Data Fetched Successfully'
        page = paginator.paginate_queryset(list(holiday_data), request)
        response = success_response(paginator.get_paginated_response(page), message, 200)
        return Response(response,status=status.HTTP_200_OK)
    
class CompanyEventsRetrieveViewV2(APIView):
    model = Events
    def get(self, request, *args, **kwargs):
        try:
            filter_1 = Q(
                company_id = self.kwargs.get('company_id'),
                is_deleted=False
            )
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
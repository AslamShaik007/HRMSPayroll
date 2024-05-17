import traceback
import datetime
import logging

from django.conf import settings
from django.db import transaction

import pandas as pd
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from core.smtp import send_email
from core.utils import email_render_to_string, timezone_now
from directory.models import Employee, EmployeeWorkDetails
from HRMSApp.models import CompanyDetails
from pss_calendar.models import Events, HolidayFile, Holidays
from pss_calendar.serializers import (
    CompanyEventDetailSerializer,
    CompanyEventSerializer,
    CompanyHolidaysDetailSerializer,
    CompanyHolidaysSerializer,
)
from HRMSApp.utils import Util
from core.utils import error_response, success_response,strftime
from core.whatsapp import WhatsappMessage
from alerts.utils import check_alert_notification

logger = logging.getLogger('django')
# Create your views here.


class CompanyHolidaysCreateView(CreateAPIView):
    """
    View to create Company Holidays

    SURESH, 03.02.2023
    """

    serializer_class = CompanyHolidaysSerializer
    detailed_serializer_class = CompanyHolidaysDetailSerializer
    queryset = Holidays.objects.all()


class CompanyHolidaysUpdateView(UpdateAPIView):
    """
    View to update Company Holidays

    SURESH, 03.02.2023
    """

    serializer_class = CompanyHolidaysSerializer
    detailed_serializer_class = CompanyHolidaysDetailSerializer
    lookup_field = "id"
    queryset = Holidays.objects.all()
    
    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            'request': self.request,
            'holiday_id': self.kwargs.get('id'),
            'view': self
        }


class CompanyHolidaysRetrieveView(ListAPIView):
    """
    View to retrieve Company Holidays

    SURESH, 03.02.2023
    """
    serializer_class = CompanyHolidaysDetailSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = Holidays.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)

class HolidaysImportView(APIView):
    
    model = HolidayFile

    # @transaction.atomic()
    def post(self, request):
        data = request.data.get("company")
        sid = transaction.set_autocommit(autocommit=False)
        name = request.FILES["holiday_file"]._name
        try:
            if name.split('.')[1].lower() not in ['xlsx', 'csv']:
                return Response(
                    {"data": {"status": "File Format is Incorrect"}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                    {"data": {"status": str(e)}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        holiday = HolidayFile.objects.create(
            holiday_upload_file=request.FILES["holiday_file"]
        )
        df = pd.read_excel(f"{settings.MEDIA_DIR}/{holiday.holiday_upload_file}")
        company = CompanyDetails.objects.get(id=data).id
        try:
            for record in df.values.tolist():
                today = timezone_now().date()
                if record[1] < today:
                    return Response(
                        {
                            "data": {"status": "Holidays Cannot Be Added For Past Dates"}
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                h_qs = Holidays.objects.filter(
                    holiday_name=record[0],
                    holiday_date=record[1],
                    is_deleted=False
                )
                if h_qs.exists():
                    transaction.rollback(sid)
                    return Response(
                        {
                            "data": {"status": f"Please check Holiday {record[0]} with Date {record[1].date().strftime('%d-%m-%Y')} is already exists"}
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if record[2] is True:
                    Holidays.objects.create(
                        holiday_name=record[0],
                        holiday_date=record[1],
                        holiday_type=True,
                        company_id=company,
                    )
                else:
                    Holidays.objects.create(
                        holiday_name=record[0],
                        holiday_date=record[1],
                        company_id=company,
                    )

        except Exception as e:
            transaction.rollback(sid)
            return Response(
                {"data": {"status": "File Format is Incorrect"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        transaction.commit()
        return Response(
            {"data": {"status": "Holiday created Succesfully"}},
            status=status.HTTP_201_CREATED,
        )


class CompanyEventsCreateView(CreateAPIView):
    """
    View to create Company Events
    """

    serializer_class = CompanyEventSerializer

    def post(self,request):
        try:
            transaction.set_autocommit(autocommit=False)
            request_data = request.data
            event_title = request_data.get('event_title')
            description = request_data.get('event_description')
            start_date = request_data.get('start_date')
            start_time = request_data.get('start_time')
            end_date = request_data.get('end_date')
            end_time = request_data.get('end_time')
            departments = request_data.get("department",'')
            visibility = request_data.get('visibility')
            domain = f"{self.request.scheme}://{self.request.get_host()}/"
            
            serializer = self.get_serializer(data=request_data)
            if serializer.is_valid() :
                self.perform_create(serializer)
            else:
                Error  = ''
                for index, error in enumerate(serializer.errors):
                    Error  += str(serializer.errors.get(error)).split("[ErrorDetail(string='")[1].split("', code=")[0]
                response = error_response(Error,'something went wrong', 400)
                return Response(response, status=status.HTTP_400_BAD_REQUEST)
            if departments:
                serializer.instance.departments.add(*(departments))
            massage = "Event created,message hase been sent to employees"
            
            # Sending mails to all the users with respect to the departments
            filters = {'is_deleted':False,'employee_status' : 'Active'}
            if visibility == 'LIMITED_VISIBILITY':
                filters['department__in'] =  departments
            for record in EmployeeWorkDetails.objects.filter(employee_status='Active').prefetch_related('employee','employee__company').filter(**filters):
                emp_code = record.employee_number
                # body=f'Hello {record.employee.first_name} [{emp_code}],\n\nEvent Title: {event_title},\nEvent Start Date: {start_date} Time: {start_time},\nEvent End Date: {end_date} Time: {end_time}\nEvent Description: {description}\n\nJust a quick reminder that your invitation.\nDont miss out - come and join your team,\n\nPlease refer the link for more information {domain}holiday\n\nThanks & Regards,\n{record.employee.company.company_name}'  
                event_start_time = datetime.datetime.strptime(start_time, "%H:%M").strftime("%I:%M %p")
                event_end_time = datetime.datetime.strptime(end_time, "%H:%M").strftime("%I:%M %p")
                body=f'''
    Hello {record.employee.first_name} [{emp_code}],
    
    Event Title: {event_title},
    Event Start Date: {start_date} Time: {event_start_time},
    Event End Date: {end_date} Time: {event_end_time},
    Event Description: {description},
    
    Just a quick reminder that your invitation,
    Dont miss out - come and join your team,
    
    Please refer the link for more information {domain}holiday,
    
    Thanks & Regards,
    {record.employee.company.company_name}.
    '''
                
                data={
                    'subject':'New event added by admin',
                    'body':body,
                    'to_email':record.employee.official_email
                }
                if check_alert_notification("Calender",'Add Event', email=True):
                    Util.send_email(data)
                
                # employee Whatsapp notifications
                try:
                    domain = f"{self.request.scheme}://{self.request.get_host()}/"
                    whatsapp_data = {
                            'phone_number': record.employee.user.phone,
                            'subject': 'New event added by admin',
                            "body_text1":f"{event_title} is added, Just a quick reminder that your invitation",
                            'body_text2': "Dont miss out - come and join your team,",
                            'url': f"{domain}holiday",
                            "company_name":record.employee.company.company_name.title()
                            }
                    if check_alert_notification("Calender",'Add Event', whatsapp=True):
                        WhatsappMessage.whatsapp_message(whatsapp_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to {record.employee.user.username} in event create: {e}") 
        except Exception as e:
            response = error_response(f'{str(e)} Error: {traceback.format_exc()}', 400)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        
        response = success_response(serializer.data, massage, 200)
        transaction.commit()
        return Response(response,status=status.HTTP_201_CREATED)




class CompanyEventsUpdateView(UpdateAPIView):
    """
    View to update Company Events
    """
    serializer_class = CompanyEventSerializer
    
    def update(self, request, *args, **kwargs):
        try:

            request_data = self.request.data
            event_title = request_data.get('event_title')
            description = request_data.get('event_description')
            start_date = request_data.get('start_date')
            start_time = request_data.get('start_time')
            end_date = request_data.get('end_date')
            end_time = request_data.get('end_time')
            visibility = request_data.get('visibility')
            departments = request_data.get("department",'')
            event_id = self.kwargs.get('id')
            domain = f"{self.request.scheme}://{self.request.get_host()}/"
            
            instance = Events.objects.get(id = event_id)
            if datetime.datetime.combine( instance.start_date, instance.start_time) < datetime.datetime.now():
                return Response(
                    error_response("",'Event Already started Cant be Edit or deleted', 400),
                    status=status.HTTP_400_BAD_REQUEST
                )
            if 'is_deleted' in request_data:
                instance.is_deleted = True
                instance.save()
                response = success_response('', 'Event deleted successfully', 200)
                return Response(response, status=status.HTTP_200_OK)  
            serializer = self.get_serializer(instance, request_data,context={'event_id':event_id},partial=True)
            if departments:
                instance.departments.clear()
                serializer.instance.departments.add(*(departments))
            if serializer.is_valid() :
                self.perform_update(serializer)
            else:
                Error  = ''
                for index, error in enumerate(serializer.errors):
                    Error  += str(serializer.errors.get(error)).split("[ErrorDetail(string='")[1].split("', code=")[0]
                response = error_response('something went wrong',Error, 400)
                return Response(response, status=status.HTTP_400_BAD_REQUEST)
            

            filters = {'is_deleted':False,'employee_status' : 'Active'}
            if visibility == 'LIMITED_VISIBILITY':
                filters['department__in'] =  departments
            for record in EmployeeWorkDetails.objects.filter(employee_status='Active').prefetch_related('employee','employee__company').filter(**filters):
                emp_code = record.employee_number
                # body=f'Hello {record.employee.first_name} [{emp_code}],\n\nEvent Title: {event_title},\nEvent Start Date: {start_date} Time: {start_time},\nEvent End Date: {end_date} Time: {end_time}\nEvent Description: {description}\n\nJust a quick reminder that your invitation.\nDont miss out - come and join your team,\n\nPlease refer the link for more information {domain}holiday\n\nThanks & Regards,\n{record.employee.company.company_name}'  
                event_start_time = datetime.datetime.strptime(start_time, "%H:%M").strftime("%I:%M %p")
                event_end_time = datetime.datetime.strptime(end_time, "%H:%M").strftime("%I:%M %p")
                body=f'''
    Hello {record.employee.first_name} [{emp_code}],
    
    Event Title: {event_title},
    Event Start Date: {start_date} Time: {event_start_time},
    Event End Date: {end_date} Time: {event_end_time},
    Event Description: {description},
    
    Just a quick reminder that your invitation,
    Dont miss out - come and join your team,
    
    Please refer the link for more information {domain}holiday,
    
    Thanks & Regards,
    {record.employee.company.company_name}.
    '''
                
                data={
                    'subject':'Event updated by admin',
                    'body':body,
                    'to_email':record.employee.official_email
                }
                if check_alert_notification("Calender",'Update Event', email=True):
                    Util.send_email(data)
                
                # employee Whatsapp notifications
                try:
                    whatsapp_data = {
                            'phone_number': record.employee.user.phone,
                            'subject': 'Event updated by admin',
                            "body_text1":f"{event_title} is updated, Just a quick reminder that your invitation",
                            'body_text2': "Dont miss out - come and join your team,",
                            'url': f"{domain}holiday",
                            "company_name":record.employee.company.company_name.title()
                            }
                    if check_alert_notification("Calender",'Update Event', whatsapp=True):
                        WhatsappMessage.whatsapp_message(whatsapp_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to {record.employee.user.username} in event create: {e}") 
                    
            message =  "Event updated successfully"
            response = success_response(serializer.data, message, 200)
            return Response(response, status=status.HTTP_200_OK)

        except Exception as e:
            response = error_response(f'{str(e)} Error: {traceback.format_exc()}', 400)
            return Response(response, status=status.HTTP_200_OK)

class CompanyEventsRetrieveView(ListAPIView):
    """
    View to retrieve Company Events

    SURESH, 03.02.2023
    """

    serializer_class = CompanyEventDetailSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = Events.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        if self.request.user.employee_details.first().roles.first().name.lower() == "employee":
            try:
                filter_kwargs['department_id'] = self.request.user.employee_details.first().work_details.department_id
            except Exception:
                filter_kwargs['department_id'] = 0
        return queryset.filter(**filter_kwargs)

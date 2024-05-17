import traceback
from datetime import date, timedelta,datetime, time
import datetime as dt
from dateutil.parser import parse
from HRMSApp.utils import Util
from core.whatsapp import WhatsappMessage

from django.db.models import Exists, OuterRef, Q, F, Value, ExpressionWrapper, Func, DurationField, Subquery
from django.db.models.functions import Concat
from django.utils.html import format_html
from django.conf import settings

from rest_framework import permissions, status
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    RetrieveUpdateAPIView,
    UpdateAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from uritemplate import partial

from attendance import serializers as dir_serializers
from attendance.models import (
    AnamolyHistory,
    AssignedAttendanceRules,
    AttendanceRules,
    AttendanceRuleSettings,
    EmployeeCheckInOutDetails, EmployeeMonthlyAttendanceRecords, ConsolidateNotificationDates, KeyloggerAttendanceLogs, ConsolidateButton
)
from leave.models import EmployeeWorkRuleRelation, LeavesHistory
from attendance.serializers import (
    AssignedAttendanceRulesDetailsSerializer,
    AssignedAttendanceRulesSerializer,
    AttendanceRuleSettingsDetailsSerializer,
    AttendanceRuleSettingsSerializer,
    AttendanceRulesSerializer,
    CheckInOutDetailSerializer,
    CheckInOutSerializer,
    EmployeeAttendaceRuleRelationSerializer,
    EmployeeAttendanceRuleBulkSerializer,
    KeyloggerAttendanceLogsSerializer,
)
from attendance.services import calculate_break_time, calculate_work_time, get_monthly_record_obj_month, fetch_attendace_rule_start_end_dates
from core.smtp import send_email
from core.utils import (
    b64_to_image,
    email_render_to_string,
    get_formatted_time,
    get_ip_address,
    strptime,
    timezone_now,
    success_response,
    error_response,
    mins_to_hrs,
    localize_dt,
    get_paycycle_dates,
    search_filter_decode,
    hrs_to_mins

)
from core.views import AbstractListAPIView, AbstractRetrieveUpdateAPIView
from directory.models import Employee, EmployeeReportingManager, ManagerType, EmployeeWorkDetails
from directory.serializers import EmployeeDetailSerializer
from leave import models as leave_models
from core.utils import get_month_weeks, TimestampToIST, TimestampToStrDateTime
from leave.services import is_day_type
import logging
import pandas as pd
from core.utils import excel_converter
logger = logging.getLogger("django")
from core.custom_paginations import CustomPagePagination
from django.db import models
from HRMSProject.multitenant_setup import MultitenantSetup
from alerts.utils import check_alert_notification
import subprocess, os
# Create your views here.
class AttendanceCreateAPIView(CreateAPIView):
    """
    View to create attendance

    SURESH 24-02-2023
    """
    model = AttendanceRules
    serializer_class = dir_serializers.AttendanceRulesSerializer
    
class AttendanceRetrieveUpdateView(RetrieveUpdateAPIView):
    """
    View to Retrieve Update

    SURESH 24-02-2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = dir_serializers.AttendanceRulesSerializer
    lookup_field = "id"
    queryset = AttendanceRules.objects.all()


class AttendanceRulesRetriveView(ListAPIView):
    """
    Attendance Rule Retriew view

    Aslam 24-02-2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttendanceRulesSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = AttendanceRules.objects.all()

    def filter_queryset(self, queryset):
        filter_queryset = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_queryset)


class AssignedAttendanceRulesCreateView(CreateAPIView):
    """
    Assigning Attendance Create Api View

    SURESH 24-02-2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = AssignedAttendanceRulesSerializer
    detailed_serializer_class = AssignedAttendanceRulesDetailsSerializer
    queryset = AssignedAttendanceRules.objects.all()


class EmployeeAttendanceRuleBulkAPIView(APIView):
    """
    Bulk Assign Attendance and Bulk Update API

    """
    model = AssignedAttendanceRules
    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeAttendanceRuleBulkSerializer
    detailed_serializer_class = EmployeeAttendaceRuleRelationSerializer
    lookup_field = "company"

    def get_queryset(self):
        return Employee.objects.filter(
            company=self.kwargs[self.lookup_field], is_deleted=False
        )

    def _perform_create(self, request, *args, **kwargs):
        """
        performs update or save
        :param request: The request object

        SURESH, 02.03.2023
        """
        context = {"logged_in_user" : self.request.user.username,
                   "domain": f"{self.request.scheme}://{self.request.get_host()}/"}
        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        if kwargs.pop("partial", False):
            serializer.update(None, validated_data=serializer.validated_data)
        else:
            serializer.save()

    def _retrieve(self, *args, **kwargs):
        """
        > The function retrieves all the objects in the database and returns them in a serialized format
        :return: The serializer.data is being returned.

        SURESH, 02.03.2023
        """

        serializer = self.detailed_serializer_class(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """
        SURESH, 02.03.2023
        """
        self._perform_create(request)
        return self._retrieve()

    def get(self, request, *args, **kwargs):
        """
        Retrieve Company's employee work rules

        SURESH, 02.03.2023
        """
        return self._retrieve()

    def patch(self, request, *args, **kwargs):
        """
        Override default patch method

        SURESH, 02.03.2023
        """
        self._perform_create(request, partial=partial)
        return self._retrieve()


class EmployeeAttendanceRuleRelationRetrieveView(AbstractListAPIView):
    """
    Retrieve company_employee attandance rule
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeAttendaceRuleRelationSerializer
    lookup_field = "company_id"
    model = Employee

    def get_queryset(self):
        return Employee.objects.filter(
            company=self.kwargs[self.lookup_field], is_deleted=False
        )


class EmpAttendanceRuleRetrieveView(AbstractListAPIView):
    """
    Retrieve employee attandance rule
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = AssignedAttendanceRulesDetailsSerializer
    lookup_field = "employee"
    lookup_url_kwarg = "employee_id"
    queryset = AssignedAttendanceRules.objects.all()

    def filter_queryset(self, queryset):
        filter_queryset = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_queryset)


class AttendanceRuleSettingsRetrieveView(ListAPIView):
    """
    Attendance Setting List Api View

    Aslam 24-02-2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttendanceRuleSettingsDetailsSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = AttendanceRuleSettings.objects.all()

    def filter_queryset(self, queryset):
        """
        Filtering Given Company Id And Checking Is Deleted (Flase)
        If It Is False, Getting Data According To Given Company_id

        Aslam 24-02-2023
        """
        filter_queryset = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_queryset)


class AttendanceRuleSettingsUpdateView(UpdateAPIView):
    """
    Attendance Setting Update Api View

    Aslam 24-02-2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttendanceRuleSettingsSerializer
    detailed_serializer_class = AttendanceRuleSettingsDetailsSerializer
    lookup_field = "id"
    queryset = AttendanceRuleSettings.objects.all()
    
    def patch(self, request, *args, **kwargs):
        company = request.user.employee_details.first().company
        if company.employees.filter(emp_payroll_info__isnull=False,
                        emp_payroll_info__month_year__year=timezone_now().year).exists():
            return Response(error_response("Cant Update Payroll settings in this year",
                                        "Cant Update Payroll settings in this year", 400), status=status.HTTP_400_BAD_REQUEST)
        return super().patch(request, *args, **kwargs)


class EmployeeCheckInOutDetailsRetriveView(ListAPIView):
    """
    Employee Checkin Chockout Retriew view

    Aslam 16-03-2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CheckInOutSerializer
    lookup_field = "employee"
    lookup_url_kwarg = "employee_id"
    queryset = EmployeeCheckInOutDetails.objects.all()

    def filter_queryset(self, queryset):
        filter_queryset = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_queryset)


class EmployeeCheckInView(APIView):
    """
    Employee Check-in Update Api View

    SURESH 16-03-2023
    AJAY, 20.03.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    allowed_methods = ["post"]
    model = EmployeeCheckInOutDetails

    def get_object(self, validated_data, today, **kwargs):
        qs = EmployeeCheckInOutDetails.objects.filter(
            employee_id=validated_data["employee"], date_of_checked_in=today.date()
        )

        return (
            qs.first()
            if qs.exists()
            else EmployeeCheckInOutDetails.objects.get_or_create(
                employee_id=validated_data["employee"],
                date_of_checked_in=today.date(),
            )[0]
        )

    def post(self, request, *args, **kwargs):
        data = request.data
        rules = AssignedAttendanceRules.objects.filter(
            employee=data.get("employee", None)
        )
        if not rules.exists():
            return Response(
                data={"error": "Employee is not assigned to any attendance rule"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Handling Check In locations
        query = self.model.objects.filter(employee_id=data.get("employee"), date_of_checked_in=timezone_now().date())
        
        check_in_obj = EmployeeCheckInOutDetails.objects.filter(employee_id=data.get("employee"))
        latest_check_in_location = "Work From Office" 
        if not query.exists() and check_in_obj.exists():
            latest_check_in_location = check_in_obj.last().checkin_location if check_in_obj.last().checkin_location else "Work From Office" 
        w_l = query.first().checkin_location if query.exists() else latest_check_in_location
        work_location = data.get('checkin_location',w_l)
        status_update = data.get('status_update',False)
        if status_update and query.exists():
            punch_history = query.first().extra_data['punch_history']
            last_record = punch_history.pop()
            last_record['checkin_location'] = work_location
            punch_history.extend([last_record])
            query.update(extra_data = {"punch_history":punch_history}, checkin_location=work_location)
            return Response(
                success_response([],'CheckIn Location Updated Successfully'),
                status=status.HTTP_200_OK
            )
        rule = rules.first().attendance_rule
        sel_tz = settings.TIME_ZONE
        if rule.selected_time_zone:
            sel_tz = rule.selected_time_zone
        emp_obj = Employee.objects.get(id=data.get("employee", None))
        if emp_obj.leaveshistory_set.filter(
            status=10, start_date__lte = timezone_now(tz=sel_tz).date(),
            end_date__gte = timezone_now(tz=sel_tz).date(), 
        ).exclude((Q(start_day_session__isnull=False) | Q(end_day_session__isnull=False))).exists():
            return Response(
                data={"error":"Leave already approved on today date"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if emp_obj.date_of_join is None:
            return Response(
                data={"error": "Employee Dosen't Have Date of Join"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if emp_obj.date_of_join > timezone_now(tz=sel_tz).date():
            return Response(
                data={"error": "Employee Cant Check In Before Date of JOIN"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        
        if not rules.exists():
            return Response(
                data={"error": "Employee is not assigned to any attendance rule"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        work_rule = EmployeeWorkRuleRelation.objects.filter(
            employee=data.get("employee", None)
        )
        if not work_rule.exists():
            return Response(
                data={"error": "Employee is not assigned to any work rule"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # att_rule=rules[0]
        # print(att_rule.attendance_rule.enable_geo_fencing)
        # if att_rule.attendance_rule.enable_geo_fencing:
        #     location = AttendanceRules.objects.filter(
        #         longitude = data["longitude"],
        #         latitude = data["latitude"],
        #     )
        #     if not location.exists():
        #         return Response(
        #         data={"error": "Please check your login location"},
        #         status=status.HTTP_404_NOT_FOUND,
        #     )
        today = timezone_now(tz=sel_tz)
        instance = self.get_object(data, today)
        instance.checkin_location = work_location
        instance.is_logged_out = False
        image_data = data.get("employee_image", None)
        if image_data:
            instance.employee_selfie = b64_to_image(
                image_data=image_data,
                file_name=instance.employee.name,
                use_ctime_as_prefix=True,
            )
            instance.employee_selfie_binary = format_html(
                '<img src="data:;base64,{}">', image_data
            )

        # * Calculate break time
        if instance.time_in is None:
            # ? First time check in
            instance.time_in = today
            instance.breaks = 0
        elif instance.time_out:
            calculate_break_time(instance, today)

        instance.latest_time_in = today
        history = instance.extra_data.get("punch_history", [])
        history.append(
            {
                "time": get_formatted_time(today, tz=sel_tz),
                "type": "Clock In",
                "ip_address": get_ip_address(request),
                "checkin_location": work_location
            }
        )
        instance.extra_data["punch_history"] = history
        instance.save()
        result = {
            "status": "P",
            "time_in": get_formatted_time(instance.time_in, tz=sel_tz),
            "time_out": get_formatted_time(instance.time_out, tz=sel_tz)
            if instance.time_out
            else "-",
            "punch_history": history,
            # "time_out_history": instance.extra_data.get("time_out_history", []),
            "work_duration": instance.work_duration or "-",
            "break_duration": instance.break_duration or "-",
            "breaks": instance.breaks,
            "employee_selfie": instance.employee_selfie.url
            if instance.employee_selfie
            else "-",
            "employee_selfie_binay": instance.employee_selfie_binary,
            "checkin_location": work_location
        }
        # attendance_rule = rules.first().attendance_rule
        # attendance_start_day, attendace_end_day = fetch_attendace_rule_start_end_dates(instance.employee.company_id)
        # check_month = get_monthly_record_obj_month(attendance_start_day, attendace_end_day, instance.date_of_checked_in)
        # month_record_obj, is_created = EmployeeMonthlyAttendanceRecords.objects.get_or_create(
        #     employee_id=emp_obj.id, year=instance.date_of_checked_in.year, month=check_month
        # )
        # p_count = 0
        # if str(instance.date_of_checked_in) not in month_record_obj.attendance_data.keys() and not (
        #         attendance_rule.enable_anomaly_tracing or attendance_rule.auto_deduction or attendance_rule.enable_over_time or attendance_rule.enable_comp_off
        #     ):
        #     month_record_obj.present_days += 1.0
        #     p_count = 1
        # else:
        #     p_count = month_record_obj.attendance_data.get(str(instance.date_of_checked_in), {}).get('present_count', 0)
        # month_record_obj.attendance_data[str(instance.date_of_checked_in)] = {
        #     'breaks': instance.breaks,
        #     'reason': '',
        #     'status': 'P' if not (
        #         attendance_rule.enable_anomaly_tracing or attendance_rule.auto_deduction or attendance_rule.enable_over_time or attendance_rule.enable_comp_off
        #     ) else 'A',
        #     'time_in': dt.datetime.strftime(localize_dt(dt=instance.time_in, tz=sel_tz), "%Y-%m-%d %I:%M %p"),
        #     'time_out': dt.datetime.strftime(localize_dt(dt=instance.time_out, tz=sel_tz), "%Y-%m-%d %I:%M %p") if instance.time_out else None,
        #     'anamolies': {'count': 0},
        #     'present_count': p_count,
        #     'work_duration': instance.work_duration,
        #     'break_duration': instance.break_duration,
        #     'over_time_data': mins_to_hrs(instance.overtime_hours) ,
        #     'approval_status': ''
        # }
        # month_record_obj.save()
                        
        try:
            company_name = instance.employee.company.company_name
            emp_name = instance.employee.user.username
            emp_email = instance.employee.official_email
            emp_number = instance.employee.work_details.employee_number
            # gender = instance.employee.gender
            tag = emp_number if emp_number else "-"
            today = timezone_now()
            domain = f"{self.request.scheme}://{self.request.get_host()}/"
            subject = f"Successfully checked In on HRMS for the date {today.strftime('%d-%m-%Y')}"
            body=f'''
    Hello {emp_name.title()} [{tag}],
    
    This is to inform you that you have successfully checked In on HRMS for the date {today.strftime('%d-%m-%Y %I:%M %p')}.
    
    Please refer the link for more information {domain}userAttendancelogs
    
    Thanks & Regards,    
    {company_name.title()}
    
    '''
            data={  
                'subject':subject,
                'body':body,
                'to_email':emp_email
            }
            if check_alert_notification("Attendance",'Check In', email=True):
                Util.send_email(data)
        except Exception as e:
            logger.warning(f"Error while sending email notificaton : {e}")
        
        # Employee Whatsapp notifications
        try:
            whatsapp_data = {
                            'phone_number': instance.employee.user.phone,
                            'subject': 'Checked In',
                            "body_text1":f"You have successfully checked in for the date {today.strftime('%d-%m-%Y %I:%M %p')}",
                            'body_text2': ' ',
                            'url': f"{domain}userAttendancelogs",
                            "company_name":instance.employee.company.company_name.title()
                            }
            if check_alert_notification("Attendance",'Check In', whatsapp=True):
                WhatsappMessage.whatsapp_message(whatsapp_data)
        except Exception as e:
            logger.warning(f"Error while sending Whatsapp notificaton to {instance.employee.user.username} in notifications about check in: {e}")   
        return Response(result, status=status.HTTP_200_OK)



class EmployeeCheckOutView(APIView):
    """
    Employee Check-Out Update Api View

    AJAY, 20.03.2023
    """

    allowed_methods = ["post"]
    model = EmployeeCheckInOutDetails

    def get_object(self, validated_data, today, **kwargs):
        qs = EmployeeCheckInOutDetails.objects.filter(
            employee__id=validated_data["employee"]
        ).order_by('date_of_checked_in')
        print(qs)
        return qs.last()

    def post(self, request, *args, **kwargs):
        data = request.data
        rules = AssignedAttendanceRules.objects.filter(
            employee=data.get("employee", None)
        )
        if not rules.exists():
            return Response(
                data={"error": "Employee is not assigned to any attendance rule"},
                status=status.HTTP_404_NOT_FOUND,
            )
        attendance_rule = rules.first().attendance_rule
        work_rule = EmployeeWorkRuleRelation.objects.filter(
            employee=data.get("employee", None)
        )
        if not work_rule.exists():
            return Response(
                data={"error": "Employee is not assigned to any work rule"},
                status=status.HTTP_404_NOT_FOUND,
            )
        # att_rule=rules[0]
        # if att_rule.attendance_rule.enable_geo_fencing:
        #     location = AttendanceRules.objects.filter(
        #         longitude = data["longitude"],
        #         latitude = data["latitude"],
        #     )
        #     if not location.exists():
        #         return Response(
        #         data={"error": "Please check your login location"},
        #         status=status.HTTP_404_NOT_FOUND,
        #     )
        sel_tz = settings.TIME_ZONE
        if attendance_rule.selected_time_zone:
            sel_tz = attendance_rule.selected_time_zone
        today = timezone_now(tz=attendance_rule.selected_time_zone)
        instance = self.get_object(data, today)
        instance.is_logged_out = True
        # * Calculate work time
        calculate_work_time(instance, today)

        history = instance.extra_data.get("punch_history", [])
        history.append(
            {
                "time": get_formatted_time(today,tz=sel_tz),
                "type": "Clock Out",
                "ip_address": get_ip_address(request),
            }
        )
        instance.extra_data["punch_history"] = history
        instance.save()

        result = {
            "status": "P",
            "in_time": get_formatted_time(instance.time_in,tz=sel_tz),
            "out_time": get_formatted_time(instance.time_out,tz=sel_tz),
            "punch_history": history,
            "work_duration": instance.work_duration or "-",
            "break_duration": instance.break_duration or "-",
            "breaks": instance.breaks,
            "employee_selfie": instance.employee_selfie.url
            if instance.employee_selfie
            else "-",
            "employee_selfie_binay": instance.employee_selfie_binary,
        }
        
        # attendance_start_day, attendace_end_day = fetch_attendace_rule_start_end_dates(instance.employee.company_id)
        # check_month = get_monthly_record_obj_month(attendance_start_day, attendace_end_day, instance.date_of_checked_in)
        # month_record_obj, is_created = EmployeeMonthlyAttendanceRecords.objects.get_or_create(
        #     employee_id=instance.employee.id, year=instance.date_of_checked_in.year, month=check_month
        # )
        # p_count = 0
        # if str(instance.date_of_checked_in) not in month_record_obj.attendance_data.keys() and not (
        #         attendance_rule.enable_anomaly_tracing or attendance_rule.auto_deduction or attendance_rule.enable_over_time or attendance_rule.enable_comp_off
        #     ):
        #     month_record_obj.present_days += 1.0
        #     p_count = 1
        # else:
        #     try:
        #         p_count = month_record_obj.attendance_data[str(instance.date_of_checked_in)]['present_count']
        #     except:
        #         pass
        
        # month_record_obj.attendance_data[str(instance.date_of_checked_in)] = {
        #     'breaks': instance.breaks,
        #     'reason': '',
        #     'status': 'P' if not (
        #         attendance_rule.enable_anomaly_tracing or attendance_rule.auto_deduction or attendance_rule.enable_over_time or attendance_rule.enable_comp_off
        #     ) else 'A',
        #     'time_in': dt.datetime.strftime(localize_dt(dt=instance.time_in, tz=sel_tz), "%Y-%m-%d %I:%M %p"),
        #     'time_out': dt.datetime.strftime(localize_dt(dt=instance.time_out, tz=sel_tz), "%Y-%m-%d %I:%M %p") if instance.time_out else None,
        #     'anamolies': {'count': 0},
        #     'present_count': p_count,
        #     'work_duration': instance.work_duration,
        #     'break_duration': instance.break_duration,
        #     'over_time_data': mins_to_hrs(instance.overtime_hours),
        #     'approval_status': ''
        # }
        # month_record_obj.save()
        
        try:
            company_name = instance.employee.company.company_name
            emp_name = instance.employee.user.username
            emp_email = instance.employee.official_email
            emp_number = instance.employee.work_details.employee_number
            # gender = instance.employee.gender
            tag = emp_number if emp_number else "-"
            today = timezone_now()
            domain = f"{self.request.scheme}://{self.request.get_host()}/"
            subject = f"Successfully checked out from the HRMS for the date {today.strftime('%d-%m-%Y')}"
            body=f'''
    Hello {emp_name.title()} [{tag}],
    
    This is to inform you that you have successfully checkout from the HRMS for the date {today.strftime('%d-%m-%Y %I:%M %p')}.
    
    Please refer the link for more information {domain}userAttendancelogs
    
    Thanks & Regards,
    {company_name.title()}
    
    '''
            data={
                'subject':subject,
                'body':body,
                'to_email':emp_email
            }
            if check_alert_notification("Attendance",'Check Out', email=True):
                Util.send_email(data)
        except Exception as e:
            logger.warning(f"Error while sending email notificaton : {e}")
            
        # Employee Whatsapp notifications
        try:
            whatsapp_data = {
                            'phone_number': instance.employee.user.phone,
                            'subject': 'Checked Out',
                            "body_text1":f"You have successfully checked Out for the date {today.strftime('%d-%m-%Y %I:%M %p')}",
                            'body_text2': ' ',
                            'url': f"{domain}userAttendancelogs",
                            "company_name":instance.employee.company.company_name.title()
                            }
            if check_alert_notification("Attendance",'Check Out', whatsapp=True):
                WhatsappMessage.whatsapp_message(whatsapp_data)
        except Exception as e:
            logger.warning(f"Error while sending Whatsapp notificaton to {instance.employee.user.username} in notifications about check out: {e}") 
            
        return Response(result, status=status.HTTP_200_OK)


class CheckInOutUpdateView(AbstractRetrieveUpdateAPIView):
    """
    Employee Check In/Out Update Api View

    SURESH 21-03-2023
    AJAY, 18.04.2023
    """

    serializer_class = CheckInOutSerializer
    detailed_serializer_class = CheckInOutDetailSerializer
    filterset_fields = {"id": ["in", "exact"], "employee": ["in", "exact"]}
    queryset = EmployeeCheckInOutDetails.objects.all()
    
    def time_diff(self, start, end):
        start_dt = datetime.combine(timezone_now(), start)
        end_dt = datetime.combine(timezone_now(), end)
        return (end_dt - start_dt).total_seconds() / 3600
    
    def patch(self, request, *args, **kwargs):
        MultitenantSetup().create_to_connection(request)
        print(self.get_queryset)
        qs = self.filter_queryset(self.get_queryset())
      
        print("750",qs)
        try:
            logger.info(request.data)
            
            
            if 'status' in request.data and request.data.get('status') == "absent":

                domain = f"{self.request.scheme}://{self.request.get_host()}/"
                time_in_string = request.data.get('time_in')

                # Specify the format of the datetime string
                time_in_format = "%Y-%m-%d %H:%M"


                # Parse the datetime string into a datetime object
                time_in = datetime.strptime(time_in_string, time_in_format)

                # Localize the datetime object to the timezone specified in Django settings                                       
                time_in_string = request.data.get('time_in')

                # Specify the format of the datetime string
                time_in_format = "%Y-%m-%d %H:%M"

                # Parse the datetime string into a datetime object
                time_in = datetime.strptime(time_in_string, time_in_format)
                # Localize the datetime object to the timezone specified in Django settings                                       
                time_in = localize_dt(time_in, settings.TIME_ZONE)

                time_out_string = request.data.get('time_out')

                # Specify the format of the datetime string
                time_out_format = "%Y-%m-%d %H:%M"

                # Parse the datetime string into a datetime object
                time_out = datetime.strptime(time_out_string, time_out_format)

                # Localize the datetime object to the timezone specified in Django settings                                       
                time_out = localize_dt(time_out, settings.TIME_ZONE)
                
                # check weather a employee is requesting under shift timings
                employee_shift_timings = AssignedAttendanceRules.objects.filter(employee_id=request.data.get('emp_id'), is_deleted=False
                                                                                ).values('attendance_rule__shift_in_time','attendance_rule__shift_out_time', 
                                                                                         'attendance_rule__half_day_work_duration', 'attendance_rule__full_day_work_duration')
                if not employee_shift_timings.exists():
                    message = f"Employee Does Not Have Any Active Attendance Rule"
                    return Response(
                        error_response(message,message, 400),
                        status=status.HTTP_400_BAD_REQUEST
                )
                shift_in_time =  employee_shift_timings.first().get('attendance_rule__shift_in_time')
                shift_out_time =  employee_shift_timings.first().get('attendance_rule__shift_out_time')
                half_day_work_duration = employee_shift_timings.first().get('attendance_rule__half_day_work_duration')
                full_day_work_duration = employee_shift_timings.first().get('attendance_rule__full_day_work_duration')
                if not(shift_in_time <= time_in.time() <= shift_out_time and shift_in_time <= time_out.time() <= shift_out_time):
                    message = f"Please Select Time In Between Your Shift Timings ({shift_in_time.strftime('%I:%M %p')} - {shift_out_time.strftime('%I:%M %p')})"
                    return Response(
                        error_response(message,message, 400),
                        status=status.HTTP_400_BAD_REQUEST
                )
                    
                #Check weather employee is complted at least half day
                time_difference = datetime.combine(timezone_now(), time_out.time()) - datetime.combine(timezone_now(), time_in.time())
                wk_hours, wk_minutes = divmod(time_difference.seconds // 60, 60)  
                tt_work_duration = hrs_to_mins(wk_hours, wk_minutes)  
                half_work_duration = hrs_to_mins(half_day_work_duration.split(':')[0], half_day_work_duration.split(':')[1])
                full_work_duration = hrs_to_mins(full_day_work_duration.split(':')[0], full_day_work_duration.split(':')[1])

                if tt_work_duration < half_work_duration:
                    message = f"Please Complete At Least Half Day"
                    return Response(
                        error_response(message,message, 400),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # check weather comes under first half/ second half / full day
                shift_obj = None
                if tt_work_duration >= full_work_duration:
                    shift_obj = 'Full_Day'
                else:
                    first_half_end_time = (datetime.combine(timezone_now(), shift_in_time) + timedelta(minutes=half_work_duration)).time()
                    second_half_start_time = first_half_end_time

                    actual_duration_first_half = self.time_diff(max(time_in.time(), shift_in_time), min(time_out.time(), first_half_end_time))
                    actual_duration_second_half = self.time_diff(max(time_in.time(), second_half_start_time), min(time_out.time(), shift_out_time))

                    if actual_duration_first_half > actual_duration_second_half:
                        shift_obj =  "First_Half"
                    else:
                        shift_obj = "Second_Half"
                #checking if there are any pending leaves
                leave_status = LeavesHistory.objects.filter(employee_id=request.data.get('emp_id'), 
                                                            start_date__lte=time_in.date(), end_date__gte=time_in.date(), status__in=[10,20])
                message = ''
                if leave_status.filter(start_day_session__isnull=True, end_day_session__isnull=True).exists():
                #    message = f"There are pending leave requests for the day {time_in.date().strftime('%d-%m-%Y')} (Full Day). Kindly obtain approval before proceeding." 
                    message = 'Leave Request Is Recorded For The Day (Full Day)'
                
                if leave_status.exists() and leave_status.first().start_day_session == 'FIRST_HALF' and shift_obj != 'Second_Half':
                    message = 'Leave Request Is Recorded For The Day (First Half)'
                
                if leave_status.exists() and leave_status.first().start_day_session == 'SECOND_HALF' and shift_obj != 'First_Half':
                    message = 'Leave Request Is Recorded For The Day (Second Half)'
                
                if message:
                    return Response(
                        error_response(message,message, 400),
                        status=status.HTTP_400_BAD_REQUEST
                    ) 
                
                date_of_checked_in_convert=''
                current_date=timezone_now().strftime('%Y-%m-%d %I:%M %p')
                if time_in:
                    date_of_checked_in_convert = parse(str(time_in)).strftime('%Y-%m-%d') if time_in else ''                


                time_difference = time_out - time_in
                # Get the total seconds

                total_seconds = time_difference.total_seconds()

                # Calculate hours and minutes

                hours = int(total_seconds // 3600)

                minutes = int((total_seconds % 3600) // 60)

                # Handle negative time difference

                if total_seconds < 0:

                    hours *= -1

                    minutes *= -1

                obj = EmployeeCheckInOutDetails.objects.create(
                    employee_id=request.data.get('emp_id'),
                    time_in = time_in,
                    time_out = time_out,
                    date_of_checked_in = date_of_checked_in_convert,
                    action_status=20,                    
                    action = 10,
                    work_duration=str(hours)+":" +str(minutes),
                    absent_period = shift_obj,
                    action_reason = request.data.get('reason','')
                )
                qs = self.filter_queryset(self.get_queryset())
                instances = []
                for obj in qs:
                    print(obj)
                    serializer = self.serializer_class(
                        instance=obj, data=self.request.data, partial=True
                    )
                    print(serializer.is_valid(raise_exception=True))
                    if serializer.is_valid(raise_exception=True):

                        attendance_start_day, attendace_end_day = fetch_attendace_rule_start_end_dates(obj.employee.company_id)
                        check_month = get_monthly_record_obj_month(attendance_start_day, attendace_end_day, obj.date_of_checked_in)

                        month_data, is_created = EmployeeMonthlyAttendanceRecords.objects.get_or_create(employee_id=obj.employee_id, 
                                                                                                        month=check_month, 
                                                                                                        year=obj.date_of_checked_in.year)                        
                        login_date = obj.date_of_checked_in.strftime('%Y-%m-%d')
                        print("100 - ",month_data)
                        attendance_data = month_data.attendance_data
                        print("906 - ",obj.absent_period)
                        prd = 1 if obj.absent_period == 'Full_Day' else 0.5
                        
                        if login_date not in attendance_data:
                            attendance_data[login_date] = {
                                'breaks': 0,
                                'reason': obj.absent_period,
                                'status': 'P',
                                'time_in': obj.time_in.strftime('%Y-%m-%d %I:%M %p'),
                                'time_out': obj.time_out.strftime('%Y-%m-%d %I:%M %p'),
                                'anamolies': {'count': 0},
                                'present_count': prd,
                                'work_duration': str(obj.time_out - obj.time_in).rsplit(':', 1)[0],
                                'break_duration': None,
                                'over_time_data': '0:0',
                                'approval_status': ''
                            }
                        month_data.attendance_data=attendance_data
                        month_data.save()
                    instances.append(serializer.save())                                                                        
                rep_man = EmployeeReportingManager.objects.filter(
                        employee_id=request.data.get('emp_id'),
                        is_deleted=False,
                        manager_type__manager_type=ManagerType.PRIMARY,
                    ).first()
                # reporting manager notifications
                emp_date_of_checked_in = parse(str(time_in)).strftime('%d-%m-%Y %I:%M %p') if time_in else ''
                if rep_man:
                    rp_emp_number = rep_man.manager.work_details.employee_number
                    tag = rp_emp_number if rp_emp_number else "-"
                    employee = Employee.objects.get(id=request.data.get('emp_id'))
                    body=f'Hello {rep_man.manager.name.title()} [{tag}],\n\n{rep_man.employee.name.title()} [{rep_man.employee.work_details.employee_number}] has applied for Anamoly Approval.\n\nReason : {request.data.get("action_reason")}\n\nConnect to your HRMS application to find more details.\n\nDate of check in : {date_of_checked_in_convert}\nPlease refer the link for more information {domain}adminApproveLogs\n\nThanks & Regards,\n{employee.company.company_name.title()}'
                    subject = 'Anamoly Requested for Absent'
                
                    try:
                        email_data={
                            'subject':subject,
                            'body':body,
                            'to_email':rep_man.manager.official_email
                        }
                        if check_alert_notification("Attendance",'Approvals', email=True):
                            Util.send_email(email_data)
                    except Exception as e:
                        logger.warning(f"Error while sending email notificaton : {e}")   
                    try:
                        whatsapp_data = {
                                        'phone_number': rep_man.manager.user.phone,
                                        'subject': subject,
                                        "body_text1":f"{rep_man.employee.name.title()} [{rep_man.employee.work_details.employee_number}] is requesting to approve Absent",
                                        'body_text2': f"Dated on {emp_date_of_checked_in}",
                                        'url': f"{domain}adminApproveLogs",
                                        "company_name":rep_man.manager.company.company_name.title()
                                        }
                        if check_alert_notification("Attendance",'Approvals', whatsapp=True):
                            WhatsappMessage.whatsapp_message(whatsapp_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {obj.employee.user.username} in notifications about clcok history approvals: {e}")  
                #employee notifications
                if int(request.data.get('action')) == 10:
                    subject = 'Anamoly Requested for Absent'
                
                    emp_body=f"""
                            Hello {obj.employee.user.username.title()} [{obj.employee.work_details.employee_number}],
                            
                            {subject} successfully. Connect to your HRMS application to find more details.
                            
                            Date of check in : {emp_date_of_checked_in}                                
                            Please refer the link for more information {domain}userAttendancelogs
                            
                            Thanks & Regards,
                            {obj.employee.company.company_name.title()}
                        """
                    try:
                        data={
                            'subject':subject,
                            'body':emp_body,
                            'to_email':obj.employee.official_email
                        }
                        if check_alert_notification("Attendance",'Approvals', email=True):
                            Util.send_email(data)
                    except Exception as e:
                        logger.warning(f"Error while sending email notificaton : {e}")    
                        
                    try:
                        whatsapp_data = {
                                        'phone_number': obj.employee.user.phone,
                                        'subject': subject,
                                        "body_text1":f"Your Absent Approval request has been raised successfully.",
                                        'body_text2': f"Dated on {emp_date_of_checked_in}",
                                        'url': f"{domain}userAttendancelogs",
                                        "company_name":obj.employee.company.company_name.title()
                                        }
                        if check_alert_notification("Attendance",'Approvals', whatsapp=True):
                            WhatsappMessage.whatsapp_message(whatsapp_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {obj.employee.user.username} in notifications about clcok history approvals: {e}")      
            
                
            else:
                instances = []
                for obj in qs:
                    print(obj)
                    serializer = self.serializer_class(
                        instance=obj, data=self.request.data, partial=True
                    )
                    if serializer.is_valid(raise_exception=True):
                        rep_man = EmployeeReportingManager.objects.filter(
                            employee_id=obj.employee.id,
                            is_deleted=False,
                            manager_type__manager_type=ManagerType.PRIMARY,
                        ).first()        
                        # Send email Notification to the employee
                        check_status = ''
                        if 'action_status' in request.data:
                            # updating the monthly attendance records attendance_data
                            print("start")
                            print("989 - ",obj.date_of_checked_in.month)
                            print("990 - ",obj.date_of_checked_in.year)
                            
                            attendance_start_day, attendace_end_day = fetch_attendace_rule_start_end_dates(obj.employee.company_id)
                            check_month = get_monthly_record_obj_month(attendance_start_day, attendace_end_day, obj.date_of_checked_in)

                            month_data, is_created = EmployeeMonthlyAttendanceRecords.objects.get_or_create(employee_id=obj.employee_id, 
                                                                                                            month=check_month, 
                                                                                                            year=obj.date_of_checked_in.year)                        
                            login_date = obj.date_of_checked_in.strftime('%Y-%m-%d')
                            print("100 - ",month_data)
                            attendance_data = month_data.attendance_data
                            prd = 1 if obj.absent_period == 'Full_Day' else 0.5
                            print
                            if login_date not in attendance_data:
                                attendance_data[login_date] = {
                                    'breaks': 0,
                                    'reason': obj.absent_period,
                                    'status': 'P',
                                    'time_in': obj.time_in.strftime('%Y-%m-%d %I:%M %p'),
                                    'time_out': obj.time_out.strftime('%Y-%m-%d %I:%M %p'),
                                    'anamolies': {'count': 0},
                                    'present_count': prd,
                                    'work_duration': str(obj.time_out - obj.time_in).rsplit(':', 1)[0],
                                    'break_duration': None,
                                    'over_time_data': '0:0',
                                    'approval_status': ''
                                }
                            month_data.attendance_data=attendance_data
                            month_data.save()
                            print("save")
                            domain = f"{self.request.scheme}://{self.request.get_host()}/"
                            employee = Employee.objects.get(id=obj.employee.id)
                            time_in = localize_dt(obj.time_in, settings.TIME_ZONE)
                            emp_number = employee.work_details.employee_number
                            tag = emp_number if emp_number else "-"
                            manager_name = self.request.user.username
                            if time_in:
                                # date_of_checked_in_convert = datetime.strptime(date_of_checked_in, "%Y-%m-%d").strftime("%d-%m-%Y")
                                # date_of_checked_in_convert = datetime.strptime(time_in, "%Y-%m-%dT%H:%M:%S.%f%z").strftime('%d-%m-%Y %I:%M %p')
                                date_of_checked_in_convert = parse(str(time_in)).strftime('%d-%m-%Y %I:%M %p') if time_in else ''
                            if int(request.data.get("action_status")) == 10:
                                check_status = 'Anamoly Approved'
                                w_subject = 'Anamoly'
                                valid_from = request.data.get('valid_from','')
                                valid_to = request.data.get('valid_to','')
                                body=f'Hello {employee.name.title()} [{tag}],\n\nYour applied Anamoly request has been Approved by {manager_name.title()}. Connect to your HRMS application to find more details.\n\nDate of check in : {date_of_checked_in_convert}\nPlease refer the link for more information {domain}userAttendancelogs\n\nThanks & Regards,\n{employee.company.company_name.title()}'
                                if obj.action == 50:
                                    check_status = 'Comp Off Approved'
                                    w_subject = 'Comp Off'
                                    body=f'Hello {employee.name.title()} [{tag}],\n\nYour applied Comp Off request has been Approved by {manager_name.title()}. Connect to your HRMS application to find more details.\n\nDate of check in : {date_of_checked_in_convert}\nValid From : {valid_from}\nValid To : {valid_to}\nPlease refer the link for more information {domain}userAttendancelogs\n\nThanks & Regards,\n{employee.company.company_name.title()}'
                                elif obj.action == 60:
                                    check_status = 'Over Time Approved'
                                    w_subject = 'Over Time'
                                    body=f'Hello {employee.name.title()} [{tag}],\n\nYour applied Over Time request has been Approved by {manager_name.title()}. Connect to your HRMS application to find more details.\n\nDate of check in : {date_of_checked_in_convert}\nPlease refer the link for more information {domain}userAttendancelogs\n\nThanks & Regards,\n{employee.company.company_name.title()}'    
                                elif obj.status == 'A':
                                    check_status = 'Anamoly Approved for Absent'
                                    w_subject = 'Absent Approval'
                                    body=f'Hello {employee.name.title()} [{tag}],\n\nYour applied {w_subject} request has been Approved by {manager_name.title()}. Connect to your HRMS application to find more details.\n\nDate of check in : {date_of_checked_in_convert}\nPlease refer the link for more information {domain}userAttendancelogs\n\nThanks & Regards,\n{employee.company.company_name.title()}'    
                            
                                # Employee Whatsapp notifications
                                try:
                                    whatsapp_data = {
                                                    'phone_number': employee.user.phone,
                                                    'subject': check_status,
                                                    "body_text1":f"Your {w_subject.lower()} request has been approved successfully.",
                                                    'body_text2': f"Dated on {date_of_checked_in_convert}",
                                                    'url': f"{domain}userAttendancelogs",
                                                    "company_name":employee.company.company_name.title()
                                                    }
                                    if check_alert_notification("Attendance",'Approvals', whatsapp=True):
                                        WhatsappMessage.whatsapp_message(whatsapp_data)
                                except Exception as e:
                                    logger.warning(f"Error while sending Whatsapp notificaton to {employee.user.username} in notifications about clcok history approvals: {e}")  
                            
                            elif int(request.data.get("action_status")) == 40:
                                check_status = 'Anamoly Rejected'
                                w_subject = 'Anamoly'
                                reject_reasons = serializer.validated_data.get('reject_reason')
                                body=f'Hello {employee.name.title()} [{tag}],\n\nYour applied Anamoly request has been Rejected by {manager_name.title()}. Connect to your HRMS application to find more details.\n\nDate of check in : {date_of_checked_in_convert}\nReject reason : {reject_reasons}\nPlease refer the link for more information {domain}userAttendancelogs\n\nThanks & Regards,\n{employee.company.company_name.title()}'         

                                if obj.action == 50:
                                    check_status = 'Comp Off Rejected'
                                    w_subject = 'Comp Off'
                                    body=f'Hello {employee.name.title()} [{tag}],\n\nYour applied Comp Off request has been Rejected by {manager_name.title()}. Connect to your HRMS application to find more details.\n\nDate of check in : {date_of_checked_in_convert}\nReject reason : {reject_reasons}\nPlease refer the link for more information {domain}userAttendancelogs\n\nThanks & Regards,\n{employee.company.company_name.title()}'         
                                elif obj.action == 60:    
                                    check_status = 'Over Time Rejected'
                                    w_subject = 'Over Time'
                                    body=f'Hello {employee.name.title()} [{tag}],\n\nYour applied Over Time request has been Rejected by {manager_name.title()}. Connect to your HRMS application to find more details.\n\nDate of check in : {date_of_checked_in_convert}\nReject reason : {reject_reasons}\nPlease refer the link for more information {domain}userAttendancelogs\n\nThanks & Regards,\n{employee.company.company_name.title()}'         
                                elif obj.status == 'A': 
                                    check_status = 'Anamoly Rejected for Absent'
                                    w_subject = 'Absent Approval'
                                    body=f'Hello {employee.name.title()} [{tag}],\n\nYour applied Anamoly Approval for Absent request has been Rejected by {manager_name.title()}. Connect to your HRMS application to find more details.\n\nDate of check in : {date_of_checked_in_convert}\nReject reason : {reject_reasons}\nPlease refer the link for more information {domain}userAttendancelogs\n\nThanks & Regards,\n{employee.company.company_name.title()}'         
                                # Employee Whatsapp notifications
                                try:
                                    whatsapp_data = {
                                                    'phone_number': employee.user.phone,
                                                    'subject': check_status,
                                                    "body_text1":f"Your {w_subject.lower()} request has been rejected",
                                                    'body_text2': f"Dated on {date_of_checked_in_convert}",
                                                    'url': f"{domain}userAttendancelogs",
                                                    "company_name":employee.company.company_name.title()
                                                    }
                                    if check_alert_notification("Attendance",'Approvals', whatsapp=True):
                                        WhatsappMessage.whatsapp_message(whatsapp_data)
                                except Exception as e:
                                    logger.warning(f"Error while sending Whatsapp notificaton to {employee.user.username} in notifications about clcok history approvals: {e}")  
                            
                                
                    if check_status:    
                        try:
                            data={
                                'subject':check_status,
                                'body':body,
                                'to_email':employee.official_email
                            }
                            if check_alert_notification("Attendance",'Approvals', email=True):
                                Util.send_email(data)
                        except Exception as e:
                            logger.warning(f"Error while sending email notificaton : {e}")
                            
                    # Send email Notification to the Manager   
                    if 'action' in request.data and int(request.data.get('action')) in [10,50,60] :
                        domain = f"{self.request.scheme}://{self.request.get_host()}/"
                        time_in = localize_dt(obj.time_in, settings.TIME_ZONE)
                        date_of_checked_in_convert=''
                        current_date=timezone_now().strftime('%d-%m-%Y %I:%M %p')
                        if time_in:
                            date_of_checked_in_convert = parse(str(time_in)).strftime('%d-%m-%Y %I:%M %p') if time_in else ''
                        if rep_man:
                            rp_emp_number = rep_man.manager.work_details.employee_number if not rep_man.is_multitenant else rep_man.multitenant_manager_emp_id
                            tag = rp_emp_number if rp_emp_number else "-"
                            employee = Employee.objects.get(id=obj.employee.id)
                            body=f'Hello {rep_man.manager.name.title() if not rep_man.is_multitenant else rep_man.multitenant_manager_name.title()} [{tag}],\n\n{rep_man.employee.name.title()} [{rep_man.employee.work_details.employee_number}] has applied for Anamoly Approval.\n\nReason : {request.data.get("action_reason")}\n\nConnect to your HRMS application to find more details.\n\nDate of check in : {date_of_checked_in_convert}\nPlease refer the link for more information {domain}adminApproveLogs\n\nThanks & Regards,\n{employee.company.company_name.title()}'
                            subject = 'Anamoly Requested'
                            w_subject = 'Anamoly'
                            if int(request.data.get('action')) == 50:
                                subject = 'Comp Off Requested'
                                w_subject = 'Comp Off'
                                cmp_added ='Full Day' if obj.compoff_added == 'full_day' else 'Half Day'
                                body=f'''
    Hello {rep_man.manager.name.title() if not rep_man.is_multitenant else rep_man.multitenant_manager_name.title()} [{tag}],
    
    {rep_man.employee.name.title()} [{rep_man.employee.work_details.employee_number}] has applied for Comp Off Approval. Connect to your HRMS application to find more details.
    
    Date of check in : {date_of_checked_in_convert}
    Comp Off requested at : {current_date}
    Comp Off period  : {cmp_added}
    Please refer the link for more information {domain}adminApproveLogs
    
    Thanks & Regards,
    {employee.company.company_name.title()}
    '''
                            elif int(request.data.get('action')) == 60:
                                subject = 'Over Time Requested'
                                body=f'Hello {rep_man.manager.name.title() if not rep_man.is_multitenant else rep_man.multitenant_manager_name.title()} [{tag}],\n\n{rep_man.employee.name.title()} [{rep_man.employee.work_details.employee_number}] has applied for Over Time Approval. Connect to your HRMS application to find more details.\n\nDate of check in : {date_of_checked_in_convert}\nPlease refer the link for more information {domain}adminApproveLogs\n\nThanks & Regards,\n{employee.company.company_name.title()}'
                                
                            try:
                                data={
                                    'subject':subject,
                                    'body':body,
                                    'to_email':rep_man.manager.official_email if not rep_man.is_multitenant else rep_man.multitenant_manager_email
                                }
                                if check_alert_notification("Attendance",'Approvals', email=True):
                                    Util.send_email(data)
                            except Exception as e:
                                logger.warning(f"Error while sending email notificaton : {e}")   
                                
                            # Manager Whatsapp notifications
                            try:
                                whatsapp_data = {
                                                'phone_number': rep_man.manager.user.phone,
                                                'subject': subject,
                                                "body_text1":f"{rep_man.employee.name.title()} [{rep_man.employee.work_details.employee_number}] is requesting to approve {w_subject.lower()}",
                                                'body_text2': f"Dated on {date_of_checked_in_convert}",
                                                'url': f"{domain}adminApproveLogs",
                                                "company_name":rep_man.manager.company.company_name.title()
                                                }
                                if check_alert_notification("Attendance",'Approvals', whatsapp=True):
                                    WhatsappMessage.whatsapp_message(whatsapp_data)
                            except Exception as e:
                                pass
                                # logger.warning(f"Error while sending Whatsapp notificaton to {rep_man.manager.user.username} in notifications about about Clock history: {e}")   
                                
                        if int(request.data.get('action')) == 10:
                            subject = 'Anamoly Requested'
                            w_subject = 'Anamoly'
                        if int(request.data.get('action')) == 50:
                            subject = 'Comp Off Requested'
                            w_subject = 'Comp Off'
                        elif int(request.data.get('action')) == 60:
                            subject = 'Over Time Requested'
                            w_subject = 'Over Time'
                        cmp_added ='Full Day' if obj.compoff_added == 'full_day' else 'Half Day'  
                        emp_body=f"""
    Hello {obj.employee.user.username.title()} [{obj.employee.work_details.employee_number}],
    
    {subject} successfully. Connect to your HRMS application to find more details.
    Date of check in : {date_of_checked_in_convert}
    
    Please refer the link for more information {domain}userAttendancelogs
    
    Thanks & Regards,
    {obj.employee.company.company_name.title()}

    """     
    
                        if int(request.data.get('action')) == 50:
                            emp_body=f"""
    Hello {obj.employee.user.username.title()} [{obj.employee.work_details.employee_number}],
    
    {subject} successfully. Connect to your HRMS application to find more details.
    Date of check in : {date_of_checked_in_convert}
    Comp Off period  : {cmp_added}
    
    Please refer the link for more information {domain}userAttendancelogs
    
    Thanks & Regards,
    {obj.employee.company.company_name.title()}
    """
                        try:
                            data={
                                'subject':subject,
                                'body':emp_body,
                                'to_email':obj.employee.official_email
                            }
                            if check_alert_notification("Attendance",'Approvals', email=True):
                                Util.send_email(data)
                        except Exception as e:
                            logger.warning(f"Error while sending email notificaton : {e}")   
                        
                        # Employee Whatsapp notifications
                        try:
                            whatsapp_data = {
                                            'phone_number': obj.employee.user.phone,
                                            'subject': subject,
                                            "body_text1":f"You have successfully raised a request for {w_subject.lower()} approval",
                                            'body_text2': f"Dated on {date_of_checked_in_convert}",
                                            'url': f"{domain}userAttendancelogs",
                                            "company_name":obj.employee.company.company_name.title()
                                            }
                            if check_alert_notification("Attendance",'Approvals', whatsapp=True):
                                WhatsappMessage.whatsapp_message(whatsapp_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to {obj.employee.user.username} in notifications about about Clock history: {e}")  
                    
                    instances.append(serializer.save())
            MultitenantSetup().go_to_old_connection(request)     
            return Response(
                data="Updated Successfully",
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            MultitenantSetup().go_to_old_connection(request)
            return Response(
                data={
                    "errors": f'{e} Error At: {traceback.format_exc()}',
                    "status": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )



class AbsentApprovalCompanyRetrieveViewV2(APIView):
    model = EmployeeCheckInOutDetails
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
        employee_checkd_in = request.user.employee_details.first()
        employee_checkd_in_role = employee_checkd_in.roles.first().name

        company_id = kwargs.get("company_id")
        paginator = self.pagination_class()
        params = request.query_params
        q_filters = models.Q(employee__company_id=company_id, is_deleted=False)
        if employee_checkd_in_role in ['TEAM LEAD']:
            # check_ids = list(EmployeeReportingManager.objects.filter(manager_id=employee_checkd_in.id).values_list("employee_id", flat=True))
            # check_ids.append(employee_checkd_in.id)
            q_filters &= models.Q(employee_id__in=EmployeeReportingManager.objects.filter(manager_id=employee_checkd_in.id, is_deleted=False).values_list("employee_id", flat=True))
        if employee_checkd_in_role in ['MANAGER']:
            q_filters &= models.Q(employee_id__in=self.get_manager_employees([employee_checkd_in]))
        if 'search_filter' in params:
            q_filters &= models.Q(
                models.Q(employee__user__username__icontains=search_filter_decode(params.get("search_filter"))) |
                models.Q(leave_rule__name__icontains=search_filter_decode(params.get("search_filter"))) |
                models.Q(employee__work_details__employee_number__icontains=search_filter_decode(params.get("search_filter")))
            )
        if 'department_id' in params:
            q_filters &= models.Q(employee__work_details__department_id__in=params['department_id'].split(','))
            
        if 'employee_id' in params:
            q_filters &= models.Q(employee_id__in=params.get('employee_id').split(','))
        
        if 'session_year' in params:
            q_filters &= models.Q(leave_rule__employeeleaverulerelation__session_year__session_year__in=params.get('session_year').split(','))
              
        if 'start_date' in params and 'end_date' in params:
            # q_filters &= models.Q(
            #     models.Q(start_date__range=(params['start_date'], params['end_date'])) |
            #     models.Q(end_date__range=(params['start_date'], params['end_date'])))
            q_filters &= models.Q(start_date__lte = params['end_date'],end_date__gte = params['start_date'])
        # else:
        #     att_sett_data = AttendanceRuleSettings.objects.filter(company_id=company_id)
        #     psc_from_date =  att_sett_data.first().attendance_input_cycle_from
        #     psc_to_date   =  att_sett_data.first().attendance_input_cycle_to
        #     pay_cycle_from_date,pay_cycle_to_date,current_payout_date = get_paycycle_dates(timezone_now(),psc_from_date,psc_to_date)
        #     q_filters &= models.Q(start_date__lte=timezone_now().date(),end_date__gte=pay_cycle_from_date.date())
        #     start_date = pay_cycle_from_date.date().strftime('%Y-%m-%d')
        if 'action_status' in params:
            if params['action_status'] in ['10','20','30','40']:
                q_filters &= models.Q(status=params['action_status'])
        
        qs = self.model.objects.filter(q_filters).annotate(
                      
            time_in_display=models.F('time_in'),
            time_out_display=models.F('time_out'),
            employee_name=models.F('employee__user__username'),
            employee_number=models.F("employee__work_details__employee_number"),
            work_duration_display=models.F('work_duration'),
            break_duration_display=models.F('break_duration'),
            breaks_display=models.F('breaks'),
            location_display=models.F('location'),
            action_reason_display=models.Case(
                # *[models.When(status=i[0], then=models.Value(i[1])) for i in self.model.STATUS_CHOICES],
                models.When(models.Q(action=10), then=models.Value("Mark as Present")),                                        
                default=models.Value(""),
                output_field=models.CharField()
            ),
            action_status_display=models.Case(
                # *[models.When(status=i[0], then=models.Value(i[1])) for i in self.model.STATUS_CHOICES],
                models.When(models.Q(action_status=10), then=models.Value("Approved")),                
                models.When(models.Q(action_status=20), then=models.Value("Pending")),                
                models.When(models.Q(action_status=30), then=models.Value("Cancelled")),            
                models.When(models.Q(action_status=40), then=models.Value("Rejected")),                                
                default=models.Value(""),
                output_field=models.CharField()
            ),
          
            date_of_join=models.F('employee__date_of_join'),
            
        ).all().values(
            "id", "employee", "employee_name", "employee_number","action_status",         
            "time_in_display", "time_out_display", "work_duration_display", "break_duration_display",
            "breaks_display", "location_display","action_reason_display","date_of_join","action_status_display"
        ).order_by("-updated_at")
                
        if "is_export" in params:
            data_df = pd.DataFrame(qs,columns=["employee_number","employee_name","action_status",         
            "time_in_display", "time_out_display", "work_duration_display", "break_duration_display",
            "breaks_display", "location_display","action_reason_display","date_of_join","action_status_display"])
            if data_df.empty:
                return Response(
                    error_response('No Data Found To Export', "No Data Found To Export", 404),
                    status=status.HTTP_404_NOT_FOUND
                )             
            data_df['start_date'] = data_df.apply(lambda obj : obj['start_date'].strftime("%d-%m-%Y"), axis=1)
            data_df['end_date'] = data_df.apply(lambda obj : obj['end_date'].strftime("%d-%m-%Y"), axis=1)
            data_df['created_at__date'] = data_df.apply(lambda obj : obj['created_at__date'].strftime("%d-%m-%Y"), axis=1)
            data_df['date_of_join'] = data_df.apply(lambda obj : obj['date_of_join'].strftime("%d-%m-%Y"), axis=1)
            data_df.rename(columns={"employee_number":"ID","employee_name":"Employee Name","date_of_join":"DOJ","created_at__date":"Created Date","start_date":"Start Date","end_date":"End Date"},inplace=True)

            file_name = f"export_attendance_approval_{timezone_now().date()}.xlsx"
            return excel_converter(data_df,file_name)       
        page = paginator.paginate_queryset(qs, request)
        return Response(
            success_response(
                paginator.get_paginated_response(page), "Successfully fetched Company Employee attendance Relations", 200
            ),
            status=status.HTTP_200_OK
        )


class AbsentApprovalCompanyUpdateViewV2(APIView):
    model = EmployeeCheckInOutDetails
    
    def patch(self, request, *args, **kwargs):
        try:
            obj_id = kwargs.get("id")
            paginator = self.pagination_class()
            params = request.query_params                            
            qs = self.model.objects.get(id=obj_id,is_deleted=False)
            qs.action_status = int(params.get("action_status"))
            qs.save()
            return Response(
                    data="Updated Successfully",
                    status=status.HTTP_200_OK,
                )
        except Exception as e:
            return Response(
                data={
                    "errors": f'{e} Error At: {traceback.format_exc()}',
                    "status": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )






class ClockDetailsView(AbstractListAPIView):
    serializer_class = CheckInOutDetailSerializer
    filterset_fields = ["company", "id"]
    queryset = Employee.objects.prefetch_related("clock_details").all()

    def _init_clock(self, date_of_checked_in: date) -> dict:
        return {
            "status": "A",
            "date_of_checked_in": str(date_of_checked_in),
            "time_in": None,
            "time_out": None,
            "punch_history": [],
            "work_duration": None,
            "break_duration": None,
            "breaks": None,
            "anamolies": {"count": 0},
        }

    def get(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        result = {}

        params = self.request.GET
        today = timezone_now().date()
        from_date = params.get("fromDate", today)
        to_date = params.get("toDate", today)
        action_status = params.get("actionStatus", [])
        extra_filters = Q()

        if isinstance(from_date, str):
            from_date = strptime(from_date, fmt="%Y-%m-%d")

        if isinstance(to_date, str):
            to_date = strptime(to_date, fmt="%Y-%m-%d")
        if params.get('id'):
            date_of_join = qs.get(id=params.get('id')).date_of_join
            from_date = max(date_of_join, from_date)

        if action_status:
            extra_filters &= Q(action_status__in=[action_status])
        
        if params.get('status'):
            extra_filters &= Q(status=params.get('status'))

        for i in range(((to_date + timedelta(1)) - from_date).days):
            extraction_dt = from_date + timedelta(i)
            result[f"{extraction_dt}"] = []
            clock_details = {}
            for obj in qs:
                employee = EmployeeDetailSerializer(obj).data
                clock_qs = EmployeeCheckInOutDetails.objects.filter(
                    employee=obj,
                    date_of_checked_in=extraction_dt,
                )
                clock_qs = clock_qs.filter(extra_filters)
                if clock_qs.exists():
                    clock_details = CheckInOutDetailSerializer(clock_qs.first()).data
                elif action_status:
                    continue
                else:
                    if obj.leaveshistory_set.filter(
                        start_date__lte=extraction_dt, end_date__gte=extraction_dt,
                        status=10, employee__clock_details__isnull=True
                    ):
                        clock_details = {
                            "status": "L",
                            "date_of_checked_in": str(from_date + timedelta(i)),
                            "time_in": None,
                            "time_out": None,
                            "punch_history": [],
                            "work_duration": None,
                            "break_duration": None,
                            "breaks": None,
                            "anamolies": {"count": 0},
                        }
                    else:
                        clock_details = self._init_clock(from_date + timedelta(i))
                    if clock_details['status'] == 'A':
                        if work_rule_relation := leave_models.EmployeeWorkRuleRelation.objects.filter(
                            employee=obj #, effective_date__lte=extraction_dt
                        ).first():
                            work_rule = work_rule_relation.work_rule
                            week_number = get_month_weeks(
                                extraction_dt, need_week_number_only=True
                            )
                            rule_choice = leave_models.WorkRuleChoices.objects.filter(
                                work_rule=work_rule, week_number=week_number
                            ).first()
                            if is_day_type(choice=rule_choice, dt_input=extraction_dt):
                                clock_details['status'] = "WO"
                result[f"{extraction_dt}"].append(
                    {
                        "employee": employee,
                        "clock_details": clock_details,
                    }
                )
        return Response(data=result, status=status.HTTP_200_OK)


class AnamolyHistoryView(AbstractListAPIView):
    """
    Anamoly History View

    AJAY, 27.03.2023
    """

    serializer_class = CheckInOutDetailSerializer
    queryset = EmployeeCheckInOutDetails.objects.annotate(
        has_anamolies=Exists(AnamolyHistory.objects.filter(clock=OuterRef("id")))
    ).filter(has_anamolies=True)

    def filter_queryset(self, queryset):
        params = self.request.GET

        today = timezone_now().date()
        from_date = params.get("fromDate", today)
        to_date = params.get("toDate", today)
        action_status = params.get("actionStatus", [])

        filters = {}

        if isinstance(from_date, str):
            filters["date_of_checked_in__gte"] = strptime(from_date, fmt="%Y-%m-%d")

        if isinstance(to_date, str):
            filters["date_of_checked_in__lte"] = strptime(to_date, fmt="%Y-%m-%d")

        if action_status:
            filters["action_status__in"] = [int(i) for i in action_status.split(",")]

        if "employee" in params:
            filters["employee"] = params["employee"]

        if "company" in params:
            filters["employee__company"] = params["company"]

        return super().filter_queryset(queryset.filter(**filters))


class AttendanceResendRemiderView(APIView):
    model = AssignedAttendanceRules

    def post(self, request, format=None):
        data = request.data
        print(data)
        for emp in data["employee"]:
            print(emp)
            try:
                attendance = AssignedAttendanceRules.objects.filter(employee=emp)[0]
                domain = f"{self.request.scheme}://{self.request.get_host()}/"
                emp_number = attendance.employee.work_details.employee_number
                # gender = attendance.employee.gender
                tag = emp_number if emp_number else "-"
                body=f'Hello {attendance.employee.name.title()} [{tag}],\n\nThis is attendance resend reminder please check below your shift detailes.\n\nAttendance rule name: {attendance.attendance_rule.name}\nshift intime: {attendance.attendance_rule.shift_in_time.strftime("%I:%M %p")}\nshift out_time: {attendance.attendance_rule.shift_out_time.strftime("%I:%M %p")}\nGrace in time: {attendance.attendance_rule.grace_in_time}\nGrace out time: {attendance.attendance_rule.grace_out_time}\nFull day work duration: {attendance.attendance_rule.full_day_work_duration}\nHalf day work duration: {attendance.attendance_rule.half_day_work_duration}\nMaximum breaks for day: {attendance.attendance_rule.max_breaks}\nMaximum break duration: {attendance.attendance_rule.max_break_duration}\nPlease refer the link for more information {domain}userAttendanceRules\n\nThanks & Regards,\n{attendance.attendance_rule.company.company_nameattendance.employee.name.title()}'  
                data={
                    'subject':'This is the attendance reminder',
                    'body':body,
                    'to_email':attendance.employee.official_email
                }
                if check_alert_notification("Attendance",'Employee Attendance Rule Update', email=True):
                    Util.send_email(data)
            except Exception as e:
                print(str(e))
                pass

        return Response(
            data={
                "message": "Attendance resend reminder sent successfully",
            },
            status=status.HTTP_200_OK,
        )

class AttendanceMontlyEmployeeView(APIView):
    model = EmployeeMonthlyAttendanceRecords
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        employee = request.user.employee_details.first()
        params = request.query_params
        query_filters = Q(employee=employee, employee__payroll_status=True)
        if 'year' not in params:
            return Response(
                {
                    "error": "Year Must be select"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        if 'month' not in params:
            return Response(
                {
                    "error": "Month Must be select"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        query_filters &= Q(month=params['month'])
        query_filters &= Q(year=params['year'])
        if "employee" in params:
            query_filters &=Q(employee=params.get("employee"))
        qs =  list(self.model.objects.filter(query_filters).order_by('employee_id', 'month', 'year').distinct('employee_id', 'month', 'year').values(
            "year", "month", "attendance_data", "present_days", "leaves_count", "overtime_count",
            "absent_count", "anamoly_count", "lop_count", "penalty_details", "is_payroll_run","leaves_encash_count", "hr_comment", "manager_comment"
        ))
        # data = []
        # if 'status' in params:
        #     status = params["status"]
        #     for obj in qs:
                
        return Response(qs, status=status.HTTP_200_OK)


class AttendanceMontlyManagerHRView(APIView):
    model = EmployeeMonthlyAttendanceRecords
    permission_classes = (permissions.IsAuthenticated,)
    
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
    
    def get(self, request):
        company_id = request.user.employee_details.first().company_id
        params = request.query_params
        query_filter = Q(employee__company_id=company_id, employee__payroll_status=True)
        user = request.user
        if 'year' not in params:
            return Response(
                {
                    "error": "Year Must be select"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        if 'month' not in params:
            return Response(
                {
                    "error": "Month Must be select"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if 'department_id' in params:
            query_filter &= Q(employee__work_details__department_id__in=params["department_id"].split(','))
        if 'employee_id' in params:
            query_filter &= Q(employee_id__in = params.get('employee_id').split(','))
        role = request.user.employee_details.first().roles.values_list('name', flat=True).first()
        if role in ['MANAGER']:
            user_id = request.user.employee_details.first().id
            emp_ids = self.get_manager_employees([user_id])
            query_filter &= Q(employee_id__in=emp_ids)
        elif role not in ["HR", "CEO", "ADMIN"]:
            query_filter &= Q(employee__employee__manager_id=request.user.employee_details.first().id, employee__employee__is_deleted=False)

            # prod , commit, db_name
        # env = env = os.environ.get('APP_ENV')
        # db_name = settings.DATABASES["default"]["NAME"] #"qa_indianpayrollservice_com"
        # subprocess.run(f'/var/www/html/hrms/hrms_env/bin/python /var/www/html/hrms/src/scripts/employee_montly_attendance_data_run.py {env} '+db_name, shell=True)
        months = params['month'].split(',')
        month_year_dict = {
            params['year'] : params['month'].split(',')
         }
        if len(months) > 1 and str(12) in months:
            months.remove('12')
            dec_year = int(params['year']) - 1 
            month_year_dict[str(dec_year)] = [12]
            month_year_dict[params['year']] = months
        month_year_dict = dict(sorted(month_year_dict.items()))
        op_data = []
        for year,month in month_year_dict.items():
            month_qs = self.model.objects.filter(query_filter, month__in=month, year=year).select_related('employee').prefetch_related(
                "employee__work_details", "employee__work_details__department")
            # if user.employee_details.first().roles.values_list('name', flat=True).first() == "HR":
            #     if month_qs.filter(is_manager_updated=False, employee__employee__manager__isnull=False).exclude(
            #         employee__roles__name__in=['MANAGER', 'CEO']
            #     ):
            #         return Response(
            #             {
            #                 "error": f"Manager's ({', '.join(month_qs.filter(is_manager_updated=False, employee__employee__isnull=False).order_by('employee__employee__manager__user__username').distinct('employee__employee__manager__user__username').values_list('employee__employee__manager__user__username', flat=True))}) Didnt Updated this monthly data for some employees."
            #             },
            #             status=status.HTTP_400_BAD_REQUEST
            #         )
            
            data = list(month_qs.annotate(
                employee_name=F("employee__user__username")
                    ).values(
                    "employee__work_details__department__name", 
                    "employee__work_details__employee_number",
                    "employee_name", "present_days", "leaves_count",
                    "absent_count", "anamoly_count", "penalty_details",
                    "is_manager_updated", "month", "year", "employee_id",
                    "is_hr_updated", "lop_count", "updated_manager_lop_count",
                    "overtime_count",
                    "updated_hr_lop_count", "manager_hosted_by__user__username", "hr_hosted_by__user__username", "is_payroll_run","leaves_encash_count",
                    "hr_comment", "manager_comment", "employee__date_of_join"
                ).order_by('year','month'))
            for op in data:
                l_details = {}
                p_details = op['penalty_details']
                p_days = sum([i[1]['no_of_days_deducted'] for i in p_details.items()])
                for p_item in p_details.items():
                    if p_item[1]['deducted_from'] not in l_details:
                        l_details[p_item[1]["deducted_from"]] = 0
                    l_details[p_item[1]["deducted_from"]] += p_item[1]['no_of_days_deducted']
                op['no_of_penalty_days'] = p_days
                op['penalty_data'] = l_details
                op_data.append(op)
        if 'is_export' in request.query_params:
            if len(op_data) > 0:
                df = pd.DataFrame(op_data)
                df['month'] = df.month.apply(lambda x: 1 if x == 12 else x + 1)
                df['month'] =  pd.to_datetime(df.month, format='%m').dt.month_name().str[::]
                df.rename(columns={'employee__work_details__employee_number':'ID','employee_name':'Employee Name', 'month': 'Month',
                                        'employee__work_details__department__name':'Department','present_days':'Present Days',
                                        'leaves_count':'Leave Days','absent_count':'Absent Days',
                                        'no_of_penalty_days':'Penalty Days','anamoly_count':'Outstanding Anomalies',
                                        'updated_manager_lop_count':'RM LOP', 'manager_hosted_by__user__username': 'MANAGER', 'manager_comment': 'MANAGER COMMENT', 'updated_hr_lop_count':'HR LOP', 'hr_hosted_by__user__username': 'HR NAME', 'hr_comment': 'HR COMMENT', "lop_count": "Total Lop Count", "employee__date_of_join": "Employee Date Of Join"}, inplace=True)
                df = df[['ID','Employee Name', "Employee Date Of Join", 'Month', 'Department','Present Days','Leave Days',
                            'Absent Days','Penalty Days','Outstanding Anomalies','RM LOP', 'MANAGER', 'MANAGER COMMENT',
                            'HR LOP', 'HR NAME', 'HR COMMENT',  "Total Lop Count"]]
                df['S.NO'] = range(1, len(df) + 1)
                df.set_index('S.NO', inplace=True)
                file_name = f"admin_consolidate_report_{timezone_now().date()}.xlsx"
                return excel_converter(df,file_name)
            return Response(
                {
                    "error": "No data found with selected options"
                },
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            op_data,
            status=status.HTTP_200_OK
        )
    
    def put(self, request):
        data = request.data
        if 'year' not in data:
            return Response(
                {
                    "error": "Year Must be select"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        if 'month' not in data:
            return Response(
                {
                    "error": "Month Must be select"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        employee_lop_data = data.get("employee_lop_data", [])
        company_id = request.user.employee_details.first().company_id
        qs = self.model.objects.filter(
            employee__company_id=company_id,
            year=data['year'], month__in=data['month'], employee_id__in=[emp['id'] for emp in employee_lop_data])
        role = request.user.employee_details.first().roles.values_list('name', flat=True).first()
        if role not in ['HR', 'MANAGER', 'TEAM LEAD', 'ADMIN']:
            return Response(
                {
                    "error": "Only HR or Manager Can Update"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        for employee_lop in employee_lop_data:
            obj = qs.filter(employee_id=employee_lop["id"], month=employee_lop['month']).first()
            if obj:
                if role == "HR":
                    obj.is_hr_updated = True
                    obj.hr_hosted_by = request.user.employee_details.first()
                    obj.updated_hr_lop_count = employee_lop['lop_count']
                    obj.hr_comment = employee_lop.get('hr_comment')
                else:
                    obj.is_manager_updated = True
                    obj.manager_hosted_by = request.user.employee_details.first()
                    obj.manager_comment = employee_lop.get("manager_comment")
                    obj.updated_manager_lop_count = employee_lop['lop_count']
                obj.save()
        return Response(
            {
                'message': 'Data updated successfully'
            },
            status=status.HTTP_200_OK
        )

class ConsolidateNotificationDatesView(APIView):
    model = ConsolidateNotificationDates
    
    def get(self, request):
        company_id = request.user.employee_details.first().company_id
        now_date = timezone_now().date()
        if not ConsolidateNotificationDates.objects.filter(company_id = company_id).exists():
            ConsolidateNotificationDates.objects.create(
                    company_id = company_id,
                    employee_start_date = now_date,
                    employee_end_date  = now_date,
                    reporting_manager_start_date  = now_date,
                    reporting_manager_end_date  = now_date,
                    hr_manager_start_date  = now_date,
                    hr_manager_end_date  = now_date
                )
        data  = ConsolidateNotificationDates.objects.filter(
                                                company_id = company_id
                                            ).values('id','company_id','employee_start_date','employee_end_date',
                                                    'reporting_manager_start_date','reporting_manager_end_date',
                                                    'hr_manager_start_date','hr_manager_end_date')    
        return Response(
            success_response(data,'Consolidate Notification Dates fetched successfully'),
            status=status.HTTP_200_OK
        )
    def put(self, request):
        try:
            request_data = request.data
            company_id = request.user.employee_details.first().company_id
            consolidate_query = ConsolidateNotificationDates.objects.filter(company_id = company_id)
            att_sett_data = AttendanceRuleSettings.objects.filter(company_id = company_id)
            if not att_sett_data.exists():
                return Response(
                        error_response('Please Set up Attendance Rules for the company', 400),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            if not consolidate_query.exists():
                message = 'Please Provide Correct Company Id'
                return Response(
                        error_response(message, message, 404),
                        status=status.HTTP_404_NOT_FOUND
                    )  
            """   
            psc_from_date =  att_sett_data.first().attendance_input_cycle_from
            psc_to_date   =  att_sett_data.first().attendance_input_cycle_to
            # payout_date = att_sett_data.first().attendance_start_month
             
            employee_start_date = datetime.strptime(request_data.get('employee_start_date'), "%Y-%m-%d")
            employee_end_date = datetime.strptime(request_data.get('employee_end_date'), "%Y-%m-%d")
            reporting_manager_start_date = datetime.strptime(request_data.get('reporting_manager_start_date'), "%Y-%m-%d")
            reporting_manager_end_date = datetime.strptime(request_data.get('reporting_manager_end_date'), "%Y-%m-%d")
            hr_manager_start_date = datetime.strptime(request_data.get('hr_manager_start_date'), "%Y-%m-%d")
            hr_manager_end_date = datetime.strptime(request_data.get('hr_manager_end_date'), "%Y-%m-%d")
            
            current_date = timezone_now()
            pay_cycle_from_date,pay_cycle_to_date,current_payout_date = get_paycycle_dates(current_date,psc_from_date,psc_to_date)
            
            if not (pay_cycle_from_date <= employee_start_date <= pay_cycle_to_date and employee_end_date <= pay_cycle_to_date) :
                return Response(
                    error_response('Employee Notification should be in between the pay cycle dates', 'Some thing went wrong', 400),
                    status=status.HTTP_400_BAD_REQUEST
                )
           
            if not (pay_cycle_to_date < reporting_manager_start_date <= current_payout_date and reporting_manager_end_date <= current_payout_date) :
                return Response(
                    error_response('Reporting Manager Notification should be in between the pay cycle end date and pay out date', 'Some thing went wrong', 400),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not (pay_cycle_to_date < hr_manager_start_date <= current_payout_date and hr_manager_end_date <= current_payout_date) :
                return Response(
                    error_response('HR Manager Notification should be in between the pay cycle end date and pay out date', 'Some thing went wrong', 400),
                    status=status.HTTP_400_BAD_REQUEST
                )    
            """ 
            ConsolidateNotificationDates.objects.filter(company_id = company_id).update(
                **request_data
            )
            return Response(
                    success_response(consolidate_query.values(),'Consolidate Notification Dates updated successfully'),
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                    error_response(str(e), 'Some thing went wrong', 400),
                    status=status.HTTP_400_BAD_REQUEST
                )

class KeyLoggerApi(APIView):
    """
    this class is used to store the logs via keylogger
    """
    model = KeyloggerAttendanceLogs
    permission_classes = [permissions.AllowAny]
    pagination_class = CustomPagePagination

    def post(self, request):
        try:
            data = request.data
            data = KeyloggerAttendanceLogsSerializer(data = data, many=True)
            if data.is_valid():
                data.save()
            else:
                Response(
                    success_response(str(data.errors),
                                     "error in saving"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                    success_response(data.data,'key logger added successfully'),
                    status=status.HTTP_201_CREATED
                ) 
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "Got error in saving attendance log", 400),
                status=status.HTTP_400_BAD_REQUEST
            )

class KeyLoggerV2(APIView):
        
        model = KeyloggerAttendanceLogs
        # permission_classes = [permissions.AllowAny]
        pagination_class = CustomPagePagination
        def get(self, request):
        #search pending
            try:
                params = request.query_params
                # req_emp_id = request.user.employee_details.all().first().work_details.employee_number #presently no needed as giving complete admin
                q_filters=Q()
                if 'start_date' in params and 'end_date' in params:
                    start_date = datetime.strptime(params.get("start_date"), "%Y-%m-%d").date()
                    end_date = datetime.strptime(params.get("end_date"), "%Y-%m-%d").date()
                    if end_date < start_date:
                        message = "To Date Should Be Greater Than The From Date"
                        return Response(
                                error_response(message, message, 400),
                                status=status.HTTP_400_BAD_REQUEST
                            )
                if 'start_date' in params and 'end_date' in params:
                    start_date = datetime.strptime(params.get("start_date"), "%Y-%m-%d").date()
                    end_date = (datetime.strptime(params.get("end_date"), "%Y-%m-%d")+timedelta(days=1)).date()
                    q_filters &= (Q(system_on__range = [start_date, end_date])|Q(break_start__range = [start_date, end_date])|Q(break_end__range = [start_date, end_date]))


                elif 'start_date' in params:
                    start_date = datetime.strptime(params.get("start_date"), "%Y-%m-%d").date()
                    q_filters &= (Q(system_on__date__gte=start_date)|Q(system_off__date__gte=start_date)|Q(break_start__date__gte=start_date)|Q(break_end__date__gte=start_date))

                elif 'end_date' in params:
                    end_date = datetime.strptime(params.get("end_date"), "%Y-%m-%d").date()
                    q_filters &= (Q(system_on__date__lte=end_date)|Q(system_off__date__lte=end_date)|Q(break_start__date__lte=end_date)|Q(break_end__date__lte=end_date))
                
                # if 'department' in params: # need to add stopped due to prod migration
                #     q_filters &= Q(emp_id__)
                if 'emp_ids' in params:
                    q_filters &= Q(emp_id__in= params.get('emp_ids').split(','))

                qs = self.model.objects.filter(q_filters).annotate(
                        duration_seconds=F('break_end') - F('break_start'),
                        # instance_duration=ExpressionWrapper(Func(F('duration_seconds'), function='EXTRACT', template='%(function)s(MINUTE FROM %(expressions)s)'),
                        #     output_field=DurationField()),
                        # instance_duration_hour=ExpressionWrapper(Func(F('duration_seconds'), function='EXTRACT', template='%(function)s(HOUR FROM %(expressions)s)'),
                        #     output_field=DurationField()),
                        instance_duration = ExpressionWrapper(F('duration_seconds')/60, output_field=models.DurationField()),
                        system_on_char   = models.functions.Cast(TimestampToStrDateTime(TimestampToIST(models.F('system_on'), 'Asia/Kolkata')), models.CharField()),
                        system_off_char  = models.functions.Cast(TimestampToStrDateTime(TimestampToIST(models.F('system_off'), 'Asia/Kolkata')), models.CharField()),
                        break_start_char = models.functions.Cast(TimestampToStrDateTime(TimestampToIST(models.F('break_start'), 'Asia/Kolkata')), models.CharField()),
                        break_end_char   = models.functions.Cast(TimestampToStrDateTime(TimestampToIST(models.F('break_end'), 'Asia/Kolkata')), models.CharField()),
                        employee_name = KeyloggerAttendanceLogs.objects.filter(emp_id=OuterRef('emp_id')).annotate(
                            empid=Subquery(Employee.objects.filter(work_details__employee_number=OuterRef('emp_id')).annotate(
                                empname= models.functions.Trim(Concat(F('first_name'),Value(" "),F('middle_name'),Value(" "),F('last_name'),))).values('empname')
                                )).values('empid')[:1],
                        employee_department = KeyloggerAttendanceLogs.objects.filter(emp_id=OuterRef('emp_id')).annotate(
                            empworkd_obj=Subquery(EmployeeWorkDetails.objects.filter(employee_number=OuterRef('emp_id')).annotate(
                                emp_dept= F('department__name')).values('emp_dept')
                                )).values('empworkd_obj')[:1],
                        employee_designation = KeyloggerAttendanceLogs.objects.filter(emp_id=OuterRef('emp_id')).annotate(
                            empworkd_obj=Subquery(EmployeeWorkDetails.objects.filter(employee_number=OuterRef('emp_id')).annotate(
                                emp_desig= F('designation__name')).values('emp_desig')
                                )).values('empworkd_obj')[:1]
                    )
                if not qs.exists():
                    message = "No Data Found For The Request"
                    return Response(
                            error_response(message, message, 400),
                            status=status.HTTP_400_BAD_REQUEST
                        )
                data = qs.values('employee_name', 'employee_department', 'employee_designation', 'emp_id', 'system_ip', 'system_name', 'internet_ip', 'system_on_char', 'system_off_char', 'break_start_char', 'break_end_char', 'instance_duration', 'system_location', 'internet_location', 'break_cause')
                # filters_data = {
                #     'emp_ids':set(KeyloggerAttendanceLogs.objects.all().values_list('emp_id', flat=True))
                # }
                filters_data = KeyloggerAttendanceLogs.objects.all().annotate(
                            emp_name=Subquery(Employee.objects.filter(
                                                work_details__employee_number=OuterRef('emp_id')).values('user__username')[:1])
                        ).values('emp_name','emp_id').distinct('emp_id')

                if ("download" in params) and (params['download']=="true"):
                    df = pd.DataFrame.from_dict(data)
                    file_name = "key logger report.xlsx"
                    return excel_converter(df,file_name)
                if data:
                    df = pd.DataFrame.from_dict(data)
                    df.replace({pd.NaT: None}, inplace=True)
                    df1 = df.groupby(['emp_id']).agg({
                        'employee_name':list,
                        'system_ip':list,
                        'system_name':list,
                        'internet_ip':list,
                        'system_on_char':list,
                        'system_off_char':list,
                        'break_start_char':list,
                        'break_end_char':list,
                        'instance_duration':list,
                        'system_location':list,
                        'internet_location':list,
                        'break_cause':list,
                        }).reset_index()
                    df2 = df.drop_duplicates(subset="emp_id") 
                    final_df = pd.merge(df2, df1, on="emp_id", suffixes=('_', ''))
                    data = final_df.to_dict("records")
                paginator = self.pagination_class()
                page = paginator.paginate_queryset(data, request)
                
                return Response(
                    success_response(
                        result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data}, msg= "Successfully fetched key logger data"
                    ),status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "error in fetching attendance log", 400),
                    status=status.HTTP_400_BAD_REQUEST
                )
from dateutil.relativedelta import relativedelta
class ConsolidateButtonStatus(APIView):
    """
    this class is used to get|set the status of button consolidate report
    """
    model = EmployeeMonthlyAttendanceRecords
    def get(self, request):
        try:
            #return button enable or not
            params = request.query_params
            months = params.get('months', None)
            year = params.get('year', None)
            if not months:
                return Response("key months need to send in query params")
            if not year:
                return Response("key year need to send in query params")
            company = request.user.employee_details.first().company
            months = months.split(',')
            consolidate_button_qs = ConsolidateButton.objects.filter(year=year, month__in=months, company=company)
            if consolidate_button_qs.exists():
                return Response({"button_enabled":False, 'cause':'already cron button has run'})
            else:
                attendance_rule_setting = AttendanceRuleSettings.objects.filter(company = company)
                if not attendance_rule_setting.exists():
                    return Response("Attendance rule setting not present")
                attendance_cycle_to  = attendance_rule_setting.first().attendance_input_cycle_to
                if not attendance_cycle_to:
                    return Response("Attendance rule cycle from is not defined")

                for month in months:
                    attendance_day_to_run = date(int(year), int(month), attendance_cycle_to)
                    today = timezone_now().date() - relativedelta(months=1)
                    if attendance_day_to_run > today :    
                        return Response({"button_enabled":False, 'cause':'button not allowing as not completed the month'})
                return Response({"button_enabled":True, 'cause':f'not existing in consolidatButton and it"s {today}'})            
        except Exception as e:
            return Response(
                    error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "error in fetching attendance log", 400),
                    status=status.HTTP_400_BAD_REQUEST
                )

    def post(self, request):
        
        try:
            params = request.query_params
            months = params.get('months', None)
            year = params.get('year', None)
            emps = params.get('emps', None)
            if not months:
                return Response("key month need to send in query params")
            if not year:
                return Response("key year need to send in query params")
            q_filters = Q()
            if emps:
                q_filters &= Q(employee_id__in=emps)

            company = request.user.employee_details.first().company

            #to do implement the cron need to check in server or call it directly
            env = 'local'
            db_name = 'vg_april5_db'
            # env = env = os.environ.get('APP_ENV')
            # db_name = settings.DATABASES["default"]["NAME"] #"qa_indianpayrollservice_com"
            # subprocess.run(f'/var/www/html/hrms/hrms_env/bin/python /var/www/html/hrms/src/scripts/employee_montly_attendance_data_run.py {env} '+db_name, shell=True)
            months= months.split(',')
            for month in months:
                ConsolidateButton.objects.get_or_create(year=year, month=month, company=company)
                EmployeeMonthlyAttendanceRecords.objects.filter(year=year, month=month).filter(q_filters).update(is_cron_run=True)
            return Response({"button_enabled":False, 'cause':"cron has run"})
        
        except Exception as e:
            return Response(
                    error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "error in fetching attendance log", 400),
                    status=status.HTTP_400_BAD_REQUEST
                )

from dateutil.relativedelta import relativedelta
class ConsolidateButtonStatus(APIView):
    """
    this class is used to get|set the status of button consolidate report
    """
    model = EmployeeMonthlyAttendanceRecords
    def get(self, request):
        try:
            #return button enable or not
            params = request.query_params
            months = params.get('months', None)
            year = params.get('year', None)
            if not months:
                return Response("key months need to send in query params")
            if not year:
                return Response("key year need to send in query params")
            company = request.user.employee_details.first().company
            months = months.split(',')
            consolidate_button_qs = ConsolidateButton.objects.filter(year=year, month__in=months, company=company)
            if consolidate_button_qs.exists():
                return Response({"button_enabled":False, 'cause':'already cron button has run'})
            else:
                attendance_rule_setting = AttendanceRuleSettings.objects.filter(company = company)
                if not attendance_rule_setting.exists():
                    return Response("Attendance rule setting not present")
                attendance_cycle_to  = attendance_rule_setting.first().attendance_input_cycle_to
                if not attendance_cycle_to:
                    return Response("Attendance rule cycle from is not defined")

                for month in months:
                    attendance_day_to_run = date(int(year), int(month), attendance_cycle_to)
                    today = timezone_now().date() - relativedelta(months=1)
                    if attendance_day_to_run > today :    
                        return Response({"button_enabled":False, 'cause':'button not allowing as not completed the month'})
                return Response({"button_enabled":True, 'cause':f'not existing in consolidatButton and it"s {today}'})            
        except Exception as e:
            return Response(
                    error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "error in fetching attendance log", 400),
                    status=status.HTTP_400_BAD_REQUEST
                )

    def post(self, request):
        
        try:
            params = request.query_params
            months = params.get('months', None)
            year = params.get('year', None)
            emps = params.get('emps', None)
            if not months:
                return Response("key month need to send in query params")
            if not year:
                return Response("key year need to send in query params")
            q_filters = Q()
            if emps:
                q_filters &= Q(employee_id__in=emps)

            company = request.user.employee_details.first().company

            #to do implement the cron need to check in server or call it directly
            env = 'local'
            db_name = 'vg_april5_db'
            # env = env = os.environ.get('APP_ENV')
            # db_name = settings.DATABASES["default"]["NAME"] #"qa_indianpayrollservice_com"
            # subprocess.run(f'/var/www/html/hrms/hrms_env/bin/python /var/www/html/hrms/src/scripts/employee_montly_attendance_data_run.py {env} '+db_name, shell=True)
            months= months.split(',')
            for month in months:
                ConsolidateButton.objects.get_or_create(year=year, month=month, company=company)
                EmployeeMonthlyAttendanceRecords.objects.filter(year=year, month=month).filter(q_filters).update(is_cron_run=True)
            return Response({"button_enabled":False, 'cause':"cron has run"})
        
        except Exception as e:
            return Response(
                    error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "error in fetching attendance log", 400),
                    status=status.HTTP_400_BAD_REQUEST
                )
  
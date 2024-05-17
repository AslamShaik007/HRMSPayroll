import pandas as pd
import datetime as dt
import traceback
import pytz
from django.conf import settings

from django.db import models as db_models
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import success_response, error_response, search_filter_decode, excel_converter, get_paycycle_dates
from core.custom_paginations import CustomPagePagination

from core.utils import get_month_weeks
from leave.services import is_day_type
from core.utils import get_month_weeks, localize_dt, strftime, strptime
from core.utils import (
    b64_to_image,
    email_render_to_string,
    get_formatted_time,
    get_ip_address,
    strptime,
    timezone_now,
    TimestampToIST, TimestampToStr
)
from HRMSProject.multitenant_setup import MultitenantSetup
from attendance import models as attendance_models
from directory import models as directory_models
from leave import models as leave_models
from payroll import models as payroll_models
from HRMSApp.models import CompanyCustomizedConfigurations

"""
1. api/attendance/retrieve/clock/history/?id=345 --> EmployeeID Every Page

2. api/attendance/get/attendance_rule/145/ -> Company ID, Admin side
    Attendance rule settings -> Attendance rules

3. api/attendance/update/attendance_rule/164/ -> Attendance rule id, Admin side
    http://38.143.106.249/editattandancerules?id=164

4. api/attendance/retrieve/employee/attendance_rule/relation/145/ -> Company ID, Admin side
    Assign Attendance Rule

5. api/attendance/retrieve/clock/history/?fromDate=2023-07-12&toDate=2023-08-11&company=145&actionStatus=20, Admin side, user side
    Attendance Approvals

6. api/attendance/get/employee/assigned/attendance_rule/345/ User side
    Attendance rules

7. leave/get/employee/work_rule/relation/345/ User side
    Attendance rules

"""


class ClockDetailsViewV2(APIView):
    model = directory_models.Employee
    pagination_class = CustomPagePagination

    def _init_clock(self, date_of_checked_in, status="A", deducted_from=""):
        return {
            "status": status,
            "date_of_checked_in": date_of_checked_in,
            "time_in": "-",
            "time_out": "-",
            'time_in_format': "-", 'time_out_format': "-",
            "extra_data": {},
            "punch_history": [],
            "work_duration": "-",
            "break_duration": "-",
            "breaks": "",
            "deducted_from": deducted_from,
            "anamolies": {"count": 0, "data": []},
            "checkin_location" : '-'
        }
    
    def custom_is_day_type(self, week_number, work_type, dt_input, employee):
        work_rule_choice_obj = employee.employeeworkrulerelation_set.first()
        if not hasattr(employee.employeeworkrulerelation_set.first(), 'work_rule'):
            return False
        work_rule_choice_obj = work_rule_choice_obj.work_rule.work_rule_choices.filter(week_number=week_number)
        if not work_rule_choice_obj.exists():
            return False
        work_rule_choice_obj = work_rule_choice_obj.first()
        day = dt_input.strftime("%A")
        if day.lower() not in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            raise ValueError("Invalid day of the week")
        return getattr(work_rule_choice_obj, day.lower()) == work_type

    def get_manager_employees(self,man_id):
        emp_id = man_id
        my_list = []
        tag = True
        while tag:
            query = directory_models.EmployeeReportingManager.objects.filter(manager_id__in=emp_id,
                                                            manager__work_details__employee_status='Active',
                                                            is_deleted=False)
            if not query.exists():
                break
            my_list.extend(list(query.values_list('employee_id',flat=True)))
            emp_id = list(query.values_list('employee_id',flat=True))
        return my_list
    
    def get(self, request, *args, **kwargs):
        params = request.query_params
        q_filters = db_models.Q()
        emp_filters = db_models.Q()
        today = timezone_now().date()
        from_date = params.get("fromDate", today)
        to_date = params.get("toDate", today)
        action_status = params.get("actionStatus", [])
        employee_status = params.get('employee_status','Active')
        emp_filters &= db_models.Q(work_details__employee_status__in=employee_status.split(','))
        company_config, _ = CompanyCustomizedConfigurations.objects.get_or_create(company_id=request.user.employee_details.first().company.id)
        # if action_status:
        #     att_sett_data = attendance_models.AttendanceRuleSettings.objects.filter(company_id=params.get('company',1))
        #     psc_from_date =  att_sett_data.first().attendance_input_cycle_from
        #     psc_to_date   =  att_sett_data.first().attendance_input_cycle_to
        #     pay_cycle_from_date,pay_cycle_to_date,current_payout_date = get_paycycle_dates(timezone_now(),psc_from_date,psc_to_date)
        #     if 'fromDate' not in params:
        #         from_date = pay_cycle_from_date.date()
        if 'department_id' in params:
            emp_filters &= db_models.Q(work_details__department_id__in = params.get('department_id').split(','))
            q_filters &= db_models.Q(employee__work_details__department_id__in = params.get('department_id').split(','))
            
        if params.get("fromDate",'') and params.get("toDate",''):
            if (dt.datetime.strptime(to_date, "%Y-%m-%d") - dt.datetime.strptime(from_date, "%Y-%m-%d")).days > 31:
                message = "from date and to date cant be more than 31 days"
                return Response(
                    error_response(message,message),
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if 'search_filter' in params:
            emp_filters &= (
                db_models.Q(user__username__icontains=search_filter_decode(params.get("search_filter"))) |
                db_models.Q(work_details__employee_number__icontains = search_filter_decode(params.get("search_filter")))
                )
        if action_status:
            action_status = action_status.split(',')
        try:
            if 'id' in params:
                q_filters &= db_models.Q(employee_id__in=params.get('id').split(','))
                emp_filters &= db_models.Q(id__in=params.get('id').split(','))
            elif request.user.employee_details.first().roles.values_list('name', flat=True).first() in ['TEAM LEAD']:
                check_ids = list(request.user.employee_details.first().employee_manager.filter(is_deleted=False).values_list('employee_id', flat=True))
                # check_ids.append(request.user.employee_details.first().id)
                emp_filters &= db_models.Q(
                    id__in=check_ids
                )
            elif request.user.employee_details.first().roles.values_list('name', flat=True).first() in ["MANAGER"]:
                logged_in_user_id = request.user.employee_details.first().id
                emp_ids = self.get_manager_employees([logged_in_user_id])
                emp_filters &= db_models.Q(
                    id__in=emp_ids
                )
            if "company" in params:
                q_filters &= db_models.Q(employee__company_id=params["company"])
                emp_filters &= db_models.Q(company_id=params["company"])
                company_id = params["company"]
            qs = attendance_models.EmployeeCheckInOutDetails.objects.filter(q_filters)
            tz = attendance_models.AssignedAttendanceRules.objects.filter(employee__user_id=request.user.id).first()
            if tz:
                if tz.attendance_rule.selected_time_zone:
                    tzone = tz.attendance_rule.selected_time_zone
                else:
                    tzone = settings.TIME_ZONE
                today = timezone_now(tzone).date()
                # from_date = params.get("fromDate", today)
                # to_date = params.get("toDate", today)

                last_check_in = qs.filter(action_status = attendance_models.EmployeeCheckInOutDetails.OK).order_by('date_of_checked_in').last()
                
                if last_check_in:
                    if not last_check_in.time_out:
                        hour = tz.attendance_rule.shift_out_time.hour
                        minute = tz.attendance_rule.shift_out_time.minute
                    else:
                        last_timeout = localize_dt(last_check_in.time_out, tzone)
                        hour = last_timeout.hour
                        minute = last_timeout.minute
                    latest_time_out = dt.time(hour, minute)
                    
                    if tz.attendance_rule.shift_out_time > latest_time_out:
                        today = qs.order_by('date_of_checked_in').last().date_of_checked_in
                    
            emp_qs = self.model.objects.filter(emp_filters)
            
            if isinstance(from_date, str):
                from_date = strptime(from_date, fmt="%Y-%m-%d")

            if isinstance(to_date, str):
                to_date = strptime(to_date, fmt="%Y-%m-%d")

            if 'id' in params and ('fromDate' in params or 'toDate' in params):
                data_qs = self.model.objects.filter(id=params.get('id'))
                if not data_qs.exists():
                    return Response(
                        error_response("Employee Not exists", "Emp Not Exists", 404),
                        status=status.HTTP_404_NOT_FOUND
                    )
                date_of_join = data_qs.first().date_of_join
                company_id = data_qs.first().company_id
                if date_of_join > from_date:
                    from_date = date_of_join
            
            elif 'id' in params and not ('fromDate' in params or 'toDate' in params):
                last_checkin_objs = attendance_models.EmployeeCheckInOutDetails.objects.filter(
                    employee__id=params.get('id') #, time_out__isnull=True
                ).order_by('date_of_checked_in')
                if last_checkin_objs.exists() and last_checkin_objs.filter(time_out__isnull=True).exists():
                    l_check_obj_without_timeout = last_checkin_objs.filter(time_out__isnull=True).last().date_of_checked_in
                    l_check_obj_with_timeout = last_checkin_objs.last().date_of_checked_in
                    if l_check_obj_without_timeout >= l_check_obj_with_timeout:
                        from_date = l_check_obj_without_timeout
                        to_date = l_check_obj_without_timeout
                    else:
                        data_qs = self.model.objects.filter(id=params.get('id'))
                        if not data_qs.exists():
                            return Response(
                                error_response("Employee Not exists", "Emp Not Exists", 404),
                                status=status.HTTP_404_NOT_FOUND
                            )
                        date_of_join = data_qs.first().date_of_join
                        company_id = data_qs.first().company_id
                        if date_of_join > from_date:
                            from_date = date_of_join
                else:
                    data_qs = self.model.objects.filter(id=params.get('id'))
                    if not data_qs.exists():
                        return Response(
                            error_response("Employee Not exists", "Emp Not Exists", 404),
                            status=status.HTTP_404_NOT_FOUND
                        )
                    date_of_join = data_qs.first().date_of_join
                    company_id = data_qs.first().company_id
                    if date_of_join > from_date:
                        from_date = date_of_join
            q_filters &= db_models.Q(date_of_checked_in__range=[from_date, to_date])
            if action_status:
                q_filters &= db_models.Q(action_status__in=action_status)
                emp_filters &= db_models.Q(clock_details__action_status__in=action_status)

            if params.get('status'):
                q_filters &= db_models.Q(status=params.get('status'))
                emp_filters &= db_models.Q(clock_details__status=params.get('status'))
            
            qs = qs.filter(q_filters)
            emp_qs = emp_qs.filter(emp_filters)
            dates = [from_date + dt.timedelta(i) for i in range(((to_date + dt.timedelta(1)) - from_date).days)]
            current_page = request.build_absolute_uri()
            next =  None
            previous = None
            page = 0
            count = len(dates)
            limit = 10
            currentPage = None
            totalPages = None
            dates.sort()
            dates.reverse()
            if 'page' in params and 'page_size' in params:
                page = params.get("page", 1)
                if page == 'undefined':
                    page = 1
                page = int(page)
                page_size = int(params.get("page_size", 10))
                totalPages = divmod(count, page_size)[0] + 1 if divmod(count, page_size)[1] > 0 else divmod(count, page_size)[0]
                if page != totalPages:
                    next = current_page.replace(f'page={page}', f'page={page+1}')
                if page > 1:
                    previous = current_page.replace(f'page={page}', f'page={page-1}')
                dates = dates[(page-1)*page_size:(page*page_size)]
                if page > totalPages:
                    return Response(
                        {
                            "detail": "Invalid page."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            results = {}
            for extraction_dt in dates:
                week_number = get_month_weeks(extraction_dt)[extraction_dt.day]
                results[f'{extraction_dt}'] = []
                for obj in emp_qs.order_by("id").distinct("id"):
                    week_off = self.custom_is_day_type(week_number, 0, extraction_dt, obj)
                    half_week_off = self.custom_is_day_type(week_number, 1, extraction_dt, obj)
                    op_data = {}
                    op_data['employee_details'] = emp_qs.filter(id=obj.id).annotate(
                        employee_details=db_models.expressions.Func(
                                    db_models.Value('id'), 'id',
                                    # db_models.Value('date_of_join'), 'date_of_join',
                                    db_models.Value('name'), 'user__username',
                                    db_models.Value('attendance_rules'), db_models.expressions.Func(
                                        db_models.Value('name'), 'assignedattendancerules__attendance_rule__name',
                                        db_models.Value('enableOverTime'), 'assignedattendancerules__attendance_rule__enable_over_time',
                                        db_models.Value('orgInTime'), 'assignedattendancerules__attendance_rule__shift_in_time',
                                        db_models.Value('orgOutTime'), 'assignedattendancerules__attendance_rule__shift_out_time',
                                        db_models.Value('autoClockOut'), 'assignedattendancerules__attendance_rule__auto_clock_out',
                                        db_models.Value('selectedTimeZone'), 'assignedattendancerules__attendance_rule__selected_time_zone',
                                        function='jsonb_build_object',
                                        output_field=db_models.JSONField()
                                    ),
                                    # db_models.Value('workweek_rule'), db_models.expressions.Func(
                                    #     db_models.Value('name'), 'employeeworkrulerelation__work_rule__name',
                                    #     function='jsonb_build_object',
                                    #     output_field=db_models.JSONField()
                                    # ),
                                    db_models.Value('number'), db_models.F('work_details__employee_number'),
                                    db_models.Value('department'), db_models.F('work_details__department__name'),
                                    # db_models.Value('sub_department'), db_models.F('work_details__sub_department__name'),
                                    # db_models.Value('designation'), db_models.F('work_details__designation__name'),
                                    db_models.Value('work_location'), db_models.F('work_details__work_location'),
                                    # db_models.Value('employee_type'), db_models.Case(
                                    #     db_models.When(work_details__employee_type__employee_type=10, then=db_models.Value("Full Time")),
                                    #     db_models.When(work_details__employee_type__employee_type=20, then=db_models.Value("Part Time")),
                                    #     db_models.When(work_details__employee_type__employee_type=30, then=db_models.Value("Intern")),
                                    #     db_models.When(work_details__employee_type__employee_type=40, then=db_models.Value("On Contract")),
                                    #     db_models.When(work_details__employee_type__employee_type=50, then=db_models.Value("Others")),
                                    #     default=db_models.Value(""), output_field=db_models.CharField()
                                    # ),
                                    db_models.Value('employee_status'), db_models.F('work_details__employee_status'),
                                    # db_models.Value('employee_grade'), db_models.F("work_details__employee_grade__grade"),
                                    db_models.Value('reporting_manager'), ArrayAgg(
                                        db_models.functions.Concat(
                                            db_models.F('employee__manager__first_name'), db_models.Value(" "), db_models.F('employee__manager__last_name'),
                                            output_field=db_models.CharField()   
                                        ),
                                        filter=db_models.Q(employee__isnull=False, employee__manager_type__manager_type=10, employee__is_deleted=False, employee__manager__work_details__employee_status='Active'),
                                        distinct=True
                                    ),
                                    # db_models.Value('leave_rules'), db_models.expressions.Func(
                                    #     db_models.Value('name'), ArrayAgg('employeeleaverulerelation__leave_rule__name', distinct=True), 
                                    #     # ArrayAgg('employeeleaverulerelation__leave_rule__name', distinct=True),
                                    #     function='jsonb_build_object',
                                    #     output_field=db_models.JSONField()
                                    # ),
                                    function='jsonb_build_object',
                                    output_field=db_models.JSONField()
                                )
                    
                    ).values(
                        "employee_details"
                    ).first()['employee_details']
                    if qs.filter(employee_id=obj.id, date_of_checked_in=extraction_dt).exists():
                        clock = qs.filter(employee_id=obj.id, date_of_checked_in=extraction_dt).first()
                        # clock.annotate(vv=TimestampToStr(TimestampToIST(db_models.F('time_in'), "Pacific/Bougainville"))).values('vv')
                        try:
                            selected_time_zone = selected_time_zone=clock.employee.assignedattendancerules_set.first().attendance_rule.selected_time_zone
                        except:
                            selected_time_zone = settings.TIME_ZONE       
                        c_status = "P"
                        c_diducted_from = ""
                        can_apply_comp_off = False
                        if clock.status == "P":
                            if clock.employee.leaveshistory_set.filter(
                            db_models.Q(start_date__lte=extraction_dt, end_date__gte=extraction_dt, status=leave_models.LeavesHistory.APPROVED, is_penalty=False) & (
                                db_models.Q(start_day_session__isnull=False) | db_models.Q(end_day_session__isnull=False)
                            )
                            ).exists():
                                c_status = "HL"
                            else:
                                c_status = "P"
                        elif clock.status=="A" and clock.action_status==20 and clock.action==10:

                            c_status="A"
                        elif clock.status=="A" and clock.action_status==40 and clock.action==10:
                            c_status="A"
                        elif ck_data := clock.employee.leaveshistory_set.filter(
                            start_date__lte=extraction_dt,
                            end_date__gte=extraction_dt,
                            status=leave_models.LeavesHistory.APPROVED,
                            is_penalty=True
                        ):
                            c_status = "PN"
                            c_diducted_from = ck_data.first().leave_rule.name
                        elif clock.employee.leaveshistory_set.filter(
                            start_date__lte=extraction_dt,
                            end_date__gte=extraction_dt,
                            status=leave_models.LeavesHistory.APPROVED,
                            leave_rule__name="Loss Of Pay",
                            is_penalty=False
                        ).exists():
                            c_status = "PN"
                            c_diducted_from = "Loss Of Pay"
                        elif clock.employee.company.holidays_set.filter(
                            holiday_date=extraction_dt,
                            is_deleted=False, holiday_type = False
                        ).exists() and clock.compoff_added is None:
                            if clock.employee.leaveshistory_set.filter(
                                start_date__lte=extraction_dt,
                                end_date__gte=extraction_dt,
                                status=leave_models.LeavesHistory.APPROVED,
                                is_penalty=False,
                                leave_rule__holidays_between_leave=True
                            ):
                                c_status = "L"
                            else:
                                c_status = "H"
                        elif clock.employee.company.holidays_set.filter(
                            holiday_date=extraction_dt,
                            is_deleted=False, holiday_type = False
                        ).exists() and clock.compoff_added is not None:
                            c_status = "CO"
                            if dt.datetime.now().date()  < (extraction_dt + dt.timedelta(days=company_config.compoff_apply_days_excemption if company_config.compoff_apply_days_excemption else 0)):
                                can_apply_comp_off = True
                        elif half_week_off and not clock.anamolies.filter(~db_models.Q(status=10)).exists() and clock.overtime_hours == 0:
                            c_status = "P"
                        elif half_week_off and not clock.anamolies.filter(~db_models.Q(status=10)).exists() and clock.overtime_hours != 0:
                                c_status = "OT"
                        elif half_week_off and clock.anamolies.exists():
                            c_status = "AN"
                        elif week_off and clock.compoff_added is None:
                            if clock.employee.leaveshistory_set.filter(
                                start_date__lte=extraction_dt,
                                end_date__gte=extraction_dt,
                                status=leave_models.LeavesHistory.APPROVED,
                                is_penalty=False,
                                leave_rule__weekends_between_leave=True
                            ):
                                c_status = "L"
                            else:
                                c_status = "WO"
                        elif week_off and clock.compoff_added is not None:
                            c_status = "CO"
                            if dt.datetime.now().date()  < (extraction_dt + dt.timedelta(days=company_config.compoff_apply_days_excemption if company_config.compoff_apply_days_excemption else 0)):
                                can_apply_comp_off = True
                        elif clock.employee.leaveshistory_set.filter(
                            db_models.Q(start_date__lte=extraction_dt, end_date__gte=extraction_dt, status=leave_models.LeavesHistory.APPROVED, is_penalty=False) & (
                                db_models.Q(start_day_session__isnull=False) | db_models.Q(end_day_session__isnull=False)
                            )
                        ).exists():
                            c_status = "HL"
                        elif clock.employee.leaveshistory_set.filter(
                            start_date__lte=extraction_dt,
                            end_date__gte=extraction_dt,
                            status=leave_models.LeavesHistory.APPROVED,
                            is_penalty=False
                        ):
                            c_status = "L"
                        elif clock.anamolies.filter(status=10, action__in=[10, 20], clock__overtime_hours=0):
                            c_status = "P"
                        elif clock.anamolies.filter(status=10, action=30):
                            c_status = "L"
                        elif clock.anamolies.filter(status=10, action=40):
                            c_status = "LOP"
                        elif clock.overtime_hours != 0:
                            c_status = "OT"
                        elif clock.anamolies.filter(status__in=[20, 30]):
                            c_status = "AN"
                        elif clock.anamolies.filter(status=40):
                            c_status = "A"

                        elif clock.anamolies.exists():
                            c_status = "AN"
                        else:
                            c_status = "P"
                        op = qs.filter(employee_id=obj.id, date_of_checked_in=extraction_dt).annotate(
                            c_status=db_models.Value(c_status),
                            c_diducted_from=db_models.Value(c_diducted_from),
                            can_apply_comp_off=db_models.Value(
                                can_apply_comp_off
                            )
                        ).annotate(
                            clock_details=db_models.expressions.Func(
                                db_models.Value("id"), "id",
                                db_models.Value("status"), db_models.F('c_status'),
                                db_models.Value("can_apply_comp_off"), db_models.F('can_apply_comp_off'),                                
                                db_models.Value("checkin_location"), db_models.F('checkin_location'),
                                db_models.Value("deducted_from"), db_models.F('c_diducted_from'),
                                db_models.Value("date_of_checked_in"), "date_of_checked_in",
                                db_models.Value("time_in"), db_models.Case(
                                    db_models.When(time_in__isnull=False, then=db_models.functions.Cast(TimestampToIST(db_models.F('time_in'), selected_time_zone), db_models.CharField())),
                                    default=db_models.Value("-"), output_field=db_models.CharField()
                                ), 
                                db_models.Value("time_in_format"), TimestampToStr(TimestampToIST(db_models.F('time_in'), selected_time_zone)),
                                db_models.Value("latest_time_in"), TimestampToIST(db_models.F('latest_time_in'), selected_time_zone),
                                db_models.Value("time_out"), db_models.Case(
                                    db_models.When(time_out__isnull=False, then=db_models.functions.Cast(TimestampToIST(db_models.F('time_out'), selected_time_zone), db_models.CharField())),
                                    default=db_models.Value("-"), output_field=db_models.CharField()
                                ),
                                db_models.Value("time_out_format"), TimestampToStr(TimestampToIST(db_models.F('time_out'), selected_time_zone)),
                                db_models.Value("punch_history"), "extra_data",
                                db_models.Value("work_duration"), db_models.Case(
                                    db_models.When(work_duration__isnull=False, then=db_models.F("work_duration")),
                                    default=db_models.Value("-"), output_field=db_models.CharField()    
                                ),
                                db_models.Value("overtime_hours"), "overtime_hours",
                                db_models.Value("break_duration"), db_models.Case(
                                    db_models.When(break_duration__isnull=False, then=db_models.F("break_duration")),
                                    default=db_models.Value("-"), output_field=db_models.CharField()    
                                ),
                                db_models.Value("breaks"), "breaks",
                                # db_models.Value("employee_selfie"), "employee_selfie",
                                db_models.Value("action"), "action",
                                db_models.Value("action_reason"),"action_reason",
                                db_models.Value("action_display"), db_models.Case(
                                    *[db_models.When(action=i[0], then=db_models.Value(i[1])) for i in attendance_models.EmployeeCheckInOutDetails.ACTION_CHOICES],
                                    output_field=db_models.CharField(), default=db_models.Value("")
                                ),
                                db_models.Value("action_status"), "action_status",
                                db_models.Value("action_status_display"), db_models.Case(
                                    *[db_models.When(action_status=i[0], then=db_models.Value(i[1])) for i in attendance_models.EmployeeCheckInOutDetails.ACTION_STATUS_CHOICES],
                                    output_field=db_models.CharField(), default=db_models.Value("")
                                ),
                                # db_models.Value("extra_data"), "extra_data",
                                db_models.Value("anamolies"), db_models.expressions.Func(
                                    db_models.Value("count"), db_models.Count('anamolies', distinct=True),
                                    db_models.Value("data"), ArrayAgg(
                                        db_models.expressions.Func(
                                            db_models.Value('id'), 'anamolies__id',
                                            db_models.Value('type'), db_models.Case(
                                                *[db_models.When(anamolies__choice=i[0], then=db_models.Value(i[1])) for i in attendance_models.AnamolyHistory.ANAMOLY_CHOICES],
                                                output_field=db_models.CharField(), default=db_models.Value("")
                                            ),
                                            db_models.Value('discrepancy'), 'anamolies__result',
                                            db_models.Value('action'), db_models.Case(
                                                *[db_models.When(action=i[0], then=db_models.Value(i[1])) for i in attendance_models.AnamolyHistory.ACTION_CHOICES],
                                                output_field=db_models.CharField(), default=db_models.Value("")
                                            ),
                                            db_models.Value('status'), db_models.Case(
                                                *[db_models.When(anamolies__status=i[0], then=db_models.Value(i[1])) for i in attendance_models.AnamolyHistory.STATUS_CHOICES],
                                                output_field=db_models.CharField(), default=db_models.Value("")
                                            ),
                                            function='jsonb_build_object',
                                            output_field=db_models.JSONField() 
                                        ),
                                        distinct=True,
                                        ),
                                    function='jsonb_build_object',
                                    output_field=db_models.JSONField() 
                                ),
                                db_models.Value("approval_reason"), "approval_reason",
                                db_models.Value("reject_reason"), "reject_reason",
                                db_models.Value("is_logged_out"), "is_logged_out",
                                db_models.Value("auto_clocked_out"), db_models.Case(
                                    db_models.When(
                                        db_models.Q(time_out__isnull=False, is_logged_out=False,
                                                    employee__assignedattendancerules__attendance_rule__auto_clock_out=True
                                        ), then=db_models.Value("AC")
                                    ), default=db_models.Value(""), output_field=db_models.CharField()
                                ),
                                function='jsonb_build_object',
                                output_field=db_models.JSONField()
                            ),
                        
                        ).values('clock_details').first()['clock_details']
                        op_data["clock_details"] = op
                    else:
                        op = {}
                        if params.get('actionStatus', None) is None:
                            op = self._init_clock(extraction_dt)
                            if week_off and obj.leaveshistory_set.filter(
                                start_date__lte=extraction_dt,
                                end_date__gte=extraction_dt,
                                status=leave_models.LeavesHistory.APPROVED,
                                is_penalty=False,
                                leave_rule__weekends_between_leave=False
                            ).exclude(leave_rule__name="Loss Of Pay").exists():
                                op = self._init_clock(extraction_dt, 'WO')
                            elif obj.leaveshistory_set.filter(
                                start_date__lte=extraction_dt,
                                end_date__gte=extraction_dt,
                                status=leave_models.LeavesHistory.APPROVED,
                                is_penalty=False,
                            ).exclude(leave_rule__name="Loss Of Pay").exists():
                                op = self._init_clock(extraction_dt, 'L')
                            elif week_off:
                                op = self._init_clock(extraction_dt, 'WO')
                            elif obj.company.holidays_set.filter(
                                holiday_date=extraction_dt, is_deleted=False, holiday_type=False
                            ).exists():
                                op = self._init_clock(extraction_dt, 'H')
                            elif ck_data := obj.leaveshistory_set.filter(
                                start_date__lte=extraction_dt,
                                end_date__gte=extraction_dt,
                                status=leave_models.LeavesHistory.APPROVED,
                                is_penalty=False
                            ).exists():
                                op = self._init_clock(extraction_dt, 'A', "Loss Of Pay")

                            else:
                                self._init_clock(extraction_dt)
                            op_data["clock_details"] = op
                    if len(op.keys()) > 0:
                        results[f'{extraction_dt}'].append(op_data)

                # if op.exists():
                #     results[f'{extraction_dt}'].extend(list(op))
                # del op
                # if params.get('actionStatus', None) is None:
                    # for obj in emp_qs.order_by("id").distinct("id"):
                    #     clock_qs = attendance_models.EmployeeCheckInOutDetails.objects.filter(
                    #         employee=obj,
                    #         date_of_checked_in=extraction_dt,
                    #     ).filter(q_filters)
                    #     if not clock_qs.exists():
                #             op = self.model.objects.filter(id=obj.id).annotate(
                #                     week_off=db_models.Value(week_off),
                #                     half_week_off=db_models.Value(half_week_off),
                #                 ).annotate(
                #                 clockDetails=db_models.functions.Cast(
                #                     db_models.Func(
                #                         db_models.Case(
                #                             db_models.When(db_models.Q(
                #                                     leaveshistory__start_date__lte=extraction_dt,
                #                                     leaveshistory__end_date__gte=extraction_dt,
                #                                     leaveshistory__status=leave_models.LeavesHistory.APPROVED,
                #                                     leaveshistory__is_penalty=False
                #                                 ), then=db_models.Value(f"{self._init_clock(extraction_dt, 'L')}".replace("'", '"')),
                #                             ),
                #                             db_models.When(db_models.Q(
                #                                     company__holidays__holiday_date=extraction_dt,
                #                                     company__holidays__is_deleted=False
                #                                 ), then=db_models.Value(f"{self._init_clock(extraction_dt, 'H')}".replace("'", '"'))
                #                             ),
                #                             db_models.When(
                #                                 week_off=True,
                #                                 then=db_models.Value(f"{self._init_clock(extraction_dt, 'WO')}".replace("'", '"'))
                #                             ),
                #                             default=db_models.Value(f'{self._init_clock(extraction_dt)}'.replace("'", '"')),
                #                             output_field=db_models.CharField(),
                #                         ),
                #                         function='JSON'
                #                     ),
                #                     output_field=db_models.JSONField(),
                #                 ),
                #                 employee_details=db_models.expressions.Func(
                #                     db_models.Value('id'), 'id',
                #                     db_models.Value('date_of_join'), 'date_of_join',
                #                     db_models.Value('name'), db_models.functions.Concat(
                #                         db_models.F('first_name'), db_models.Value(' '), db_models.F('last_name'),
                #                         output_field=db_models.CharField()    
                #                     ),
                #                     db_models.Value('attendance_rules'), db_models.expressions.Func(
                #                         db_models.Value('name'), 'assignedattendancerules__attendance_rule__name',
                #                         db_models.Value('enableOverTime'), 'assignedattendancerules__attendance_rule__enable_over_time',
                #                         db_models.Value('orgInTime'), 'assignedattendancerules__attendance_rule__shift_in_time',
                #                         db_models.Value('orgOutTime'), 'assignedattendancerules__attendance_rule__shift_out_time',
                #                         db_models.Value('autoClockOut'), 'assignedattendancerules__attendance_rule__auto_clock_out',
                #                         function='jsonb_build_object',
                #                         output_field=db_models.JSONField()
                #                     ),
                #                     db_models.Value('workweek_rule'), db_models.expressions.Func(
                #                         db_models.Value('name'), 'employeeworkrulerelation__work_rule__name',
                #                         function='jsonb_build_object',
                #                         output_field=db_models.JSONField()
                #                     ),
                #                     db_models.Value('number'), db_models.F('work_details__employee_number'),
                #                     db_models.Value('department'), db_models.F('work_details__department__name'),
                #                     db_models.Value('sub_department'), db_models.F('work_details__sub_department__name'),
                #                     db_models.Value('designation'), db_models.F('work_details__designation__name'),
                #                     db_models.Value('work_location'), db_models.F('work_details__work_location'),
                #                     db_models.Value('employee_type'), db_models.Case(
                #                         db_models.When(work_details__employee_type__employee_type=10, then=db_models.Value("Full Time")),
                #                         db_models.When(work_details__employee_type__employee_type=20, then=db_models.Value("Part Time")),
                #                         db_models.When(work_details__employee_type__employee_type=30, then=db_models.Value("Intern")),
                #                         db_models.When(work_details__employee_type__employee_type=40, then=db_models.Value("On Contract")),
                #                         db_models.When(work_details__employee_type__employee_type=50, then=db_models.Value("Others")),
                #                         default=db_models.Value(""), output_field=db_models.CharField()
                #                     ),
                #                     db_models.Value('employee_status'), db_models.F('work_details__employee_status'),
                #                     db_models.Value('employee_grade'), db_models.F("work_details__employee_grade__grade"),
                #                     db_models.Value('reporting_manager'), ArrayAgg(
                #                         db_models.functions.Concat(
                #                             db_models.F('employee__manager__first_name'), db_models.Value(" "), db_models.F('employee__manager__last_name'),
                #                             output_field=db_models.CharField()   
                #                         ),
                #                         filter=db_models.Q(employee__isnull=False, employee__manager_type__manager_type=10, employee__is_deleted=False, employee__manager__work_details__employee_status='Active'),
                #                         distinct=True
                #                     ),
                #                     db_models.Value('leave_rules'), db_models.expressions.Func(
                #                         db_models.Value('name'), ArrayAgg('employeeleaverulerelation__leave_rule__name', distinct=True), 
                #                         # ArrayAgg('employeeleaverulerelation__leave_rule__name', distinct=True),
                #                         function='jsonb_build_object',
                #                         output_field=db_models.JSONField()
                #                     ),
                #                     function='jsonb_build_object',
                #                     output_field=db_models.JSONField()
                #                 )
                    
                #             ).values(
                #                 "clockDetails", "employee_details"
                #             )
                #             results[f'{extraction_dt}'].extend(list(op))
                #             del op
            if 'is_export' in request.query_params and request.query_params['is_export']:
                atten_df = pd.DataFrame()
                for date, employee_info_list in results.items():
                    date_df = pd.DataFrame(employee_info_list)
                    date_df['date'] = dt.datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
                    atten_df = pd.concat([atten_df, date_df], ignore_index=True)
                if atten_df.empty:
                    return Response(
                        error_response('No Data Found To Export', "No Data Found To Export", 404),
                        status=status.HTTP_404_NOT_FOUND
                    )
                atten_df = atten_df[['date', 'employee_details','clock_details']]
                atten_df = pd.concat([atten_df.drop(['employee_details'], axis=1), atten_df['employee_details'].apply(pd.Series)], axis=1)
                atten_df = pd.concat([atten_df.drop(['clock_details'], axis=1), atten_df['clock_details'].apply(pd.Series)], axis=1)
                atten_df['attendance_shift'] = atten_df.apply(lambda obj:obj['attendance_rules'].get('name') if obj['attendance_rules'].get('name') else '',axis=1)
                atten_df['outstanding_anomalies'] = atten_df.apply(lambda obj:obj['anamolies'].get('count') if obj['anamolies'] else '',axis=1)
                atten_df['reporting_manager'] = atten_df.apply(lambda obj:', '.join(obj['reporting_manager']) if obj['reporting_manager'] else '',axis=1)
                if 'overtime_hours' not in atten_df.columns:
                    atten_df['overtime_hours'] = ''
                print(atten_df.columns)
                
                if action_status and '20' in action_status:
                    atten_df = atten_df[['date','number', 'name','status','department','reporting_manager','work_location','time_in_format','time_out_format','checkin_location','attendance_shift',
                            'work_duration','break_duration','breaks','action_display','action_reason','reject_reason']]
                    atten_df['S.NO'] = range(1, len(atten_df) + 1)
                    atten_df.set_index('S.NO', inplace=True)  
                    atten_df = atten_df.rename(columns={'date':'Date','number': 'ID','name':'Employee Name','department':'Department','reporting_manager':'Reporting Manager',
                                            'work_location':'Work Location','time_in_format' : 'In Time','time_out_format':'Out Time','checkin_location':'Checkin Location','attendance_shift':'Attendance Shift',
                                            'work_duration':'Work Duration','break_duration':'Break Duration','breaks':'Breaks','action_display':'Action For',
                                            'action_reason':'AN Reason', 'reject_reason':'Reason','status':'Status'})
                else:
                    atten_df = atten_df[['date','number', 'name','status','department','reporting_manager','work_location','time_in_format','time_out_format','checkin_location','attendance_shift',
                            'work_duration','break_duration','breaks','overtime_hours','outstanding_anomalies']]
                    atten_df['S.NO'] = range(1, len(atten_df) + 1)
                    atten_df.set_index('S.NO', inplace=True)  
                    atten_df = atten_df.rename(columns={'date':'Date','number': 'ID','name':'Employee Name','department':'Department','reporting_manager':'Reporting Manager',
                                            'work_location':'Work Location','time_in_format' : 'In Time','time_out_format':'Out Time','checkin_location':'Checkin Location','attendance_shift':'Attendance Shift',
                                            'work_duration':'Work Duration','break_duration':'Break Duration','breaks':'Breaks','overtime_hours':'Overtime Duration',
                                            'outstanding_anomalies':'Outstanding Anomalies', 'status':'Status'})
                file_name = f"export_attendance_logs_{timezone_now().date()}.xlsx"
                return excel_converter(atten_df,file_name)
            
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "Got error in attendance data fetch", 400),
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            success_response(
            {
                "next": next,
                "previous": previous,
                "count": count,
                "limit": limit,
                "currentPage": page,
                "totalPages": totalPages,
                "results": dict(results.items()),
                # "verve":f"Data Access Confined to: {from_date.strftime('%d-%m-%Y')} to {to_date.strftime('%d-%m-%Y')}"
            }    
            , "Succefully fetch attendance data", 200),
            status=status.HTTP_200_OK
        )

class AttendanceRulesAPIViewV2(APIView):
    model = attendance_models.AttendanceRules
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        try:
            MultitenantSetup().create_to_connection(request)
            company_id = kwargs.get("company_id")
            params = request.query_params
            q_filters = db_models.Q(company_id=company_id, is_deleted=False)
            
            if 'search_filter' in params:
                q_filters &= (
                    db_models.Q(name__icontains=search_filter_decode(params.get("search_filter"))) | 
                    db_models.Q(attendance_id__employee__user__username__icontains=search_filter_decode(params.get("search_filter")))
                )
            paginator = self.pagination_class()
            qs = self.model.objects.filter(q_filters).annotate(
                authorName = db_models.F('created_by__username'),
                no_of_employees=db_models.Count(
                    'attendance_id',
                    filter=db_models.Q(
                        attendance_id__employee__work_details__employee_status='Active',
                        attendance_id__is_deleted=False
                    ),
                    distinct=True
                ),
                attendance_settings=db_models.expressions.Func(
                    db_models.Value('attendance_input_cycle_from'), 'company__attendancerulesettings__attendance_input_cycle_from',
                    db_models.Value('attendance_input_cycle_to'), 'company__attendancerulesettings__attendance_input_cycle_to',
                    function='jsonb_build_object',
                    output_field=db_models.JSONField()
                ),
                penalty_rules_details=db_models.expressions.Func(
                        db_models.Value("id"), "penalty_rules__id",
                        db_models.Value("attendance_rule"), "penalty_rules__attendance_rule",
                        db_models.Value("in_time"), "penalty_rules__in_time",
                        db_models.Value("late_coming_allowed"), "penalty_rules__late_coming_allowed",
                        db_models.Value("in_penalty_interval"), "penalty_rules__in_penalty_interval",
                        db_models.Value("in_penalty"), "penalty_rules__in_penalty",
                        db_models.Value("in_leave_deduction"), "penalty_rules__in_leave_deduction",
                        db_models.Value("out_time"), "penalty_rules__out_time",
                        db_models.Value("early_leaving_allowed"), "penalty_rules__early_leaving_allowed",
                        db_models.Value("out_penalty_interval"), "penalty_rules__out_penalty_interval",
                        db_models.Value("out_penalty"), "penalty_rules__out_penalty",
                        db_models.Value("out_leave_deduction"), "penalty_rules__out_leave_deduction",
                        db_models.Value("work_duration"), "penalty_rules__work_duration",
                        db_models.Value("shortfall_in_wd_allowed"), "penalty_rules__shortfall_in_wd_allowed",
                        db_models.Value("work_penalty_interval"), "penalty_rules__work_penalty_interval",
                        db_models.Value("work_penalty"), "penalty_rules__work_penalty",
                        db_models.Value("work_leave_deduction"), "penalty_rules__work_leave_deduction",
                        db_models.Value("outstanding_breaks_penalty"), "penalty_rules__outstanding_breaks_penalty",
                        db_models.Value("excess_breaks_allowed"), "penalty_rules__excess_breaks_allowed",
                        db_models.Value("break_penalty_interval"), "penalty_rules__break_penalty_interval",
                        db_models.Value("break_penalty"), "penalty_rules__break_penalty",
                        db_models.Value("break_leave_deduction"), "penalty_rules__break_leave_deduction",
                        function='jsonb_build_object',
                        output_field=db_models.JSONField(),
                    )
            ).values(
                "id", "company", "name", "description", "authorName", "shift_in_time", "shift_out_time", "auto_deduction",
                "grace_in_time", "grace_out_time", "full_day_work_duration", "half_day_work_duration", "max_break_duration",
                "max_breaks", "auto_clock_out", "is_default", "effective_date", "created_at", "enable_over_time", 
                "enable_attendance_selfie", "enable_geo_fencing", "location_address", "distance", "longitude", "latitude",
                "is_deleted", "enable_comp_off", "enable_penalty_rules", "enable_anomaly_tracing", "no_of_employees", 
                "penalty_rules_details", "attendance_settings", "comp_off_full_day_work_duration", "comp_off_half_day_work_duration",
                "minimum_hours_to_consider_ot", "selected_time_zone"
            )
            page = paginator.paginate_queryset(list(qs), request)
            MultitenantSetup().go_to_old_connection(request)
            return Response(
                success_response(paginator.get_paginated_response(page), "Successfully fetched Company Attendance Rules", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            MultitenantSetup().go_to_old_connection(request)
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing Went wrong", 400),
                status=status.HTTP_400_BAD_REQUEST
            )

class AttendanceDetailAPIViewV2(APIView):
    model = attendance_models.AttendanceRules
    
    def get(self, request, *args, **kwargs):
        try:
            id = kwargs.get("id")
            q_filters = db_models.Q(id=id, is_deleted=False)
            qs = self.model.objects.filter(q_filters).annotate(
                no_of_employees=db_models.Count(
                    'attendance_id',
                    filter=db_models.Q(
                        attendance_id__employee__work_details__employee_status='Active',
                        attendance_id__is_deleted=False
                    ),
                    distinct=True
                ),
                attendance_settings=db_models.expressions.Func(
                    db_models.Value('attendance_input_cycle_from'), 'company__attendancerulesettings__attendance_input_cycle_from',
                    db_models.Value('attendance_input_cycle_to'), 'company__attendancerulesettings__attendance_input_cycle_to',
                    function='jsonb_build_object',
                    output_field=db_models.JSONField()
                ),
                penalty_rules_details=db_models.expressions.Func(
                        db_models.Value("id"), "penalty_rules__id",
                        db_models.Value("attendance_rule"), "penalty_rules__attendance_rule",
                        db_models.Value("in_time"), "penalty_rules__in_time",
                        db_models.Value("late_coming_allowed"), "penalty_rules__late_coming_allowed",
                        db_models.Value("in_penalty_interval"), "penalty_rules__in_penalty_interval",
                        db_models.Value("in_penalty"), "penalty_rules__in_penalty",
                        db_models.Value("in_leave_deduction"), "penalty_rules__in_leave_deduction",
                        db_models.Value("out_time"), "penalty_rules__out_time",
                        db_models.Value("early_leaving_allowed"), "penalty_rules__early_leaving_allowed",
                        db_models.Value("out_penalty_interval"), "penalty_rules__out_penalty_interval",
                        db_models.Value("out_penalty"), "penalty_rules__out_penalty",
                        db_models.Value("out_leave_deduction"), "penalty_rules__out_leave_deduction",
                        # db_models.Value("out_leave_deduction"), db_models.Case(
                        #     db_models.When(penalty_rules__in_leave_deduction__len__gt=0, then=db_models.F("penalty_rules__in_leave_deduction")),
                        #     default=db_models.Value([]), output_field=db_models.JSONField()    
                        # ),
                        db_models.Value("work_duration"), "penalty_rules__work_duration",
                        db_models.Value("shortfall_in_wd_allowed"), "penalty_rules__shortfall_in_wd_allowed",
                        db_models.Value("work_penalty_interval"), "penalty_rules__work_penalty_interval",
                        db_models.Value("work_penalty"), "penalty_rules__work_penalty",
                        db_models.Value("work_leave_deduction"), "penalty_rules__work_leave_deduction",
                        db_models.Value("outstanding_breaks_penalty"), "penalty_rules__outstanding_breaks_penalty",
                        db_models.Value("excess_breaks_allowed"), "penalty_rules__excess_breaks_allowed",
                        db_models.Value("break_penalty_interval"), "penalty_rules__break_penalty_interval",
                        db_models.Value("break_penalty"), "penalty_rules__break_penalty",
                        db_models.Value("break_leave_deduction"), "penalty_rules__break_leave_deduction",
                        function='jsonb_build_object',
                        output_field=db_models.JSONField(),
                    )
            ).values(
                "id", "company", "name", "description", "shift_in_time", "shift_out_time", "auto_deduction",
                "grace_in_time", "grace_out_time", "full_day_work_duration", "half_day_work_duration", "max_break_duration",
                "max_breaks", "auto_clock_out", "is_default", "effective_date", "created_at", "enable_over_time", 
                "enable_attendance_selfie", "enable_geo_fencing", "location_address", "distance", "longitude", "latitude",
                "is_deleted", "enable_comp_off", "enable_penalty_rules", "enable_anomaly_tracing", "no_of_employees", 
                "penalty_rules_details", "attendance_settings", "comp_off_full_day_work_duration", "comp_off_half_day_work_duration",
                "minimum_hours_to_consider_ot", "selected_time_zone"
            )
            
            return Response(
                success_response(qs.first(), "Successfully fetched Attendance Rule Data", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing Went wrong", 400),
                status=status.HTTP_400_BAD_REQUEST
            )


class EmployeeAttendanceRuleRelationRetrieveViewV2(APIView):
    model = directory_models.Employee
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        try:
            company_id = kwargs.get("company_id")
            params = request.query_params
            paginator = self.pagination_class()
            q_filters = db_models.Q(company_id=company_id, work_details__employee_status__in=['Active', 'YetToJoin'])
            if "search_filter" in params:
                q_filters &= (
                    db_models.Q(official_email__icontains=search_filter_decode(params.get("search_filter"))) |
                    db_models.Q(user__username__icontains=search_filter_decode(params.get("search_filter"))) |
                    db_models.Q(work_details__employee_number__icontains = search_filter_decode(params.get("search_filter")))
                )
            qs = self.model.objects.filter(
                q_filters
            ).annotate(
                attendance_rule_data=db_models.expressions.Func(
                    db_models.Value("name"), "assignedattendancerules__attendance_rule__name",
                    db_models.Value("rel_id"), "assignedattendancerules__id",
                    db_models.Value("work_rule_id"), "assignedattendancerules__attendance_rule_id",
                    db_models.Value("effective_date"), "assignedattendancerules__effective_date",
                    function="jsonb_build_object",
                    output_field=db_models.JSONField()
                ),
                employee_data=db_models.expressions.Func(
                    db_models.Value('id'), "id",
                    db_models.Value('name'), 'user__username',
                    db_models.Value('emp_id'), "work_details__employee_number",
                    db_models.Value('department'), "work_details__department__name",
                    db_models.Value('sub_department'), "work_details__sub_department__name",
                    db_models.Value('designation'), "work_details__designation__name",
                    db_models.Value('location'), "work_details__work_location",
                    db_models.Value('date_of_join'), "date_of_join",
                    db_models.Value('type'), db_models.Case(
                        *[db_models.When(work_details__employee_type__employee_type=i[0], then=db_models.Value(i[1])) for i in directory_models.EmployeeTypes.EMPLOYEE_TYPE_CHOICES],
                            default=db_models.Value(""), output_field=db_models.CharField()
                    ),
                    function="jsonb_build_object",
                    output_field=db_models.JSONField()
                ),
                reporting_manager=db_models.expressions.Func(
                    db_models.Value("name"), ArrayAgg(
                        db_models.functions.Concat(
                            db_models.F('employee__manager__first_name'), db_models.Value(" "), db_models.F('employee__manager__last_name'),
                            output_field=db_models.CharField()   
                        ),
                        filter=db_models.Q(employee__isnull=False, employee__manager_type__manager_type=10, employee__is_deleted=False, employee__manager__work_details__employee_status='Active'),
                        distinct=True
                    ),
                    function="jsonb_build_object",
                    output_field=db_models.JSONField()
                )
            ).values(
                "attendance_rule_data", "employee_data", "reporting_manager"
            )
            page = paginator.paginate_queryset(qs, request)
            return Response(
                    success_response(paginator.get_paginated_response(page), "Successfully fetched Employee Assigned attendance data", 200),
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing Went wrong", 400),
                status=status.HTTP_400_BAD_REQUEST
            )


class EmpAttendanceRuleAPIViewV2(APIView):
    model = attendance_models.AssignedAttendanceRules
    
    def get(self, request, *args, **kwargs):
        try:
            employee_id = self.kwargs.get("employee_id")
            q_filters = db_models.Q(employee__id=employee_id, is_deleted=False)
            qs = self.model.objects.filter(q_filters).annotate(
                attendance_rule_data=db_models.expressions.Func(
                    db_models.Value("id"), "attendance_rule__id",
                    db_models.Value("company"), "attendance_rule__company",
                    db_models.Value("name"), "attendance_rule__name",
                    db_models.Value("no_of_employees"), db_models.Count(
                        'attendance_rule__attendance_id',
                        filter=db_models.Q(
                            attendance_rule__attendance_id__employee__work_details__employee_status='Active',
                            attendance_rule__attendance_id__is_deleted=False
                        ),
                        distinct=True
                    ),
                    db_models.Value("description"), "attendance_rule__description",
                    db_models.Value("shift_in_time"), "attendance_rule__shift_in_time",
                    db_models.Value("shift_out_time"), "attendance_rule__shift_out_time",
                    db_models.Value("auto_deduction"), "attendance_rule__auto_deduction",
                    db_models.Value("grace_in_time"), "attendance_rule__grace_in_time",
                    db_models.Value("grace_out_time"), "attendance_rule__grace_out_time",
                    db_models.Value("full_day_work_duration"), "attendance_rule__full_day_work_duration",
                    db_models.Value("half_day_work_duration"), "attendance_rule__half_day_work_duration",
                    db_models.Value("max_break_duration"), "attendance_rule__max_break_duration",
                    db_models.Value("max_breaks"), "attendance_rule__max_breaks",
                    db_models.Value("auto_clock_out"), "attendance_rule__auto_clock_out",
                    db_models.Value("is_default"), "attendance_rule__is_default",
                    db_models.Value("effective_date"), "attendance_rule__effective_date",
                    db_models.Value("created_at"), "attendance_rule__created_at",
                    db_models.Value("enable_over_time"), "attendance_rule__enable_over_time",
                    db_models.Value("enable_attendance_selfie"), "attendance_rule__enable_attendance_selfie",
                    db_models.Value("enable_geo_fencing"), "attendance_rule__enable_geo_fencing",
                    db_models.Value("location_address"), "attendance_rule__location_address",
                    db_models.Value("distance"), "attendance_rule__distance",
                    db_models.Value("longitude"), "attendance_rule__longitude",
                    db_models.Value("latitude"), "attendance_rule__latitude",
                    db_models.Value("is_deleted"), "attendance_rule__is_deleted",
                    db_models.Value("enable_comp_off"), "attendance_rule__enable_comp_off",
                    db_models.Value("enable_penalty_rules"), "attendance_rule__enable_penalty_rules",
                    db_models.Value("enable_anomaly_tracing"), "attendance_rule__enable_anomaly_tracing",
                    db_models.Value("penalty_rules"), "attendance_rule__penalty_rules",
                    function='jsonb_build_object',
                    output_field=db_models.JSONField()
                ),
                penalty_rule=db_models.expressions.Func(
                    db_models.Value("rel_id"), "attendance_rule__penalty_rules__id",
                    db_models.Value("in_time"), "attendance_rule__penalty_rules__in_time",
                    db_models.Value("late_coming_allowed"), "attendance_rule__penalty_rules__late_coming_allowed",
                    db_models.Value("in_penalty_interval"), "attendance_rule__penalty_rules__in_penalty_interval",
                    db_models.Value("in_penalty"), "attendance_rule__penalty_rules__in_penalty",
                    db_models.Value("in_leave_deduction"), "attendance_rule__penalty_rules__in_leave_deduction",
                    db_models.Value("out_time"), "attendance_rule__penalty_rules__out_time",
                    db_models.Value("early_leaving_allowed"), "attendance_rule__penalty_rules__early_leaving_allowed",
                    db_models.Value("out_penalty_interval"), "attendance_rule__penalty_rules__out_penalty_interval",
                    db_models.Value("out_penalty"), "attendance_rule__penalty_rules__out_penalty",
                    db_models.Value("out_leave_deduction"), "attendance_rule__penalty_rules__out_leave_deduction",
                    db_models.Value("work_duration"), "attendance_rule__penalty_rules__work_duration",
                    db_models.Value("shortfall_in_wd_allowed"), "attendance_rule__penalty_rules__shortfall_in_wd_allowed",
                    db_models.Value("work_penalty_interval"), "attendance_rule__penalty_rules__work_penalty_interval",
                    db_models.Value("work_penalty"), "attendance_rule__penalty_rules__work_penalty",
                    db_models.Value("work_leave_deduction"), "attendance_rule__penalty_rules__work_leave_deduction",
                    db_models.Value("outstanding_breaks_penalty"), "attendance_rule__penalty_rules__outstanding_breaks_penalty",
                    db_models.Value("excess_breaks_allowed"), "attendance_rule__penalty_rules__excess_breaks_allowed",
                    db_models.Value("break_penalty_interval"), "attendance_rule__penalty_rules__break_penalty_interval",
                    db_models.Value("break_penalty"), "attendance_rule__penalty_rules__break_penalty",
                    db_models.Value("break_leave_deduction"), "attendance_rule__penalty_rules__break_leave_deduction",
                    function='jsonb_build_object',
                    output_field=db_models.JSONField()
                )
            ).values(
                "id",
                "employee",
                "attendance_rule_data",
                "penalty_rule",
                "effective_date",
                "resend_reminder",
                "is_deleted",
            )
            return Response(
                success_response(qs, "Successhully Fetched Data", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(
                    f'{e} Error: {traceback.format_exc()}', "Some thing went wrong", 400
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
class AttendanceShiftsSetupAPIViewV2(APIView):

    model = attendance_models.AttendanceShiftsSetup
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
                "id","company","calendar_type","start_date","end_date","is_shiftsetup_updated","created_at"
            )
            page = paginator.paginate_queryset(data, request)
            return Response(
                    success_response(paginator.get_paginated_response(page), "Successfully fetched company shifts setup", 200),
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
                success_response("Company Shifts Setup Updated Successfully", "Company Shifts Setup Updated Successfully", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

class VgAttendanceLogsAPIViewV2(APIView):

    model = attendance_models.VgAttendanceLogs
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        data=request.data
        try:
            self.model.objects.create(
                employee_code = data.get("employee_code"),
                log_datetime = data.get("log_datetime"),
                log_date = data.get("log_date"),
                log_time = data.get("log_time"),
                direction = data.get("direction"),
                work_code = data.get("work_code"),
                device_short_name = data.get("device_short_name"),
                serial_number = data.get("serial_number"),
                verification_mode = data.get("verification_mode"),
                reserved_field_1 = data.get("reserved_field_1"),
                reserved_field_2 = data.get("reserved_field_2")
            )
            count = self.model.objects.all().count()
            return Response(
                {
                    "total_count":count,
                    "msg":"Employee Attendance Log created Successfully"
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"msg":str(e)},status=status.HTTP_400_BAD_REQUEST)


class GetAllTimeZoneDetails(APIView):
    permission_classes = (permissions.IsAuthenticated, )
    
    def get(self, request):
        
        # data = list(set(pytz.all_timezones))
        # data.sort()

        data = [  
                {"name": "(GMT -11:00) Midway Island, Samoa", "value": "US/Samoa"},
                {"name": "(GMT -10:00) Hawaii", "value": "US/Hawaii"},
                {"name": "(GMT -09:00) Alaska", "value": "US/Alaska"},
                {"name": "(GMT -09:00) Juneau", "value": "US/Alaska"},
                {"name": "(GMT -08:00) Vancouver", "value": "US/Pacific"},
                {"name": "(GMT -08:00) Pacific Time (US and Canada)", "value": "US/Pacific"},
                {"name": "(GMT -07:00) Edmonton", "value": "US/Mountain"},
                {"name": "(GMT -07:00) Mountain Time (US and Canada)", "value": "US/Mountain"},
                {"name": "(GMT -07:00) Arizona", "value": "US/Arizona"},
                {"name": "(GMT -07:00) Mazatlan", "value": "America/Mexico_City"},
                {"name": "(GMT -07:00) Yokon", "value": "America/Whitehorse"},
                {"name": "(GMT -06:00) Chihuahua", "value": "America/Chihuahua"},
                {"name": "(GMT -06:00) Winnipeg", "value": "America/Winnipeg"},
                {"name": "(GMT -06:00) Saskatchewan", "value": "America/Regina"},
                {"name": "(GMT -06:00) Central Time (US and Canada)", "value": "America/Chicago"},
                {"name": "(GMT -06:00) Mexico City", "value": "America/Mexico_City"},
                {"name": "(GMT -06:00) Guatemala", "value": "America/Guatemala"},
                {"name": "(GMT -06:00) El Salvador", "value": "America/El_Salvador"},
                {"name": "(GMT -06:00) Managua", "value": "America/Managua"},
                {"name": "(GMT -06:00) Costa Rica", "value": "America/Costa_Rica"},
                {"name": "(GMT -06:00) Tegucigalpa", "value": "America/Tegucigalpa"},
                {"name": "(GMT -06:00) Monterrey", "value": "America/Monterrey"},
                {"name": "(GMT -05:00) Montreal", "value": "America/Montreal"},
                {"name": "(GMT -05:00) Eastern Time (US and Canada)", "value": "America/New_York"},
                {"name": "(GMT -05:00) Indiana (East)", "value": "America/Indiana/Indianapolis"},
                {"name": "(GMT -05:00) Panama", "value": "America/Panama"},
                {"name": "(GMT -05:00) Bogota", "value": "America/Bogota"},
                {"name": "(GMT -05:00) Acre", "value": "America/Rio_Branco"},
                {"name": "(GMT -04:00) Halifax", "value": "America/Halifax"},
                {"name": "(GMT -04:00) Puerto Rico", "value": "America/Puerto_Rico"},
                {"name": "(GMT -04:00) Caracas", "value": "America/Caracas"},
                {"name": "(GMT -04:00) Atlantic Time (Canada)", "value": "America/Halifax"},
                {"name": "(GMT -04:00) La Paz", "value": "America/La_Paz"},
                {"name": "(GMT -04:00) Guyana", "value": "America/Guyana"},
                {"name": "(GMT -03:30) Newfoundland and Labrador", "value": "America/St_Johns"},
                {"name": "(GMT -03:00) Santiago", "value": "America/Santiago"},
                {"name": "(GMT -03:00) Montevideo", "value": "America/Montevideo"},
                {"name": "(GMT -03:00) Recife", "value": "America/Recife"},
                {"name": "(GMT -03:00) Buenos Aires, Georgetown", "value": "America/Argentina/Buenos_Aires"},
                {"name": "(GMT -03:00) Sao Paulo", "value": "America/Sao_Paulo"},
                {"name": "(GMT -02:00) Greenland", "value": "America/Godthab"},
                {"name": "(GMT -02:00) Fernando de Noronha", "value": "America/Noronha"},
                {"name": "(GMT -01:00) Azores", "value": "Atlantic/Azores"},
                {"name": "(GMT -01:00) Cape Verde Islands", "value": "Atlantic/Cape_Verde"},
                {"name": "(GMT +00:00) Universal Time UTC", "value": "UTC"},
                {"name": "(GMT +00:00) Greenwich Mean Time", "value": "GMT"},
                {"name": "(GMT +00:00) London", "value": "Europe/London"},
                {"name": "(GMT +00:00) Lisbon", "value": "Europe/Lisbon"},
                {"name": "(GMT +00:00) Nouakchott", "value": "Africa/Nouakchott"},
                {"name": "(GMT +01:00) Casablanca", "value": "Africa/Casablanca"},
                {"name": "(GMT +01:00) Ljubljana", "value": "Europe/Ljubljana"},
                {"name": "(GMT +01:00) Sarajevo", "value": "Europe/Sarajevo"},
                {"name": "(GMT +01:00) Oslo", "value": "Europe/Oslo"},
                {"name": "(GMT +01:00) Stockholm", "value": "Europe/Stockholm"},
                {"name": "(GMT +01:00) Copenhagen", "value": "Europe/Copenhagen"},
                {"name": "(GMT +01:00) Berlin", "value": "Europe/Berlin"},
                {"name": "(GMT +01:00) Amsterdam", "value": "Europe/Amsterdam"},
                {"name": "(GMT +01:00) Brussels", "value": "Europe/Brussels"},
                {"name": "(GMT +01:00) Luxembourg", "value": "Europe/Luxembourg"},
                {"name": "(GMT +01:00) Paris", "value": "Europe/Paris"},
                {"name": "(GMT +01:00) Zurich", "value": "Europe/Zurich"},
                {"name": "(GMT +01:00) Madrid", "value": "Europe/Madrid"},
                {"name": "(GMT +01:00) West Central Africa", "value": "Africa/Lagos"},
                {"name": "(GMT +01:00) Rome", "value": "Europe/Rome"},
                {"name": "(GMT +01:00) Tunis", "value": "Africa/Tunis"},
                {"name": "(GMT +01:00) Warsaw", "value": "Europe/Warsaw"},
                {"name": "(GMT +01:00) Prague Bratislava", "value": "Europe/Prague"},
                {"name": "(GMT +01:00) Vienna", "value": "Europe/Vienna"},
                {"name": "(GMT +01:00) Budapest", "value": "Europe/Budapest"},
                {"name": "(GMT +02:00) Helsinki", "value": "Europe/Helsinki"},
                {"name": "(GMT +02:00) Harare", "value": "Africa/Harare"},
                {"name": "(GMT +02:00) Pretoria", "value": "Africa/Johannesburg"},
                {"name": "(GMT +02:00) Sofia", "value": "Europe/Sofia"},
                {"name": "(GMT +02:00) Athens", "value": "Europe/Athens"},
                {"name": "(GMT +02:00) Nicosia", "value": "Asia/Nicosia"},
                {"name": "(GMT +02:00) Beirut", "value": "Asia/Beirut"},
                {"name": "(GMT +02:00) Tripoli", "value": "Africa/Tripoli"},
                {"name": "(GMT +02:00) Cairo", "value": "Africa/Cairo"},
                {"name": "(GMT +02:00) Johannesburg", "value": "Africa/Johannesburg"},
                {"name": "(GMT +02:00) Kyiv", "value": "Europe/Kiev"},
                {"name": "(GMT +02:00) Chisinau", "value": "Europe/Chisinau"},
                {"name": "(GMT +02:00) Khartoum", "value": "Africa/Khartoum"},
                {"name": "(GMT +03:00) Istanbul", "value": "Europe/Istanbul"},
                {"name": "(GMT +03:00) Damascus", "value": "Asia/Damascus"},
                {"name": "(GMT +03:00) Amman", "value": "Asia/Amman"},
                {"name": "(GMT +03:00) Moscow", "value": "Europe/Moscow"},
                {"name": "(GMT +03:00) Baghdad", "value": "Asia/Baghdad"},
                {"name": "(GMT +03:00) Kuwait", "value": "Asia/Kuwait"},
                {"name": "(GMT +03:00) Riyadh", "value": "Asia/Riyadh"},
                {"name": "(GMT +03:00) Qatar", "value": "Asia/Qatar"},
                {"name": "(GMT +03:00) Aden", "value": "Asia/Aden"},
                {"name": "(GMT +03:00) Djibouti", "value": "Africa/Djibouti"},
                {"name": "(GMT +03:00) Mogadishu", "value": "Africa/Mogadishu"},
                {"name": "(GMT +03:30) Minsk", "value": "Europe/Minsk"},
                {"name": "(GMT +03:30) Tehran", "value": "Asia/Tehran"},
                {"name": "(GMT +04:00) Dubai", "value": "Asia/Dubai"},
                {"name": "(GMT +04:00) Muscat", "value": "Asia/Muscat"},
                {"name": "(GMT +04:00) Baku, Tbilisi", "value": "Asia/Tbilisi"},
                {"name": "(GMT +04:30) Kabul", "value": "Asia/Kabul"},
                {"name": "(GMT +05:00) Yekaterinburg", "value": "Asia/Yekaterinburg"},
                {"name": "(GMT +05:00) Islamabad, Karachi, Tashkent", "value": "Asia/Karachi"},
                {"name": "(GMT +05:30) India (Kolkata)", "value": "Asia/Kolkata"},
                {"name": "(GMT +05:30) Colombo", "value": "Asia/Colombo"},
                {"name": "(GMT +05:45) Kathmandu", "value": "Asia/Kathmandu"},
                {"name": "(GMT +06:00) Almaty", "value": "Asia/Almaty"},
                {"name": "(GMT +06:00) Dhaka", "value": "Asia/Dhaka"},
                {"name": "(GMT +06:00) Astana", "value": "Asia/Almaty"},
                {"name": "(GMT +06:30) Yangon", "value": "Asia/Yangon"},
                {"name": "(GMT +07:00) Novosibirsk", "value": "Asia/Novosibirsk"},
                {"name": "(GMT +07:00) Bangkok", "value": "Asia/Bangkok"},
                {"name": "(GMT +07:00) Vietnam", "value": "Asia/Ho_Chi_Minh"},
                {"name": "(GMT +08:00) Irkutsk, Ulaanbaatar", "value": "Asia/Irkutsk"},
                {"name": "(GMT +08:00) Beijing, Shanghai", "value": "Asia/Shanghai"},
                {"name": "(GMT +08:00) Hong Kong", "value": "Asia/Hong_Kong"},
                {"name": "(GMT +08:00) Taipei", "value": "Asia/Taipei"},
                {"name": "(GMT +08:00) Singapore", "value": "Asia/Singapore"},
                {"name": "(GMT +09:00) Yakutsk", "value": "Asia/Yakutsk"},
                {"name": "(GMT +09:00) South Korea (Seoul)", "value": "Asia/Seoul"},
                {"name": "(GMT +09:00) Japan (Sapporo, Tokyo)", "value": "Asia/Tokyo"},
                {"name": "(GMT +09:30) Darwin", "value": "Australia/Darwin"},
                {"name": "(GMT +10:00) Guam, Port Moresby", "value": "Pacific/Port_Moresby"},
                {"name": "(GMT +10:30) Adelaide", "value": "Australia/Adelaide"},
                {"name": "(GMT +11:00) Australia (Sydney)", "value": "Australia/Sydney"},
                {"name": "(GMT +11:00) Magadan", "value": "Asia/Magadan"},
                {"name": "(GMT +11:00) Hobart", "value": "Australia/Hobart"},
                {"name": "(GMT +11:00) Solomon Islands", "value": "Pacific/Guadalcanal"},
                {"name": "(GMT +11:00) New Caledonia", "value": "Pacific/Noumea"},
                {"name": "(GMT +12:00) Kamchatka", "value": "Asia/Kamchatka"},
                {"name": "(GMT +12:00) Fiji Islands, Marshall Islands", "value": "Pacific/Fiji"},
                {"name": "(GMT +12:00) Independent State of Samoa", "value": "Pacific/Apia"},
                {"name": "(GMT +13:00) Auckland, Wellington", "value": "Pacific/Auckland"}
        ]

        return Response(
                    success_response(
                        data,  "Successfully Fetched Timezones", 200
                    ),
                    status=status.HTTP_200_OK
                )
class GetPaycycledates(APIView):
    model = directory_models.Employee
    def get(self, request, *args, **kwargs):
        params = request.query_params
        input_date = params.get('date','')
        date = dt.datetime.strptime(input_date, "%Y-%m-%d") if input_date else timezone_now()
        company_id = params.get('company_id',1)
        att_sett_data = attendance_models.AttendanceRuleSettings.objects.filter(company_id=company_id)
        pay_cycle_from_date=pay_cycle_to_date=current_payout_date = date
        if att_sett_data.exists():
            psc_from_date =  att_sett_data.first().attendance_input_cycle_from
            psc_to_date   =  att_sett_data.first().attendance_input_cycle_to
            pay_cycle_from_date,pay_cycle_to_date,current_payout_date = get_paycycle_dates(date,psc_from_date,psc_to_date)
        from_date = pay_cycle_from_date.date().strftime('%Y-%m-%d')
        to_date = pay_cycle_to_date.date().strftime('%Y-%m-%d')
        current_payout_date = current_payout_date.date().strftime('%Y-%m-%d')
        
        data = {
            "start_date" : from_date,
            "end_date" : to_date,
            "current_payout_date":current_payout_date
            
        }
        return Response(
                    success_response(
                        data,  "Successfully Fetched Paycycle Dates", 200
                    ),
                    status=status.HTTP_200_OK
                )
        
        
class ClockDetailsViewV3(APIView):
    model = directory_models.Employee
    pagination_class = CustomPagePagination

    def _init_clock(self, date_of_checked_in, status="A", deducted_from=""):
        return {
            "status": status,
            "date_of_checked_in": date_of_checked_in,
            "time_in": "-",
            "time_out": "-",
            'time_in_format': "-", 'time_out_format': "-",
            "extra_data": {},
            "punch_history": [],
            "work_duration": "-",
            "break_duration": "-",
            "breaks": "",
            "deducted_from": deducted_from,
            "anamolies": {"count": 0, "data": []},
            "checkin_location" : '-'
        }
    def custom_is_day_type(self, week_number, work_type, dt_input, employee):
        # print("employee:",employee)
        # employee = directory_models.Employee.objects.get(id=employee)
        work_rule_choice_obj = employee.employeeworkrulerelation_set.first()
        if not hasattr(employee.employeeworkrulerelation_set.first(), 'work_rule'):
            return False
        work_rule_choice_obj = work_rule_choice_obj.work_rule.work_rule_choices.filter(
            week_number=week_number)
        if not work_rule_choice_obj.exists():
            return False
        work_rule_choice_obj = work_rule_choice_obj.first()
        day = dt_input.strftime("%A")
        if day.lower() not in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            raise ValueError("Invalid day of the week")
        return getattr(work_rule_choice_obj, day.lower()) == work_type

    def get_manager_employees(self, man_id):
        emp_id = man_id
        print(man_id)
        my_list = []
        tag = True
        while tag:
            query = directory_models.EmployeeReportingManager.objects.filter(
                (
                    db_models.Q(is_deleted=False) & (
                        db_models.Q(manager__work_details__employee_number__in=emp_id) |
                        db_models.Q(multitenant_manager_emp_id__in=emp_id)
                    ) # & db_models.Q()
                )
            )

            if not query.exists():
                break
            my_list.extend(list(query.values_list('employee_id',flat=True)))
            emp_id = list(query.values_list('employee_id',flat=True))
        # print(                (
        #     db_models.Q(is_deleted=False) & (
        #         db_models.Q(manager__work_details__employee_number__in=emp_id)
        #         | db_models.Q(multitenant_manager_emp_id__in=emp_id) 
        #     )
        # ))
        return my_list
    
    def calling_init_clock(self, extraction_dt, c_status):
        if not c_status:
            return self._init_clock(extraction_dt, "A")
        if c_status == "L":
            return self._init_clock(extraction_dt, 'L')
        if c_status == "WO":
            return self._init_clock(extraction_dt, 'WO')
        if c_status == "H":
            return self._init_clock(extraction_dt, 'H')        
        if c_status == "A":
            return self._init_clock(extraction_dt, c_status)
        return self._init_clock(extraction_dt)
            
            
    
    def get(self, request, *args, **kwargs):
        params = request.query_params
        q_filters = db_models.Q()
        emp_filters = db_models.Q()
        today = timezone_now().date()
        from_date = params.get("fromDate", today)
        to_date = params.get("toDate", today)
        action_status = params.get("actionStatus", [])
        employee_status = params.get('employee_status','Active')
        emp_filters &= db_models.Q(work_details__employee_status__in=employee_status.split(','))
        logged_in_user_id = request.user.employee_details.first().work_details.employee_number
        logged_in_user_role = request.user.employee_details.first().roles.values_list('name', flat=True).first()
        MultitenantSetup().create_to_connection(request)
        # print(logged_in_user_id, logged_in_user_role)        
        if 'department_id' in params:
            emp_filters &= db_models.Q(work_details__department_id__in = params.get('department_id').split(','))
            q_filters &= db_models.Q(employee__work_details__department_id__in = params.get('department_id').split(','))
            
        if params.get("fromDate",'') and params.get("toDate",''):
            if (dt.datetime.strptime(to_date, "%Y-%m-%d") - dt.datetime.strptime(from_date, "%Y-%m-%d")).days > 31:
                message = "from date and to date cant be more than 31 days"
                return Response(
                    error_response(message,message),
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if 'search_filter' in params:
            emp_filters &= (
                db_models.Q(user__username__icontains=search_filter_decode(params.get("search_filter"))) |
                db_models.Q(work_details__employee_number__icontains = search_filter_decode(params.get("search_filter")))
                )
        if action_status:
            action_status = action_status.split(',')
        try:
            if 'id' in params:
                q_filters &= db_models.Q(employee_id__in=params.get('id').split(','))
                emp_filters &= db_models.Q(id__in=params.get('id').split(','))
            elif logged_in_user_role in ['TEAM LEAD']:
                check_ids = list(request.user.employee_details.first().employee_manager.filter(is_deleted=False).values_list('employee_id', flat=True))
                # check_ids.append(request.user.employee_details.first().id)
                emp_filters &= db_models.Q(
                    id__in=check_ids
                )
                q_filters &= db_models.Q(
                    employee_id__in=check_ids
                )
            elif logged_in_user_role in ["MANAGER"]:
                # logged_in_user_id = request.user.employee_details.first().id
                emp_ids = self.get_manager_employees([logged_in_user_id])
                # print("Coming Here", emp_ids)
                emp_filters &= db_models.Q(
                    id__in=emp_ids
                )
                q_filters &= db_models.Q(
                    employee_id__in=emp_ids
                )
            if "company" in params:
                q_filters &= db_models.Q(employee__company_id=params["company"])
                emp_filters &= db_models.Q(company_id=params["company"])
                company_id = params["company"]
            # print(11111,q_filters)
            qs = attendance_models.EmployeeCheckInOutDetails.objects.filter(q_filters)
            
            tz = attendance_models.AssignedAttendanceRules.objects.filter(employee__user_id=request.user.id).first()
            if tz:
                if tz.attendance_rule.selected_time_zone:
                    tzone = tz.attendance_rule.selected_time_zone
                else:
                    tzone = settings.TIME_ZONE
                today = timezone_now(tzone).date()
                # from_date = params.get("fromDate", today)
                # to_date = params.get("toDate", today)

                last_check_in = qs.filter(action_status = attendance_models.EmployeeCheckInOutDetails.OK).order_by('date_of_checked_in').last()
                
                if last_check_in:
                    if not last_check_in.time_out:
                        hour = tz.attendance_rule.shift_out_time.hour
                        minute = tz.attendance_rule.shift_out_time.minute
                    else:
                        last_timeout = localize_dt(last_check_in.time_out, tzone)
                        hour = last_timeout.hour
                        minute = last_timeout.minute
                    latest_time_out = dt.time(hour, minute)
                    
                    if tz.attendance_rule.shift_out_time > latest_time_out:
                        today = qs.order_by('date_of_checked_in').last().date_of_checked_in
            emp_qs = self.model.objects.filter(emp_filters)
            # print(emp_qs)
            if isinstance(from_date, str):
                from_date = strptime(from_date, fmt="%Y-%m-%d")

            if isinstance(to_date, str):
                to_date = strptime(to_date, fmt="%Y-%m-%d")

            q_filters &= db_models.Q(date_of_checked_in__range=[from_date, to_date])
            if action_status:
                q_filters &= db_models.Q(action_status__in=action_status)
                emp_filters &= db_models.Q(clock_details__action_status__in=action_status)

            if params.get('status'):
                q_filters &= db_models.Q(status=params.get('status'))
                emp_filters &= db_models.Q(clock_details__status=params.get('status'))
            company_config, _ = CompanyCustomizedConfigurations.objects.get_or_create(company_id=1)
            qs = qs.filter(q_filters)
            # print(qs)
            emp_qs = emp_qs.filter(emp_filters)
            dates = [from_date + dt.timedelta(i) for i in range(((to_date + dt.timedelta(1)) - from_date).days)]
            current_page = request.build_absolute_uri()
            next =  None
            previous = None
            page = 0
            count = len(dates)
            limit = 10
            currentPage = None
            totalPages = None
            dates.sort()
            # print("q_filters:",q_filters)
            if 'page' in params and 'page_size' in params:
                page = params.get("page", 1)
                if page == 'undefined':
                    page = 1
                page = int(page)
                page_size = int(params.get("page_size", 10))
                totalPages = divmod(count, page_size)[0] + 1 if divmod(count, page_size)[1] > 0 else divmod(count, page_size)[0]
                if page != totalPages:
                    next = current_page.replace(f'page={page}', f'page={page+1}')
                if page > 1:
                    previous = current_page.replace(f'page={page}', f'page={page-1}')
                dates = dates[(page-1)*page_size:(page*page_size)]
                if page > totalPages:
                    return Response(
                        {
                            "detail": "Invalid page."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            results = {}
            # print(qs)
            for extraction_dt in dates:
                # print(extraction_dt)
                week_number = get_month_weeks(extraction_dt)[extraction_dt.day]
                # print("week_number:",week_number)
                results[f'{extraction_dt}'] = []

                pp = extraction_dt.strftime("%A").lower()
                week_off_filter = {
                    "employee__employeeworkrulerelation__work_rule__work_rule_choices__week_number": week_number,
                        f'employee__employeeworkrulerelation__work_rule__work_rule_choices__{pp}': 0
                }
                half_week_off_filter = {
                    "employee__employeeworkrulerelation__work_rule__work_rule_choices__week_number": week_number,
                        f'employee__employeeworkrulerelation__work_rule__work_rule_choices__{pp}': 1
                }
                selected_time_zone = settings.TIME_ZONE
                op = qs.filter(date_of_checked_in=extraction_dt)
                existing_emps_clocks_ids = list(op.values_list('employee_id', flat=True).distinct())
                op = op.select_related(
                    'employee', 'employee__user', 'employee__work_details'
                ).prefetch_related(
                    'employee__leaveshistory_set', 'employee__company', 'employee__company__holidays_set',
                    "employee__employeeworkrulerelation_set", "employee__employeeworkrulerelation_set__work_rule",
                    "employee__employeeworkrulerelation_set__work_rule__work_rule_choices", "anamolies",
                    "employee__assignedattendancerules_set", "employee__assignedattendancerules_set__attendance_rule", 
                    "employee__employee", "employee__employee__manager", "employee__employee__manager_type",
                    "employee__employee__manager__work_details"
                ).annotate(
                    c_status= db_models.Case(
                        db_models.When(

                            db_models.Q(absent_period__isnull=False, action_status=40),                            

                            then=db_models.Value('A')

                        ),
                        db_models.When(

                            db_models.Q(action_status=20,action=10,status="A"),                            

                            then=db_models.Value('A')

                        ),
                        db_models.When(
                            db_models.Q(
                                date_of_checked_in=extraction_dt, #timezone_now().date(),
                                time_in__isnull=False,
                            ),
                            then=db_models.Value('P')
                        ),
                        db_models.When(
                            status="P",
                            then=db_models.Case(
                                db_models.When(
                                    (
                                        db_models.Q(
                                            employee__leaveshistory__start_date__lte=extraction_dt, 
                                            employee__leaveshistory__end_date__gte=extraction_dt, 
                                            employee__leaveshistory__status=leave_models.LeavesHistory.APPROVED, 
                                            employee__leaveshistory__is_penalty=False) & (
                                            db_models.Q(employee__leaveshistory__start_day_session__isnull=False) |
                                            db_models.Q(employee__leaveshistory__end_day_session__isnull=False)
                                        ) & (
                                            ~db_models.Q(**week_off_filter)
                                        )
                                    ),
                                    then=db_models.Value("HL")
                                ),
                                default=db_models.Value("P")
                            )
                        ),
                        db_models.When(
                            (
                                db_models.Q(
                                    employee__leaveshistory__start_date__lte=extraction_dt,
                                    employee__leaveshistory__end_date__gte=extraction_dt,
                                    employee__leaveshistory__status=leave_models.LeavesHistory.APPROVED, 
                                ) & (
                                    db_models.Q(
                                        employee__leaveshistory__is_penalty=True
                                    ) | db_models.Q(
                                        employee__leaveshistory__leave_rule__name="Loss Of Pay",
                                        employee__leaveshistory__is_penalty=False
                                    )
                                )
                            ),
                            then=db_models.Value("PN")
                        ),
                        db_models.When(
                            (
                                db_models.Q(
                                    employee__company__holidays__holiday_date=extraction_dt,
                                    employee__company__holidays__is_deleted=False
                                ) & db_models.Q(
                                    compoff_added=None
                                )
                            ),
                            then=db_models.Case(
                                db_models.When(
                                    db_models.Q(
                                        employee__leaveshistory__start_date__lte=extraction_dt,
                                        employee__leaveshistory__end_date__gte=extraction_dt, 
                                        employee__leaveshistory__status=leave_models.LeavesHistory.APPROVED, 
                                        employee__leaveshistory__leave_rule__holidays_between_leave=True
                                    ),
                                    then=db_models.Value("L")
                                ),
                                output_field=db_models.CharField(),
                                default=db_models.Value("H")
                            )
                        ),
                        db_models.When(
                            (
                                db_models.Q(
                                    employee__company__holidays__holiday_date=extraction_dt,
                                    employee__company__holidays__is_deleted=False
                                ) & db_models.Q(
                                    compoff_added__isnull=False
                                )     
                            ),
                            then=db_models.Value("CO")
                        ),
                        db_models.When(
                            (
                                db_models.Q(**half_week_off_filter) 
                            ),
                            then=db_models.Case(
                                db_models.When(
                                    (
                                    db_models.Q(anamolies__isnull=True) | db_models.Q(anamolies__status=10)
                                    ) & db_models.Q(overtime_hours=0),
                                    then=db_models.Value('P'), 
                                ),
                                db_models.When(
                                    (
                                    db_models.Q(anamolies__isnull=True) | db_models.Q(anamolies__status=10)
                                    ) & ~db_models.Q(overtime_hours=0),
                                    then=db_models.Value('OT'), 
                                ),
                                db_models.When((
                                    db_models.Q(
                                        anamolies__isnull=False
                                    ) & ~ db_models.Q(anamolies__status=10)
                                ), then=db_models.Value('AN')),
                                output_field=db_models.CharField(),
                                default=db_models.Value('P')
                            )
                        ),
                        db_models.When(
                            db_models.Q(**week_off_filter),
                            then=db_models.Case(
                                db_models.When(
                                    compoff_added=None, then=db_models.Case(
                                        db_models.When(
                                            db_models.Q(
                                                employee__leaveshistory__start_date__lte=extraction_dt,
                                                employee__leaveshistory__end_date__gte=extraction_dt,
                                                employee__leaveshistory__status=leave_models.LeavesHistory.APPROVED, 
                                                employee__leaveshistory__is_penalty=False,
                                                employee__leaveshistory__leave_rule__weekends_between_leave=True
                                            ),
                                            then=db_models.Value('L')
                                        ),
                                        default=db_models.Value('WO'),
                                        output_field=db_models.CharField()
                                    )
                                ),
                                db_models.When(compoff_added__isnull=False, then=db_models.Value('CO')),
                                default=db_models.Value('WO'),
                                output_field=db_models.CharField(),
                            )
                        ),
                        db_models.When(
                            db_models.Q(
                                employee__leaveshistory__start_date__lte=extraction_dt,
                                employee__leaveshistory__end_date__gte=extraction_dt,
                                employee__leaveshistory__status=leave_models.LeavesHistory.APPROVED,
                                employee__leaveshistory__is_penalty=False
                            ),
                            then=db_models.Value('L')
                        ),
                        db_models.When(
                            anamolies__status=10,
                            then=db_models.Case(
                                db_models.When(db_models.Q(
                                        anamolies__action__in=[10, 20],
                                        overtime_hours=0
                                    ), then=db_models.Value("P")
                                ),
                                db_models.When(
                                    anamolies__action=30,
                                    then=db_models.Value('L')
                                ),
                                db_models.When(
                                    anamolies__action=40,
                                    then=db_models.Value('LOP')
                                ),
                                default=db_models.Value('P'),
                                output_field=db_models.CharField()
                            )
                        ),
                        db_models.When(
                            ~db_models.Q(overtime_hours=0),
                            then=db_models.Value('OT')
                        ),
                        db_models.When(
                            (
                                db_models.Q(anamolies__status__in=[20, 30])
                            ),
                            then=db_models.Value('AN')
                        ),
                        db_models.When(
                            db_models.Q(anamolies__status=40),
                            then=db_models.Value('A')
                        ),
                        db_models.When(
                            (db_models.Q(anamolies__isnull=False) & ~db_models.Q(**week_off_filter)),
                            then=db_models.Value('AN')
                        ),
                        output_field=db_models.CharField(),
                        # default=db_models.Value('')
                    ),
                ).filter(c_status__isnull=False).annotate(
                    clock_details=db_models.expressions.Func(
                        db_models.Value("id"), "id",
                        db_models.Value("status"), "c_status",
                        db_models.Value("checkin_location"), db_models.F('checkin_location'),
                        # db_models.Value("deducted_from"), db_models.F('c_diducted_from'),
                        db_models.Value("date_of_checked_in"), "date_of_checked_in",
                        db_models.Value("time_in"), db_models.Case(
                            db_models.When(time_in__isnull=False, then=db_models.functions.Cast(TimestampToIST(db_models.F('time_in'), selected_time_zone), db_models.CharField())),
                            default=db_models.Value("-"), output_field=db_models.CharField()
                        ), 
                        db_models.Value("time_in_format"), TimestampToStr(TimestampToIST(db_models.F('time_in'), selected_time_zone)),
                        db_models.Value("latest_time_in"), TimestampToIST(db_models.F('latest_time_in'), selected_time_zone),
                        db_models.Value("time_out"), db_models.Case(
                            db_models.When(time_out__isnull=False, then=db_models.functions.Cast(TimestampToIST(db_models.F('time_out'), selected_time_zone), db_models.CharField())),
                            default=db_models.Value("-"), output_field=db_models.CharField()
                        ),
                        db_models.Value("time_out_format"), TimestampToStr(TimestampToIST(db_models.F('time_out'), selected_time_zone)),
                        db_models.Value("punch_history"), "extra_data",
                        db_models.Value("work_duration"), db_models.Case(
                            db_models.When(work_duration__isnull=False, then=db_models.F("work_duration")),
                            default=db_models.Value("-"), output_field=db_models.CharField()    
                        ),
                        db_models.Value("overtime_hours"), "overtime_hours",
                        db_models.Value("break_duration"), db_models.Case(
                            db_models.When(break_duration__isnull=False, then=db_models.F("break_duration")),
                            default=db_models.Value("-"), output_field=db_models.CharField()    
                        ),
                        db_models.Value("breaks"), "breaks",
                        # db_models.Value("employee_selfie"), "employee_selfie",
                        db_models.Value("action"), "action",
                        db_models.Value("action_reason"),"action_reason",
                        db_models.Value("action_display"), db_models.Case(
                            *[db_models.When(action=i[0], then=db_models.Value(i[1])) for i in attendance_models.EmployeeCheckInOutDetails.ACTION_CHOICES],
                            output_field=db_models.CharField(), default=db_models.Value("")
                        ),
                        db_models.Value("action_status"), "action_status",
                        db_models.Value("action_status_display"), db_models.Case(
                            *[db_models.When(action_status=i[0], then=db_models.Value(i[1])) for i in attendance_models.EmployeeCheckInOutDetails.ACTION_STATUS_CHOICES],
                            output_field=db_models.CharField(), default=db_models.Value("")
                        ),
                        # db_models.Value("extra_data"), "extra_data",
                        db_models.Value("anamolies"), db_models.expressions.Func(
                            db_models.Value("count"), db_models.Count('anamolies', distinct=True),
                            db_models.Value("data"), ArrayAgg(
                                db_models.expressions.Func(
                                    db_models.Value('id'), 'anamolies__id',
                                    db_models.Value('type'), db_models.Case(
                                        *[db_models.When(anamolies__choice=i[0], then=db_models.Value(i[1])) for i in attendance_models.AnamolyHistory.ANAMOLY_CHOICES],
                                        output_field=db_models.CharField(), default=db_models.Value("")
                                    ),
                                    db_models.Value('discrepancy'), 'anamolies__result',
                                    db_models.Value('action'), db_models.Case(
                                        *[db_models.When(action=i[0], then=db_models.Value(i[1])) for i in attendance_models.AnamolyHistory.ACTION_CHOICES],
                                        output_field=db_models.CharField(), default=db_models.Value("")
                                    ),
                                    db_models.Value('status'), db_models.Case(
                                        *[db_models.When(anamolies__status=i[0], then=db_models.Value(i[1])) for i in attendance_models.AnamolyHistory.STATUS_CHOICES],
                                        output_field=db_models.CharField(), default=db_models.Value("")
                                    ),
                                    function='jsonb_build_object',
                                    output_field=db_models.JSONField() 
                                ),
                                distinct=True,
                                ),
                            function='jsonb_build_object',
                            output_field=db_models.JSONField() 
                        ),
                        db_models.Value("approval_reason"), "approval_reason",
                        db_models.Value("reject_reason"), "reject_reason",
                        db_models.Value("is_logged_out"), "is_logged_out",
                        db_models.Value("auto_clocked_out"), db_models.Case(
                            db_models.When(
                                db_models.Q(time_out__isnull=False, is_logged_out=False,
                                            employee__assignedattendancerules__attendance_rule__auto_clock_out=True
                                ), then=db_models.Value("AC")
                            ), default=db_models.Value(""), output_field=db_models.CharField()
                        ),
                        function='jsonb_build_object',
                        output_field=db_models.JSONField()
                    ),
                    employee_details=db_models.expressions.Func(
                        db_models.Value('id'), 'employee_id',
                        db_models.Value('name'), 'employee__user__username',
                        db_models.Value('attendance_rules'), db_models.expressions.Func(
                            db_models.Value('name'), 'employee__assignedattendancerules__attendance_rule__name',
                            db_models.Value('enableOverTime'), 'employee__assignedattendancerules__attendance_rule__enable_over_time',
                            db_models.Value('orgInTime'), 'employee__assignedattendancerules__attendance_rule__shift_in_time',
                            db_models.Value('orgOutTime'), 'employee__assignedattendancerules__attendance_rule__shift_out_time',
                            db_models.Value('autoClockOut'), 'employee__assignedattendancerules__attendance_rule__auto_clock_out',
                            db_models.Value('selectedTimeZone'), 'employee__assignedattendancerules__attendance_rule__selected_time_zone',
                            function='jsonb_build_object',
                            output_field=db_models.JSONField()
                        ),
                        db_models.Value('number'), db_models.F('employee__work_details__employee_number'),
                        db_models.Value('department'), db_models.F('employee__work_details__department__name'),
                        db_models.Value('work_location'), db_models.F('employee__work_details__work_location'),
                        db_models.Value('employee_status'), db_models.F('employee__work_details__employee_status'),
                        db_models.Value('reporting_manager'), ArrayAgg(
                            db_models.functions.Concat(
                                db_models.F('employee__employee__manager__first_name'), db_models.Value(" "), db_models.F('employee__employee__manager__last_name'),
                                output_field=db_models.CharField()   
                            ),
                            filter=db_models.Q(employee__employee__isnull=False, employee__employee__manager_type__manager_type=10, employee__employee__is_deleted=False, employee__employee__manager__work_details__employee_status='Active'),
                            distinct=True
                        ),
                        function='jsonb_build_object',
                        output_field=db_models.JSONField()
                    )
                ).values(
                    "clock_details", "employee_details"
                )
                if op.exists():
                    results[f'{extraction_dt}'].extend(list(op))
                op_data = []
                if params.get('actionStatus', None) is None:
                    op_data = emp_qs.exclude(id__in=existing_emps_clocks_ids).select_related(
                        'company', 'work_details'
                    ).prefetch_related(
                        'leaveshistory_set', 'employeeworkrulerelation_set', 'company__holidays_set',
                        'assignedattendancerules_set', 'employee', 'employee__manager', "employeeworkrulerelation_set__work_rule",
                        "employeeworkrulerelation_set__work_rule__work_rule_choices", "assignedattendancerules_set__attendance_rule",
                        "employee", "employee__manager", "employee__manager_type", "employee__manager__work_details",
                        "clock_details"
                    ).annotate(week_off=db_models.Q(**{
                                                "employeeworkrulerelation__work_rule__work_rule_choices__week_number": week_number,
                                                f'employeeworkrulerelation__work_rule__work_rule_choices__{pp}': 0
                                            })).annotate(
                        c_status=db_models.Case(
                            db_models.When(
                                db_models.Q(**{
                                                "employeeworkrulerelation__work_rule__work_rule_choices__week_number": week_number,
                                                f'employeeworkrulerelation__work_rule__work_rule_choices__{pp}': 0
                                            }),
                                then=db_models.Case(
                                    db_models.When(
                                        db_models.Q(
                                            leaveshistory__start_date__lte=extraction_dt,
                                            leaveshistory__end_date__gte=extraction_dt,
                                            leaveshistory__status=leave_models.LeavesHistory.APPROVED, 
                                            leaveshistory__is_penalty=False,
                                            leaveshistory__leave_rule__weekends_between_leave=True
                                        ),
                                        then=db_models.Value('L1')
                                    ),
                                    default=db_models.Value('WO1'),
                                    output_field=db_models.CharField()
                                )
                            ),
                            db_models.When(
                                db_models.Q(
                                    leaveshistory__start_date__lte=extraction_dt,
                                    leaveshistory__end_date__gte=extraction_dt,
                                    leaveshistory__status=leave_models.LeavesHistory.APPROVED,
                                    leaveshistory__is_penalty=False
                                ), then=db_models.Case(
                                    db_models.When(
                                        (
                                            db_models.Q(   
                                                leaveshistory__start_date__lte=extraction_dt,
                                                leaveshistory__end_date__gte=extraction_dt,
                                                leaveshistory__status=leave_models.LeavesHistory.APPROVED,
                                                leaveshistory__is_penalty=False,
                                                leaveshistory__leave_rule__weekends_between_leave=False
                                            ) & 
                                            db_models.Q(**{
                                                "employeeworkrulerelation__work_rule__work_rule_choices__week_number": week_number,
                                                f'employeeworkrulerelation__work_rule__work_rule_choices__{pp}': 0
                                            })
                                        ),
                                        then=db_models.Value('WO2')
                                    ),
                                    db_models.When(
                                        (
                                            db_models.Q(
                                                leaveshistory__start_date__lte=extraction_dt,
                                                leaveshistory__end_date__gte=extraction_dt,
                                                leaveshistory__status=leave_models.LeavesHistory.APPROVED,
                                                leaveshistory__is_penalty=False,
                                                leaveshistory__leave_rule__holidays_between_leave=False
                                            ) & 
                                            db_models.Q(
                                                company__holidays__holiday_date=extraction_dt,
                                                company__holidays__is_deleted=False
                                            )
                                        ),
                                        then=db_models.Value('H1')                                        
                                    ),
                                    default=db_models.Value('L2'),
                                    output_field=db_models.CharField()
                                )
                            ),

                            db_models.When(
                                (db_models.Q(
                                    company__holidays__holiday_date=extraction_dt,
                                    company__holidays__is_deleted=False
                                ) & ~db_models.Q(
                                    leaveshistory__start_date__lte=extraction_dt,
                                    leaveshistory__end_date__gte=extraction_dt,
                                    leaveshistory__status=leave_models.LeavesHistory.APPROVED,
                                    leaveshistory__is_penalty=False
                                )), then=db_models.Value("H")
                            ),
                            db_models.When(
                                db_models.Q(
                                    leaveshistory__start_date__lte=extraction_dt,
                                    leaveshistory__end_date__gte=extraction_dt,
                                    leaveshistory__status=leave_models.LeavesHistory.APPROVED,
                                    leaveshistory__is_penalty=True
                                ), then=db_models.Value('A')
                            ),
                            # default=db_models.Value('A'),
                            output_field=db_models.CharField()
                        ),
                        employee_details=db_models.expressions.Func(
                            db_models.Value('id'), 'id',
                            db_models.Value('name'), 'user__username',
                            db_models.Value('attendance_rules'), db_models.expressions.Func(
                                db_models.Value('name'), 'assignedattendancerules__attendance_rule__name',
                                db_models.Value('enableOverTime'), 'assignedattendancerules__attendance_rule__enable_over_time',
                                db_models.Value('orgInTime'), 'assignedattendancerules__attendance_rule__shift_in_time',
                                db_models.Value('orgOutTime'), 'assignedattendancerules__attendance_rule__shift_out_time',
                                db_models.Value('autoClockOut'), 'assignedattendancerules__attendance_rule__auto_clock_out',
                                db_models.Value('selectedTimeZone'), 'assignedattendancerules__attendance_rule__selected_time_zone',
                                function='jsonb_build_object',
                                output_field=db_models.JSONField()
                            ),
                            db_models.Value('number'), db_models.F('work_details__employee_number'),
                            db_models.Value('department'), db_models.F('work_details__department__name'),
                            db_models.Value('work_location'), db_models.F('work_details__work_location'),
                            db_models.Value('employee_status'), db_models.F('work_details__employee_status'),
                            db_models.Value('reporting_manager'), ArrayAgg(
                                db_models.functions.Concat(
                                    db_models.F('employee__manager__first_name'), db_models.Value(" "), db_models.F('employee__manager__last_name'),
                                    output_field=db_models.CharField()   
                                ),
                                filter=db_models.Q(employee__isnull=False, employee__manager_type__manager_type=10, employee__is_deleted=False, employee__manager__work_details__employee_status='Active'),
                                distinct=True
                            ),
                            function='jsonb_build_object',
                            output_field=db_models.JSONField()
                        )
                    ).values('c_status', 'employee_details', 'id')
                    op_df = pd.DataFrame(op_data, columns=['c_status', 'employee_details', 'id'])
                    new_op =  op_df.groupby(['id']).aggregate({'c_status': list}).reset_index()
                    new_op.c_status = new_op.c_status.apply(lambda x: x[0] if len(set(x)) == 1  else [i for i in x if i is not None][0])
                    op_df.drop(columns=['c_status'], inplace=True)
                    op_df.drop_duplicates(['id'], inplace=True)
                    op_df = pd.merge(op_df, new_op, how='left', on=['id'])
                    op_df['clock_details'] = op_df.c_status.apply(lambda x: self.calling_init_clock(extraction_dt, x))
                    op_df.drop(columns=['c_status'], inplace=True)
                    results[f'{extraction_dt}'].extend(op_df.to_dict('records'))
                    del op_df
            if 'is_export' in request.query_params and request.query_params['is_export']:
                atten_df = pd.DataFrame()
                for date, employee_info_list in results.items():
                    date_df = pd.DataFrame(employee_info_list)
                    date_df['date'] = dt.datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
                    atten_df = pd.concat([atten_df, date_df], ignore_index=True)
                if atten_df.empty:
                    return Response(
                        error_response('No Data Found To Export', "No Data Found To Export", 404),
                        status=status.HTTP_404_NOT_FOUND
                    )
                atten_df = atten_df[['date', 'employee_details','clock_details']]
                atten_df = pd.concat([atten_df.drop(['employee_details'], axis=1), atten_df['employee_details'].apply(pd.Series)], axis=1)
                atten_df = pd.concat([atten_df.drop(['clock_details'], axis=1), atten_df['clock_details'].apply(pd.Series)], axis=1)
                atten_df['attendance_shift'] = atten_df.apply(lambda obj:obj['attendance_rules'].get('name') if obj['attendance_rules'].get('name') else '',axis=1)
                atten_df['outstanding_anomalies'] = atten_df.apply(lambda obj:obj['anamolies'].get('count') if obj['anamolies'] else '',axis=1)
                atten_df['reporting_manager'] = atten_df.apply(lambda obj:', '.join(obj['reporting_manager']) if obj['reporting_manager'] else '',axis=1)
                if 'overtime_hours' not in atten_df.columns:
                    atten_df['overtime_hours'] = ''

                
                if action_status and '20' in action_status:
                    atten_df = atten_df[['date','number', 'name','status','department','reporting_manager','work_location','time_in_format','time_out_format','checkin_location','attendance_shift',
                            'work_duration','break_duration','breaks','action_display','action_reason','reject_reason']]
                    atten_df['S.NO'] = range(1, len(atten_df) + 1)
                    atten_df.set_index('S.NO', inplace=True)  
                    atten_df = atten_df.rename(columns={'date':'Date','number': 'ID','name':'Employee Name','department':'Department','reporting_manager':'Reporting Manager',
                                            'work_location':'Work Location','time_in_format' : 'In Time','time_out_format':'Out Time','checkin_location':'Checkin Location','attendance_shift':'Attendance Shift',
                                            'work_duration':'Work Duration','break_duration':'Break Duration','breaks':'Breaks','action_display':'Action For',
                                            'action_reason':'AN Reason', 'reject_reason':'Reason','status':'Status'})
                else:
                    atten_df = atten_df[['date','number', 'name','status','department','reporting_manager','work_location','time_in_format','time_out_format','checkin_location','attendance_shift',
                            'work_duration','break_duration','breaks','overtime_hours','outstanding_anomalies']]
                    atten_df['S.NO'] = range(1, len(atten_df) + 1)
                    atten_df.set_index('S.NO', inplace=True)  
                    atten_df = atten_df.rename(columns={'date':'Date','number': 'ID','name':'Employee Name','department':'Department','reporting_manager':'Reporting Manager',
                                            'work_location':'Work Location','time_in_format' : 'In Time','time_out_format':'Out Time','checkin_location':'Checkin Location','attendance_shift':'Attendance Shift',
                                            'work_duration':'Work Duration','break_duration':'Break Duration','breaks':'Breaks','overtime_hours':'Overtime Duration',
                                            'outstanding_anomalies':'Outstanding Anomalies', 'status':'Status'})
                file_name = f"export_attendance_logs_{timezone_now().date()}.xlsx"
                MultitenantSetup().go_to_old_connection(request)
                return excel_converter(atten_df,file_name)
            
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "Got error in attendance data fetch", 400),
                status=status.HTTP_400_BAD_REQUEST
            )
        MultitenantSetup().go_to_old_connection(request)
        return Response(
            success_response(
            {
                "next": next,
                "previous": previous,
                "count": count,
                "limit": limit,
                "currentPage": page,
                "totalPages": totalPages,
                "results": dict(reversed(results.items())),
                # "verve":f"Data Access Confined to: {from_date.strftime('%d-%m-%Y')} to {to_date.strftime('%d-%m-%Y')}"
            }    
            , "Succefully fetch attendance data", 200),
            status=status.HTTP_200_OK
        )
        
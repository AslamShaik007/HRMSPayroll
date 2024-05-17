import pandas as pd
import traceback

from django.db import models as db_models
from django.contrib.postgres.aggregates import ArrayAgg

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import success_response, error_response, get_month_weeks, timezone_now, TimestampToStr

from directory.models import Employee
from attendance.models import AttendanceRules, AssignedAttendanceRules, EmployeeCheckInOutDetails
from directory.models import EmployeeReportingManager
from leave.models import LeavesHistory,EmployeeLeaveRuleRelation
from attendance.models import AnamolyHistory, EmployeeMonthlyAttendanceRecords
from attendance.services import get_monthly_record_obj_month, fetch_attendace_rule_start_end_dates

class EmployeeClockDetailsView(APIView):
    model = Employee
    
    def get_working_days(self,data):
        if not data:
            return 0
        d_data = data[0]
        d_data.pop('week_number')
        my_list = list(d_data.values())
        return sum(1 if x == 2 else (0.5 if x == 1 else x) for x in my_list)
    
    def get(self,request):
        try:
            employee_id = request.user.employee_details.first().id
            query = Employee.objects.filter(id=employee_id).annotate(
                                    att_rule_name = db_models.F('assignedattendancerules__attendance_rule__name'),
                                    shift_in_time = TimestampToStr(db_models.F('assignedattendancerules__attendance_rule__shift_in_time')),
                                    shift_out_time = TimestampToStr(db_models.F('assignedattendancerules__attendance_rule__shift_out_time')),
                                    full_day = db_models.F('assignedattendancerules__attendance_rule__full_day_work_duration'),
                                    half_day = db_models.F('assignedattendancerules__attendance_rule__half_day_work_duration'),
                                    break_duration = db_models.expressions.Func(
                                                            db_models.Value('time'), ArrayAgg('clock_details__break_duration', filter=db_models.Q(clock_details__date_of_checked_in=timezone_now().date()), distinct=True),
                                                            function='jsonb_build_object',
                                                            output_field=db_models.JSONField()
                                                        ),
                                    work_week_details = ArrayAgg(
                                            db_models.expressions.Func(
                                                db_models.Value('monday'), "employeeworkrulerelation__work_rule__work_rule_choices__monday",
                                                db_models.Value('tuesday'), "employeeworkrulerelation__work_rule__work_rule_choices__tuesday",
                                                db_models.Value('wednesday'), "employeeworkrulerelation__work_rule__work_rule_choices__wednesday",
                                                db_models.Value('thursday'), "employeeworkrulerelation__work_rule__work_rule_choices__thursday",
                                                db_models.Value('friday'), "employeeworkrulerelation__work_rule__work_rule_choices__friday",
                                                db_models.Value('saturday'), "employeeworkrulerelation__work_rule__work_rule_choices__saturday",
                                                db_models.Value('sunday'), "employeeworkrulerelation__work_rule__work_rule_choices__sunday",
                                                db_models.Value('week_number'), "employeeworkrulerelation__work_rule__work_rule_choices__week_number",
                                                function="jsonb_build_object",
                                                output_field=db_models.JSONField()
                                            ),
                                                distinct=True,
                                                filter = db_models.Q(
                                                    employeeworkrulerelation__work_rule__work_rule_choices__week_number = get_month_weeks(timezone_now().date())[timezone_now().date().day])
                                            )
                                    ).values('att_rule_name','shift_in_time','shift_out_time','full_day','half_day','break_duration','work_week_details')
                                
            emp_clock_df = pd.DataFrame(query, columns=['att_rule_name','shift_in_time','shift_out_time','full_day','half_day','break_duration','work_week_details'])                    
                                
            if len(emp_clock_df) != 0 :
                emp_clock_df['no_of_working_days'] = emp_clock_df.apply(lambda obj : self.get_working_days(obj['work_week_details']), axis=1)
                emp_clock_df['break_duration'] = emp_clock_df.apply(lambda obj : obj['break_duration'].get('time')[0] if obj['break_duration'].get('time') else None, axis=1)
                
            return Response(
                success_response(emp_clock_df.to_dict('records'), "Successfully Fetched Employee Clock Data", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
            
class CompanyWorkShiftsAPiView(APIView):

    model = AttendanceRules
    def get(self, request, *args, **kwargs):
        try:
            user_info = request.user.employee_details.first()
            company_id = user_info.company_id
            employee_id = user_info.id
            role = request.user.employee_details.first().roles.values_list('name', flat=True).first()
            q_filters = db_models.Q(is_deleted=False)
            if role in ["ADMIN","MANAGER"]:
                q_filters &= db_models.Q(company_id=company_id)
            data = self.model.objects.filter(q_filters).annotate(
                employee_count=db_models.Count('attendance_id',filter=db_models.Q(attendance_id__employee__work_details__employee_status='Active',
                                                                                  attendance_id__is_deleted=False),
                                                                                  distinct=True)
                ).values("id","name","shift_in_time","shift_out_time","selected_time_zone","employee_count").order_by("id").filter(
                db_models.Q(shift_in_time__isnull=False)|db_models.Q(shift_out_time__isnull=False)
                )
            return Response(
                    success_response(data, "Successfully fetched Work Shifts data", 200),
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )

class EmployeeCheckinAndCheckoutDetails(APIView):
    model = Employee
    
    def get(self,request):
        try:
            today = timezone_now().date()
            user_info = request.user.employee_details.first()
            role = user_info.roles.values_list('name', flat=True)
            q_filter = db_models.Q(company_id=user_info.company_id, work_details__employee_status='Active',is_deleted=False)          
            
            if 'MANAGER' in role:
                emp_ids = list(EmployeeReportingManager.objects.filter(manager_id=user_info.id, is_deleted=False).values_list('employee_id',flat=True))
                q_filter &= db_models.Q(id__in=emp_ids)
            emp_info = self.model.objects.filter(q_filter)
            total_emp_count = emp_info.count()
            check_in_info = emp_info.aggregate(
                            check_in_count = db_models.Count('clock_details__id',
                                            filter = db_models.Q(clock_details__isnull=False,clock_details__date_of_checked_in = timezone_now().date()),distinct=True),
                            check_out_count = db_models.Count('clock_details__id',
                                            filter = db_models.Q(clock_details__isnull=False,clock_details__date_of_checked_in = timezone_now().date(),clock_details__is_logged_out = True),distinct=True),
                            leaves_count = db_models.Count('leaveshistory__id',
                                            filter=db_models.Q(leaveshistory__start_date__gte=today,leaveshistory__end_date__lte=today,leaveshistory__status=LeavesHistory.APPROVED),distinct=True)
                            )
            result = {
                'total_employee_count': total_emp_count,
                'check_in_count' :check_in_info.get('check_in_count',0),
                'check_out_count':check_in_info.get('check_out_count',0),
                'leaves_count' : check_in_info.get("leaves_count",0),
                'not_checkedin_count' :total_emp_count - check_in_info.get('check_in_count', 0) - check_in_info.get("leaves_count",0),
            }
            return Response(
                success_response(result, "Successfully Fetched Employee log in data", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
class ManagerAnomomoliesRequests(APIView):
    model = AnamolyHistory

    def get(self, request, *args, **kwargs):
        try:
            roles = request.user.employee_details.first().roles.values_list('name', flat=True).first()
            user_info = request.user.employee_details.first()
            employee_id = user_info.id
            q_filters = db_models.Q(
                status=AnamolyHistory.PROCESSING, is_deleted=False, clock__action_status=EmployeeCheckInOutDetails.PENDING
            )
    
            if 'MANAGER' in roles:
                emp_ids = EmployeeReportingManager.objects.filter(manager_id=employee_id, is_deleted=False).values_list('employee_id',flat=True)
                q_filters &= db_models.Q(clock__employee__in=emp_ids)
            query = self.model.objects.filter(q_filters).order_by('clock__employee_id', 'request_date').distinct('clock__employee_id', 'request_date').count()
            data = {'pending_anomolies_count':query}
            return Response(
                        success_response(data, "Successfully fetched anomolies requests", 200),
                        status=status.HTTP_200_OK
                    )        
        except Exception as e:
                return Response(
                    error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                    status=status.HTTP_400_BAD_REQUEST
            )

class MonthlyPenaltyDetails(APIView):
    model = EmployeeMonthlyAttendanceRecords
    
    def month_year_calc(self, today):
        at_sdate, at_e_date = fetch_attendace_rule_start_end_dates(1)
        month = get_monthly_record_obj_month(at_sdate, at_e_date, today)
        return month, today.year
    
    def get(self,request):
        try:
            today = timezone_now().date()
            user_info = request.user.employee_details.first()
            role = user_info.roles.values_list('name', flat=True)
            t_month, t_year = self.month_year_calc(today)
            q_filter = db_models.Q(employee__company_id=user_info.company_id, employee__work_details__employee_status='Active', 
                                   is_deleted=False, month=t_month, year=t_year, penalty_details__isnull=False)
            
            if 'MANAGER' in role:
                emp_ids = list(EmployeeReportingManager.objects.filter(manager_id=user_info.id, is_deleted=False).values_list('employee_id',flat=True))
                q_filter &= db_models.Q(employee_id__in=emp_ids)
            pen_query = EmployeeMonthlyAttendanceRecords.objects.filter(q_filter).values('penalty_details')
            tt_count = sum(d.get('no_of_days_deducted') for item in pen_query if item for a, b in item.items() for c, d in b.items() if 'no_of_days_deducted' in d)
            result = {"count":tt_count}
            return Response(
                success_response(result, "Successfully Fetched Monthly Penalty Details", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
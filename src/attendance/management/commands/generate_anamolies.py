from datetime import date, datetime
from typing import Any, Optional
import traceback
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from attendance.models import (
    AssignedAttendanceRules,
    AttendanceRules,
    EmployeeCheckInOutDetails,
    AnamolyHistory, EmployeeMonthlyAttendanceRecords
)
from attendance.services import Anamoly, calculate_work_time, get_monthly_record_obj_month, get_month_weeks, fetch_attendace_rule_start_end_dates
from core.utils import get_month_weeks, hrs_to_mins, mins_to_hrs, timezone_now, localize_dt
from leave.models import (
    EmployeeLeaveRuleRelation,
    EmployeeWorkRuleRelation,
    LeaveRules,
    WorkRuleChoices,
)
from leave.services import is_day_type
from leave import models as leave_models
from pss_calendar.models import Holidays
import decimal
from django.db import models as db_models
from directory.models import EmployeeWorkDetails, Employee
from HRMSApp.utils import Util
import pandas as pd
class Command(BaseCommand):
    """
    Command to generate anamolies

    AJAY, 24.03.2023
    """

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--commit",
            "-c",
            default=False,
            action="store_true",
            dest="commit",
            help="Commit into DB",
        )

        parser.add_argument(
            "--date",
            "-d",
            dest="anamoly_date",
            type=date,
            help="date to generate anamoly",
        )
        
        parser.add_argument(
            "--company_id",
            "-cid",
            dest="company_id",
            type=int,
            help="company to generate anamoly",
        )

    def handle_overtime(self, clock: EmployeeCheckInOutDetails, today, rule):
        """
        This function calculates overtime hours for an employee based on their work duration and work
        rules for the day.

        :param clock: The clock parameter is an instance of the EmployeeCheckInOutDetails model, which
        contains information about an employee's check-in and check-out time, work duration, and
        overtime hours
        :type clock: EmployeeCheckInOutDetails
        :param today: The "today" parameter is a date object representing the current date for which the
        overtime calculation is being done

        AJAY, 24.04.2023
        """
        minimum_hours_to_consider_ot = rule.minimum_hours_to_consider_ot
        ot_basic_mins = hrs_to_mins(minimum_hours_to_consider_ot.split(":")[0], minimum_hours_to_consider_ot.split(":")[1])
        work_duration = clock.work_duration.split(":")
        worked_mins = hrs_to_mins(work_duration[0],work_duration[1])
        expected_working_mins = 0
        choice = WorkRuleChoices.objects.filter(
            work_rule__in=EmployeeWorkRuleRelation.objects.filter(
                employee=clock.employee,
                effective_date__lte=today,
            ).values_list("work_rule", flat=True),
            week_number=get_month_weeks(today, need_week_number_only=True),
        ).first()
        if is_day_type(
            choice=choice,
            dt_input=today,
            work_type=WorkRuleChoices.HALF_DAY,
        ):
            expected_working_mins = hrs_to_mins(rule.half_day_work_duration.split(':')[0], rule.half_day_work_duration.split(':')[1])

        if is_day_type(
            choice=choice,
            dt_input=today,
            work_type=WorkRuleChoices.FULL_DAY,
        ):
            expected_working_mins = hrs_to_mins(rule.full_day_work_duration.split(':')[0], rule.full_day_work_duration.split(':')[1])

        if expected_working_mins and (worked_mins - expected_working_mins) >= ot_basic_mins:
            clock.overtime_hours = worked_mins - expected_working_mins
            clock.save()

            self.stdout.write(
                self.style.WARNING(
                    f"OT time calculation is done of the employee: {clock.employee.name} Date: {clock.date_of_checked_in} OT: {clock.overtime_hours}"
                )
            )

    def hanlde_compoff(self, clock, today):
        """
        This function calculates the Comp Off leave for an employee based on their work duration and
        work rules.

        :param clock: The "clock" parameter is an instance of a model representing an employee's
        clock-in and clock-out time for a particular day. It contains information such as the employee,
        the clock-in time, the clock-out time, and the duration of work for that day
        :param today: The parameter "today" is a date object representing the current date for which the
        comp off calculation is being done
        :return: It is not clear what is being returned as the function does not have a return
        statement. It may return None implicitly if none of the conditions in the function are met.

        AJAY, 24.03.2023
        """
        choice = WorkRuleChoices.objects.filter(
            work_rule__in=EmployeeWorkRuleRelation.objects.filter(
                employee=clock.employee,
                effective_date__lte=today,
            ).values_list("work_rule", flat=True),
            week_number=get_month_weeks(today, need_week_number_only=True),
        ).first()

        leave_relation = EmployeeLeaveRuleRelation.objects.filter(
            employee=clock.employee, leave_rule__name="Comp Off"
        ).first()
        
        attendance_relation = AssignedAttendanceRules.objects.filter(employee=clock.employee).first()

        if (not choice) or (not leave_relation):
            return


        work_duration = clock.work_duration.split(":")
        worked_mins = hrs_to_mins(work_duration[0],work_duration[1])
        # leave_rule: EmployeeLeaveRuleRelation = leave_relation.leave_rule
        half_day_work_duration = attendance_relation.attendance_rule.comp_off_half_day_work_duration.split(":")
        half_day_work = hrs_to_mins(half_day_work_duration[0], half_day_work_duration[1])
        full_day_work_duration = attendance_relation.attendance_rule.comp_off_full_day_work_duration.split(":")
        full_day_work = hrs_to_mins(full_day_work_duration[0], full_day_work_duration[1])

        if Holidays.objects.filter(
            holiday_date=today, company=clock.employee.company
        ).exists() or is_day_type(
            choice=choice,
            dt_input=today,
            work_type=WorkRuleChoices.WEEK_OFF,
        ):


            if worked_mins >= full_day_work:
                # leave_relation.remaining_leaves += decimal.Decimal(1)
                # leave_relation.earned_leaves += decimal.Decimal(1)
                clock.compoff_added = 'full_day'

            elif worked_mins >= half_day_work:
                # leave_relation.remaining_leaves += decimal.Decimal(0.5)
                # leave_relation.earned_leaves += decimal.Decimal(0.5)
                clock.compoff_added = 'half_day'
            clock.save()
            # if worked_mins >= (4 * 60) or worked_mins <= (8 * 60):
            #     leave_relation.remaining_leaves += 0.5
            #     leave_relation.earned_leaves += 0.5

            # if worked_mins >= (8 * 60):
            #     leave_relation.remaining_leaves += 1
            #     leave_relation.earned_leaves += 1

            # leave_relation.save(
            #     update_fields=["remaining_leaves", "earned_leaves"]
            # )
            self.stdout.write(
                self.style.WARNING(
                    f"Comp Off calculation is done of the employee: {clock.employee.name} Date: {clock.date_of_checked_in} Val: {clock.compoff_added}"
                )
            )

    # @transaction.atomic()
    def handle(self, *args: Any, **options: Any):
        sid = transaction.set_autocommit(autocommit=False)
        today = options.get("date", timezone_now())
        company_id = options.get('company_id')
        clock_filters = (
            
            db_models.Q(date_of_checked_in=today.date())
            # &
            # (
            #     db_models.Q(employee__assignedattendancerules__attendance_rule__enable_anomaly_tracing=True)|
            #     db_models.Q(employee__assignedattendancerules__attendance_rule__enable_comp_off=True)|
            #     db_models.Q(employee__assignedattendancerules__attendance_rule__enable_over_time=True)
            # )
        )
        clock_objs = EmployeeCheckInOutDetails.objects.filter(
            clock_filters
        )
        if company_id:
            clock_objs = clock_objs.filter(employee__company_id=company_id)
        anamoly = Anamoly()

        self.stdout.write(
            self.style.WARNING(f"No.of attendees found: {clock_objs.count()}")
        )
        for clock in clock_objs:
            try:
                rule_relation = AssignedAttendanceRules.objects.filter(
                    employee=clock.employee
                ).first()
                if not rule_relation:
                    continue

                rule = rule_relation.attendance_rule
                if not options.get("date"):
                    today = clock.date_of_checked_in
                #Auto Clock Out
                if rule.auto_clock_out and not clock.time_out and clock.time_in:
                    date_obj = clock.date_of_checked_in
                    datetime_obj = datetime.combine(date_obj, rule.shift_out_time)
                    last_in_date = localize_dt(dt=datetime_obj,tz=rule.selected_time_zone)
                    today = options.get("date", last_in_date)
                    clock.is_logged_out = False
                    calculate_work_time(clock, today)
                    history = clock.extra_data.get("punch_history", [])
                    last_clock_in_ip = next((entry['ip_address'] for entry in reversed(history) if entry['type'] == 'Clock In'), None)
                    history.append(
                        {
                        "time": rule.shift_out_time.strftime("%I:%M %p"),
                        "type": "Clock Out",
                        "ip_address": last_clock_in_ip,}
                    )
                    clock.extra_data["punch_history"] = history
                    clock.save()

                if rule.enable_over_time and clock.work_duration:
                    self.handle_overtime(clock, today, rule)

                if rule.enable_comp_off:
                    self.hanlde_compoff(clock, today)
                if rule.enable_anomaly_tracing and clock.compoff_added is None:
                    anamoly.handle(clock)
                if not rule.enable_anomaly_tracing:
                    # caluclate WD and compare fullday half day durations, if not matched create LOP either fullday or Half day
                    
                    work_duration = clock.work_duration.split(":")
                    worked_mins = hrs_to_mins(work_duration[0],work_duration[1])
                    expected_working_mins = 0
                    choice = WorkRuleChoices.objects.filter(
                        work_rule__in=EmployeeWorkRuleRelation.objects.filter(
                            employee=clock.employee,
                            effective_date__lte=today,
                        ).values_list("work_rule", flat=True),
                        week_number=get_month_weeks(today, need_week_number_only=True),
                    ).first()
                    half_day_mins = hrs_to_mins(rule.half_day_work_duration.split(':')[0], rule.half_day_work_duration.split(':')[1])
                    full_day_mins = hrs_to_mins(rule.full_day_work_duration.split(':')[0], rule.full_day_work_duration.split(':')[1])
                    if is_day_type(
                        choice=choice,
                        dt_input=today,
                        work_type=WorkRuleChoices.HALF_DAY,
                    ) or leave_models.LeavesHistory.objects.filter(
                        db_models.Q(start_date=clock.date_of_checked_in) & (db_models.Q(start_day_session__isnull=False) | db_models.Q(end_day_session__isnull=False))
                    ).exists():
                        expected_working_mins = half_day_mins
                    elif is_day_type(
                        choice=choice,
                        dt_input=today,
                        work_type=WorkRuleChoices.FULL_DAY,
                    ) or Holidays.objects.filter(holiday_date=clock.date_of_checked_in, is_deleted=False).exists() or leave_models.LeavesHistory.objects.filter(
                            db_models.Q(start_date=clock.date_of_checked_in) & (db_models.Q(start_day_session__isnull=False) | db_models.Q(end_day_session__isnull=False))
                        ).exists():
                        expected_working_mins = full_day_mins
                    
                    if worked_mins < expected_working_mins:
                        elr = leave_models.EmployeeLeaveRuleRelation.objects.filter(leave_rule__name="Loss Of Pay", leave_rule__is_deleted=False, employee=clock.employee).first()
                        if half_day_mins > worked_mins:
                            leave_models.LeavesHistory.objects.get_or_create(
                                employee=clock.employee,
                                leave_rule=elr.leave_rule,
                                start_date=clock.date_of_checked_in,
                                end_date=clock.date_of_checked_in,
                                reason="Half day Work duration not matched",
                                status=leave_models.LeavesHistory.APPROVED,
                                no_of_leaves_applied=1,
                            )
                        if half_day_mins <= worked_mins < full_day_mins:
                            leave_models.LeavesHistory.objects.get_or_create(
                                employee=clock.employee,
                                leave_rule=elr.leave_rule,
                                start_date=clock.date_of_checked_in,
                                end_date=clock.date_of_checked_in,
                                reason="Full day Work duration not matched",
                                status=leave_models.LeavesHistory.APPROVED,
                                no_of_leaves_applied=0.5,
                            )
                        self.stdout.write(
                            self.style.WARNING(
                                f"Lop Added: {clock.employee.name} Date: {clock.date_of_checked_in}"
                            )
                        )
                attendance_start_day, attendace_end_day = fetch_attendace_rule_start_end_dates(clock.employee.company_id)
                check_month = get_monthly_record_obj_month(attendance_start_day, attendace_end_day, clock.date_of_checked_in)
                month_record_obj, is_created = EmployeeMonthlyAttendanceRecords.objects.get_or_create(
                    employee_id=clock.employee.id, year=clock.date_of_checked_in.year, month=check_month
                )
                if rule.enable_anomaly_tracing and clock.anamolies.exists():
                    """Add anamolies to Month records AN"""
                    month_record_obj.attendance_data[
                        str(clock.date_of_checked_in)
                    ] = {
                        'breaks': clock.breaks,
                        'reason': '',
                        'status': 'AN',
                        'time_in': datetime.strftime(localize_dt(dt=clock.time_in,tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p"),
                        'time_out':datetime.strftime(localize_dt(dt=clock.time_out,tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p") if clock.time_out else None,
                        'anamolies': {'count': clock.anamolies.count()},
                        'present_count': 0,
                        'work_duration': clock.work_duration,
                        'break_duration': clock.break_duration,
                        'over_time_data': mins_to_hrs(clock.overtime_hours) ,
                        'approval_status': ''
                    }
                    month_record_obj.anamoly_count += 1
                    self.stdout.write(
                        f"Anamolies created for the employee: << {clock.employee} >>"
                    )
                elif rule.enable_over_time and not clock.anamolies.exists() and clock.overtime_hours > 0:
                    """Change Status Month Records to OT"""
                    month_record_obj.attendance_data[
                        str(clock.date_of_checked_in)
                    ] = {
                        'breaks': clock.breaks,
                        'reason': '',
                        'status': 'OT',
                        'time_in': datetime.strftime(localize_dt(dt=clock.time_in,tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p"),
                        'time_out':datetime.strftime(localize_dt(dt=clock.time_out,tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p") if clock.time_out else None,
                        'anamolies': {'count': 0},
                        'present_count': 1,
                        'work_duration': clock.work_duration,
                        'break_duration': clock.break_duration,
                        'over_time_data': mins_to_hrs(clock.overtime_hours) ,
                        'approval_status': ''
                    }
                    month_record_obj.present_days += 1

                elif rule.enable_comp_off and clock.compoff_added:
                    """Change Status Month records to CO"""
                    month_record_obj.attendance_data[
                        str(clock.date_of_checked_in)
                    ] = {
                        'breaks': clock.breaks,
                        'reason': '',
                        'status': 'CO',
                        'time_in': datetime.strftime(localize_dt(dt=clock.time_in, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p"),
                        'time_out':datetime.strftime(localize_dt(dt=clock.time_out, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p") if clock.time_out else None,
                        'anamolies': {'count': 0},
                        'present_count': 1,
                        'work_duration': clock.work_duration,
                        'break_duration': clock.break_duration,
                        'over_time_data': mins_to_hrs(clock.overtime_hours) ,
                        'approval_status': ''
                    }
                    month_record_obj.present_days += 1
                elif clock.employee.leaveshistory_set.filter(start_date=clock.date_of_checked_in):
                    lh_qs = clock.employee.leaveshistory_set.filter(start_date=clock.date_of_checked_in)
                    month_record_obj.attendance_data[
                        str(clock.date_of_checked_in)
                    ] = {
                        'breaks': clock.breaks,
                        'reason': lh_qs.first().reason,
                        'status': 'L',
                        'time_in': datetime.strftime(localize_dt(dt=clock.time_in,tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p"),
                        'time_out':datetime.strftime(localize_dt(dt=clock.time_out,tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p") if clock.time_out else None,
                        'anamolies': {'count': 0},
                        'present_count': 0,
                        'work_duration': clock.work_duration,
                        'break_duration': clock.break_duration,
                        'over_time_data': mins_to_hrs(clock.overtime_hours) ,
                        'approval_status': ''
                    }
                    if float(lh_qs.first().no_of_leaves_applied) < 1.0:
                        month_record_obj.present_days += 0.5
                        month_record_obj.lop_count += 0.5
                        month_record_obj.p_count = 0.5
                        month_record_obj.attendance_data[
                            str(clock.date_of_checked_in)
                        ]['present_count'] = 0.5
                        month_record_obj.penalty_details[str(clock.date_of_checked_in)] = {
                            "reason": lh_qs.first().reason,
                            "no_of_days_deducted": 0.5,
                            "deducted_from": lh_qs.last().leave_rule.name
                        }
                    else:
                        month_record_obj.lop_count += 1.0
                        month_record_obj.p_count = 0.5
                        
                        month_record_obj.penalty_details[str(clock.date_of_checked_in)] = {
                            "reason": lh_qs.first().reason,
                            "no_of_days_deducted": 1,
                            "deducted_from": lh_qs.last().leave_rule.name
                        }
                else:
                    month_record_obj.attendance_data[
                        str(clock.date_of_checked_in)
                    ] = {
                        'breaks': clock.breaks,
                        'reason': '',
                        'status': 'P',
                        'time_in': datetime.strftime(localize_dt(dt=clock.time_in,tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p"),
                        'time_out':datetime.strftime(localize_dt(dt=clock.time_out,tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p") if clock.time_out else None,
                        'anamolies': {'count': 0},
                        'present_count': 1,
                        'work_duration': clock.work_duration,
                        'break_duration': clock.break_duration,
                        'over_time_data': mins_to_hrs(clock.overtime_hours) ,
                        'approval_status': ''
                    }
                    month_record_obj.present_days += 1
                month_record_obj.save()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'EMP: {clock.employee.user.username} DATE: {clock.date_of_checked_in} ERROR: {e} AT: {traceback.format_exc()}'))

        if options["commit"]:
            transaction.commit()
            self.stdout.write(self.style.SUCCESS("Anamolies created successfully!"))
            self.stdout.write(self.style.SUCCESS("sending mails in progress!"))
            # Send email Notification to the employees
            today = timezone_now().date()
            data = AnamolyHistory.objects.filter(is_deleted=False,request_date = today).annotate(choice_types = db_models.Case(
                                   *[db_models.When(choice=i[0], then=db_models.Value(i[1])) for i in AnamolyHistory.ANAMOLY_CHOICES],
                                    default=db_models.Value(''), output_field=db_models.CharField())).values('choice_types','clock__employee__user__email',
                                                                                                            'clock__employee__company__company_name','clock__employee__user__username')
            dfr = pd.DataFrame(data,columns = ['clock__employee__user__username','clock__employee__user__email','clock__employee__company__company_name','choice_types'])
            if len(dfr) > 0:
                dfr = dfr.groupby('clock__employee__user__username').agg({'clock__employee__user__email':'first',
                                                                    'clock__employee__company__company_name':'first',
                                                                    'choice_types':list}).reset_index()
                dfr['choices'] = dfr.apply(lambda obj:', '.join(obj['choice_types']) if len(obj['choice_types']) else '',axis=1)
                
                data_dict = dfr.to_dict('records')
                for obj in data_dict:                    #send email to employee
                    try:
                        if obj['choices']:
                            employee_name = obj['clock__employee__user__username']
                            official_email = obj['clock__employee__user__email']
                            breach_reason = obj['choices']
                            company_name = obj['clock__employee__company__company_name']
                            # body=f'Hello Mr/Ms {employee_name},\n\n Anomalies were created for {today.strftime("%d-%m-%Y")} due to the {breach_reason}, Connect to your HRMS application to find more details.\n\nThanks,\n{company_name}'
                            body=f"Dear {employee_name},\n\nWe've identified an HRMS anomaly due to {breach_reason}. To ensure your attendance is accurate, please seek your reporting manager's approval before the pay cycle ends. Act promptly.\n\nThank you,\n{company_name}"                         
                            data={
                                'subject':'Anamoly Created',
                                'body':body,
                                'to_email':official_email
                            }
                            Util.send_email(data)
                    except Exception as e:
                        pass
                        # logger.warning(f"Error while sending email notificaton : {e}")

            self.stdout.write(self.style.SUCCESS("mails sent successfully!"))
        else:
            transaction.rollback(sid)
            self.stdout.write(self.style.WARNING("Dry Run!"))

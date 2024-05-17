from datetime import datetime
import traceback

from dateutil.relativedelta import relativedelta

from django.db import models as db_models
from django.conf import settings

from attendance.models import (
    AnamolyHistory,
    AssignedAttendanceRules,
    AttendanceRuleSettings,
    EmployeeCheckInOutDetails,
    AttendanceShiftsSetup,
)
from core.utils import hrs_to_mins, localize_dt, mins_to_hrs, get_month_weeks, timezone_now
from leave.services import is_day_type


def calculate_work_time(instance, today, save: bool = False):
    a_rule = instance.employee.assignedattendancerules_set.first().attendance_rule.selected_time_zone
    if not a_rule:
        a_rule = settings.TIME_ZONE
    if instance.time_out is None:
        instance.time_out = timezone_now(tz=a_rule)
    instance.work_duration = mins_to_hrs(
        (
            (localize_dt(instance.time_out, a_rule)  - localize_dt(instance.time_in, a_rule)).seconds //60) - (
                hrs_to_mins(instance.break_duration.split(":")[0], instance.break_duration.split(":")[1]
            ) if instance.break_duration else 0
        )
    )
    # instance.time_out = today
    # current_work_delta = relativedelta(
    #     today, (instance.latest_time_in or instance.time_in)
    # )
    # work_delta = current_work_delta
    # if _prev_work_delta := instance.work_duration:
    #     _hrs = int(_prev_work_delta.split(":")[0])
    #     _mins = int(_prev_work_delta.split(":")[1])
    #     work_delta = relativedelta(hours=_hrs, minutes=_mins) + relativedelta(
    #         hours=current_work_delta.hours,
    #         minutes=current_work_delta.minutes,
    #     )
    # instance.work_duration = f"{work_delta.hours}:{work_delta.minutes}"
    if save:
        instance.save()

def fetch_attendace_rule_start_end_dates(company_id):
    ars = AttendanceRuleSettings.objects.get(company_id=company_id)
    return ars.attendance_input_cycle_from, ars.attendance_input_cycle_to

def calculate_break_time(instance, today, save: bool = False):
    current_break_delta = relativedelta(today, instance.time_out)
    break_delta = current_break_delta
    if _prev_break_delta := instance.break_duration:
        _hrs = int(_prev_break_delta.split(":")[0])
        _mins = int(_prev_break_delta.split(":")[1])
        break_delta = relativedelta(hours=_hrs, minutes=_mins) + relativedelta(
            hours=current_break_delta.hours,
            minutes=current_break_delta.minutes,
        )
    instance.break_duration = f"{break_delta.hours}:{break_delta.minutes}"
    instance.breaks += 1
    instance.time_out = None
    if save:
        instance.save()

def custom_is_day_type(week_number, work_type, dt_input, employee):
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

def get_monthly_record_obj_month(attendance_input_cycle_from, attendance_input_cycle_to, applied_date):
    applied_month = applied_date.month
    if attendance_input_cycle_from > attendance_input_cycle_to:
        if applied_month == timezone_now().month and applied_date.day >= attendance_input_cycle_from:
            return applied_month
        elif applied_month == timezone_now().month and applied_date.day <= attendance_input_cycle_to:
            return applied_month - 1 if applied_month != 1 else 12
        elif applied_month > timezone_now().month and applied_date.day <= attendance_input_cycle_to:
            return applied_month - 1
        elif applied_month > timezone_now().month and applied_date.day >= attendance_input_cycle_from:
            return applied_month  if applied_month < 12 else 1
        elif applied_month <  timezone_now().month and applied_date.day >= attendance_input_cycle_from:
            return applied_month if applied_month != 12 else 1
        elif applied_month <  timezone_now().month and applied_date.day <= attendance_input_cycle_to:
            return applied_month - 1 if applied_month != 1 else 12
    elif attendance_input_cycle_from < attendance_input_cycle_to:
        return applied_month


class Anamoly:
    """
    Class to handle anamoly functionalities

    AJAY, 24.03.2023
    """

    def create_anamoly_hist(self, clock, choice, result):
        """
        It creates an AnamolyHistory object with the clock, request_date, choice, and result

        :param clock: This is the clock object that is being created
        :param choice: This is the choice that the user made
        :param result: This is the result of the anamoly. It's a boolean value
        :return: AnamolyHistory object

        AJAY, 24.03.2023
        """
        if AnamolyHistory.objects.filter(clock=clock,
                request_date=clock.date_of_checked_in,
                choice=choice):
            AnamolyHistory.objects.filter(clock=clock,
                                            request_date=clock.date_of_checked_in,
                                            choice=choice).update(result=result)
            return AnamolyHistory.objects.get(
                clock=clock,
                request_date=clock.date_of_checked_in,
                choice=choice,
                result=result,
            )
        return AnamolyHistory.objects.create(
            clock=clock,
            request_date=clock.date_of_checked_in,
            choice=choice,
            result=result,
        )

    def half_day_check(self, clock):
        week_number = get_month_weeks(clock.date_of_checked_in)[clock.date_of_checked_in.day]
        return is_day_type(
            clock.employee.employeeworkrulerelation_set.first().work_rule.work_rule_choices.get(week_number=week_number),
            1,
            clock.date_of_checked_in
        )

    def handle_work_duration(self, clock, rule):
        """
        Work duration anamoly functionality

        AJAY, 27.03.2023
        """
        # * FULL WORK ANAMOLY
        wd_chunks = [int(chunk) for chunk in clock.work_duration.split(":")]
        wd_minutes = hrs_to_mins(wd_chunks[0], wd_chunks[1])
        leave_qs = clock.employee.leaveshistory_set.filter(
            db_models.Q(start_date__lte=clock.date_of_checked_in, end_date__gte=clock.date_of_checked_in, status=10) &
            (db_models.Q(start_day_session__isnull=False)| db_models.Q(end_day_session__isnull=False))
        )
        is_half_day = self.half_day_check(clock)
        fwd_chunks = [int(chunk) for chunk in rule.full_day_work_duration.split(":")]
        fwd_minutes = hrs_to_mins(fwd_chunks[0], fwd_chunks[1])
        gp_in_chunks = rule.grace_in_time.split(":")
        gp_in_mins = hrs_to_mins(gp_in_chunks[0], gp_in_chunks[1])
        gp_out_chunks = rule.grace_out_time.split(":")
        gp_out_mins = hrs_to_mins(gp_out_chunks[0], gp_out_chunks[1])
        if fwd_minutes - (gp_in_mins+gp_out_mins) > wd_minutes:
            if not leave_qs and not is_half_day:
                self.create_anamoly_hist(
                    clock,
                    choice=AnamolyHistory.FULL_DAY_WD_BREACH,
                    result=mins_to_hrs(fwd_minutes - wd_minutes),
                )
            else:
                if (fwd_minutes - (gp_in_mins+gp_out_mins)) / 2 > wd_minutes:
                    self.create_anamoly_hist(
                        clock,
                        choice=AnamolyHistory.FULL_DAY_WD_BREACH,
                        result=mins_to_hrs(fwd_minutes - wd_minutes),
                    )
        # TODO: Implement Half Day , hint: Get work week to calculate for the half day
        # h_work_duration = rule.half_day_work_duration

        hwd_chunks = [int(chunk) for chunk in rule.half_day_work_duration.split(":")]
        hwd_minutes = hrs_to_mins(hwd_chunks[0], hwd_chunks[1])

        if hwd_minutes - (gp_in_mins+gp_out_mins) > wd_minutes:
            if not leave_qs and not is_half_day:
                self.create_anamoly_hist(
                    clock,
                    choice=AnamolyHistory.HALF_DAY_WD_BREACH,
                    result=mins_to_hrs(hwd_minutes - wd_minutes),
                )
            else:
                if (hwd_minutes - (gp_in_mins+gp_out_mins)) / 2 > wd_minutes:
                    self.create_anamoly_hist(
                        clock,
                        choice=AnamolyHistory.HALF_DAY_WD_BREACH,
                        result=mins_to_hrs(hwd_minutes - wd_minutes),
                    )

    def handle_break_duration(self, clock, rule):
        """
        handle break duration anamoly

        AJAY, 27.03.2023
        """
        max_bd_chunks = [int(chunk) for chunk in rule.max_break_duration.split(":")]
        max_bd_minutes = hrs_to_mins(max_bd_chunks[0], max_bd_chunks[1])

        bd_chunks = [int(chunk) for chunk in clock.break_duration.split(":")]
        bd_minutes = hrs_to_mins(bd_chunks[0], bd_chunks[1])

        if bd_minutes > max_bd_minutes:
            self.create_anamoly_hist(
                clock,
                choice=AnamolyHistory.MAX_BREAK_DURATION_BREACH,
                result=mins_to_hrs(bd_minutes - max_bd_minutes),
            )

        # * MAX BREAKS ANAMOLY
        max_breaks = rule.max_breaks if rule.max_breaks else 0
        breaks = clock.breaks
        if max_breaks < breaks:
            self.create_anamoly_hist(
                clock,
                choice=AnamolyHistory.MAX_TOTAL_BREAKS_BREACH,
                result=f"{breaks - max_breaks}",
            )

    def handle(
        self,
        clock: EmployeeCheckInOutDetails = None,
        rule: AttendanceRuleSettings = None,
    ):
        """
        Anamoly handler

        AJAY, 23.03.2023
        """
        if clock is None:
            return

        if rule is None:
            rule = (
                AssignedAttendanceRules.objects.filter(employee=clock.employee)
                .first()
                .attendance_rule
            )
        if not rule.enable_anomaly_tracing:
            return
        today = clock.time_in.date()

        # *  IN TIME ANAMOLY
        try:
            shift_in_time = localize_dt(dt=datetime.combine(today, rule.shift_in_time),tz=rule.selected_time_zone)
            clock_in = localize_dt(dt=clock.time_in,tz=rule.selected_time_zone)
            if clock.time_out is None:
                self.create_anamoly_hist(
                    clock,
                    choice=AnamolyHistory.OUT_TIME_BREACH,
                    result="0:0",
                )
                clock.status = "AN"
                clock.save(update_fields=["status"])
                return
                
            shift_out_time = localize_dt(dt=datetime.combine(today, rule.shift_out_time),tz=rule.selected_time_zone)
            clock_out = localize_dt(dt=clock.time_out,tz=rule.selected_time_zone)
            is_half_day = self.half_day_check(clock)
            if is_half_day:
                """
                Shift In and out times will be change
                """
                td = shift_out_time - shift_in_time
                shift_in_time = shift_in_time.replace(hour=shift_in_time.hour+((td.seconds//3600)//2),
                                                    minute=shift_in_time.minute+((td.seconds//60)//2))
                if shift_out_time.minute-((td.seconds//60)//2) > 0:
                    shift_out_time = shift_out_time.replace(hour=shift_out_time.hour-((td.seconds//3600)//2),
                                                        minute=shift_out_time.minute-((td.seconds//60)//2))
                else:
                    shift_out_time = shift_out_time.replace(hour=shift_out_time.hour-1-((td.seconds//3600)//2),
                                                        minute=60-shift_out_time.minute-((td.seconds//60)//2))
            diff = relativedelta(clock_in, shift_in_time)
            diff_mins = hrs_to_mins(diff.hours, diff.minutes)
            
            gp_chunks = rule.grace_in_time.split(":")
            gp_mins = hrs_to_mins(gp_chunks[0], gp_chunks[1])

            if diff_mins > gp_mins:
                ck_mins = divmod(diff_mins - gp_mins, 60)
                self.create_anamoly_hist(
                    clock,
                    choice=AnamolyHistory.IN_TIME_BREACH,
                    result=f"{ck_mins[0]}:{ck_mins[1]}",
                )

            # *  OUT TIME ANAMOLY

            diff = relativedelta(shift_out_time, clock_out)
            diff_mins = hrs_to_mins(diff.hours, diff.minutes)

            gp_chunks = rule.grace_out_time.split(":")
            gp_mins = hrs_to_mins(gp_chunks[0], gp_chunks[1])

            if diff_mins > gp_mins:
                ck_mins = divmod(diff_mins - gp_mins, 60)
                self.create_anamoly_hist(
                    clock,
                    choice=AnamolyHistory.OUT_TIME_BREACH,
                    result=f"{ck_mins[0]}:{ck_mins[1]}",
                )

            # * WORK DURATION ANAMOLY
            if clock.work_duration:
                self.handle_work_duration(clock, rule)

            # * MAX BREAK DURATION ANAMOLY
            if clock.break_duration:
                self.handle_break_duration(clock, rule)

            if clock.anamolies.all().exists():
                clock.status = "AN"
                clock.overtime_hours = 0
            else:
                clock.status = "P"
            clock.save()
        except Exception as e:
            print("errors in script", str(e), clock.employee.user.username, clock.date_of_checked_in, traceback.format_exc())


def init_shiftsetup_settings(self="", company=""):
    if not company:
        return
    current_year = timezone_now().date().year
    calendar_type="calendaryear"
    start_date = f"{current_year}-01-01"
    end_date = f"{current_year}-12-31"
    AttendanceShiftsSetup.objects.create(company=company,
                                    calendar_type=calendar_type,
                                    start_date=start_date,
                                    end_date=end_date,
                                )
import sys
import os
import traceback
import django
from concurrent.futures import ThreadPoolExecutor
import datetime
import math

sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from django.db import transaction
from django.db import models as db_models

from attendance import models as attendance_models
from leave import models as leave_models
from pss_calendar import models as pss_calendar_models
from directory import models as directory_models

from core.utils import get_month_weeks, get_month_pay_cycle_start_end_dates, mins_to_hrs, hrs_to_mins, localize_dt, timezone_now
from leave.services import is_day_type

class EmployeeMontlyAddendanceData:
    
    def __init__(self, start_date, end_date, employee):
        self.start_date = start_date
        self.end_date = end_date
        self.employee = employee
        self.attendance_data = {}
        self.present_days = 0.0
        self.leaves_count = 0.0
        self.absent_count = 0.0
        self.anamoly_count = 0.0
        self.halfday_count = 0.0
        self.overtime_count = 0.0
        self.lop_count = 0.0
        self.updated_lop_count = 0.0
        self.penalty_details = {}

    def prepare_attendance_data(self, status, time_in, time_out, work_duration, break_duration, breaks, anamolies, approval_status, reason=None, present_count=0, over_time_data=""):
        return {
            "status": status,
            "time_in": time_in,
            "time_out": time_out,
            "work_duration": work_duration,
            "break_duration": break_duration,
            "breaks": breaks,
            "anamolies": anamolies,
            "approval_status": approval_status,
            "reason": reason,
            "present_count": present_count,
            "over_time_data": over_time_data
        }
    
    def get_status_reason(self, clock):
        lh_qs = leave_models.LeavesHistory.objects.filter(
            employee=self.employee,
            start_date__lte=clock.date_of_checked_in,
            end_date__gte=clock.date_of_checked_in,
            status=leave_models.LeavesHistory.APPROVED
        )
        if h := pss_calendar_models.Holidays.objects.filter(
            holiday_date=clock.date_of_checked_in, company=self.employee.company, is_deleted=False
        ):
            if not lh_qs.exists():
                if clock.compoff_added is None:
                    self.present_days += 1.0
                    # print(self.present_days, clock.date_of_checked_in)
                    self.p_count = 1
                    return "H", h.first().holiday_name, False
                if clock.compoff_added is not None:
                    self.present_days += 1.0
                    # print(self.present_days, clock.date_of_checked_in)
                    self.p_count = 1
                    return "CO", f'{h.first().holiday_name} - {clock.compoff_added}', False
            else:
                if lh_qs.filter(leave_rule__holidays_between_leave=True):
                    self.leaves_count += 1
                    self.p_count = 0
                    self.penalty_details[self.formatted_date] = {
                        "reason": lh_qs.first().reason,
                        "no_of_days_deducted": 1,
                        "deducted_from": lh_qs.last().leave_rule.name
                    }
                    return "L", lh_qs.first().reason, False
        
        if work_rule_relation := leave_models.EmployeeWorkRuleRelation.objects.filter(
            employee=self.employee, #effective_date__lte=clock.date_of_checked_in
        ).first():
            work_rule = work_rule_relation.work_rule
            week_number = get_month_weeks(
                clock.date_of_checked_in, need_week_number_only=True
            )
            rule_choice = leave_models.WorkRuleChoices.objects.filter(
                work_rule=work_rule, week_number=week_number
            ).first()
            if not lh_qs.exists():
                if is_day_type(choice=rule_choice, work_type=0, dt_input=clock.date_of_checked_in) and clock.compoff_added is None:
                    self.present_days += 1.0
                    # print(self.present_days, clock.date_of_checked_in)
                    self.p_count = 1
                    return "WO", "Week OFF", False
                if is_day_type(choice=rule_choice, work_type=0, dt_input=clock.date_of_checked_in) and clock.compoff_added is not None:
                    self.present_days += 1.0
                    # print(self.present_days, clock.date_of_checked_in)
                    self.p_count = 1
                    return "CO", f'{clock.compoff_added} - {clock.compoff_added}', False
                if is_day_type(choice=rule_choice, work_type=1, dt_input=clock.date_of_checked_in) and clock.status == "P":
                    self.present_days += 1.0
                    # print(self.present_days, clock.date_of_checked_in)
                    self.p_count = 1
                    return "P", "Half Week Off", False
            else:
                if lh_qs.filter(leave_rule__weekends_between_leave=True):
                    self.leaves_count += 1
                    self.p_count = 0
                    self.penalty_details[self.formatted_date] = {
                        "reason": lh_qs.first().reason,
                        "no_of_days_deducted": 1,
                        "deducted_from": lh_qs.last().leave_rule.name
                    }
                    return "L", lh_qs.first().reason, False


        if lh_qs.filter(is_penalty=True).exists():
            self.anamoly_count += 1

            if float(lh_qs.first().no_of_leaves_applied) < 1.0:
                self.present_days += float(0.5)
                # print(self.present_days, clock.date_of_checked_in)
                self.leaves_count += float(0.5)
                self.p_count = 0.5
                
                self.penalty_details[self.formatted_date] = {
                    "reason": lh_qs.first().reason,
                    "no_of_days_deducted": 0.5,
                    "deducted_from": lh_qs.last().leave_rule.name
                }
            else:
                self.leaves_count += 1.0
                self.p_count = 0
                
                self.penalty_details[self.formatted_date] = {
                    "reason": lh_qs.first().reason,
                    "no_of_days_deducted": 1,
                    "deducted_from": lh_qs.last().leave_rule.name
                }
            return "PN", lh_qs.first().reason, False
        elif lh_qs.filter(leave_rule__name="Loss Of Pay", approved_by__isnull=True).exists():
            self.anamoly_count += 1
            if float(lh_qs.first().no_of_leaves_applied) < 1.0:
                self.present_days += float(0.5)
                # print(self.present_days, clock.date_of_checked_in)
                self.lop_count += 0.5
                self.p_count = 0.5
                # self.penalty_details[self.formatted_date] = {
                #     "reason": lh_qs.first().reason,
                #     "no_of_days_deducted": 0.5,
                #     "deducted_from": lh_qs.last().leave_rule.name
                # }
            else:
                self.lop_count += 1.0
                self.p_count = 0
                # self.penalty_details[self.formatted_date] = {
                #     "reason": lh_qs.first().reason,
                #     "no_of_days_deducted": 1,
                #     "deducted_from": lh_qs.last().leave_rule.name
                # }
            return "PN", lh_qs.first().reason, False
        elif lh_qs.filter(leave_rule__name="Loss Of Pay", approved_by__isnull=False).exists():
            if float(lh_qs.first().no_of_leaves_applied) < 1.0:
                self.present_days += 0.5
                # print(self.present_days, clock.date_of_checked_in)
                self.lop_count += 0.5
                self.p_count = 0.5
                
                # self.penalty_details[self.formatted_date] = {
                #     "reason": lh_qs.first().reason,
                #     "no_of_days_deducted": 0.5,
                #     "deducted_from": lh_qs.last().leave_rule.name
                # }
            else:
                self.lop_count += 1.0
                self.p_count = 0.5
                
                # self.penalty_details[self.formatted_date] = {
                #     "reason": lh_qs.first().reason,
                #     "no_of_days_deducted": 1,
                #     "deducted_from": lh_qs.last().leave_rule.name
                # }
            return "L", lh_qs.first().reason, True       
        elif lh_qs.filter(is_penalty=False).exists():
            if lh_qs.filter(~db_models.Q(leave_rule__name='Additional Leaves')):
                if float(lh_qs.first().no_of_leaves_applied) < 1.0:
                    self.present_days += 0.5
                    # print(self.present_days, clock.date_of_checked_in)
                    self.leaves_count += 0.5
                    self.p_count = 0.5
                    
                    self.penalty_details[self.formatted_date] = {
                        "reason": lh_qs.first().reason,
                        "no_of_days_deducted": 0.5,
                        "deducted_from": lh_qs.last().leave_rule.name
                    }
                else:
                    self.penalty_details[self.formatted_date] = {
                        "reason": lh_qs.first().reason,
                        "no_of_days_deducted": 1,
                        "deducted_from": lh_qs.last().leave_rule.name
                    }
                    self.p_count = 0
                    self.leaves_count += 1.0
            else:
                if float(lh_qs.first().no_of_leaves_applied) < 1.0:
                    self.present_days += 0.5
                    # print(self.present_days, clock.date_of_checked_in)
                    self.lop_count += 0.5
                    self.p_count = 0.5
                    
                    self.penalty_details[self.formatted_date] = {
                        "reason": lh_qs.first().reason,
                        "no_of_days_deducted": 0.5,
                        "deducted_from": lh_qs.last().leave_rule.name
                    }
                else:
                    self.penalty_details[self.formatted_date] = {
                        "reason": lh_qs.first().reason,
                        "no_of_days_deducted": 1,
                        "deducted_from": lh_qs.last().leave_rule.name
                    }
                    self.p_count = 0
                    self.lop_count += 1.0
            return "L", lh_qs.first().reason, True


        if clock.status == "AN" or clock.anamolies.exists():
            if 10 not in clock.anamolies.values_list('status', flat=True):
                
                self.absent_count += 1
                elr = leave_models.EmployeeLeaveRuleRelation.objects.filter(leave_rule__name="Loss Of Pay", leave_rule__is_deleted=False, employee=self.employee).first()
                l_obj, is_leave_cre = leave_models.LeavesHistory.objects.get_or_create(
                        employee=self.employee,
                        leave_rule=elr.leave_rule,
                        start_date=clock.date_of_checked_in,
                        end_date=clock.date_of_checked_in,
                        reason="Absent",
                        status=leave_models.LeavesHistory.APPROVED,
                        no_of_leaves_applied=1,
                    )
                # self.penalty_details[self.formatted_date] = {
                #     "reason": "Absent",
                #     "no_of_days_deducted": 1,
                #     "deducted_from": "Loss Of Pay"
                # }
                elr.remaining_leaves = float(elr.remaining_leaves) - float(1)
                elr.used_lop_leaves = float(elr.used_lop_leaves) + float(1)
                elr.used_so_far = float(elr.used_so_far) + float(1)
                elr.save()
                self.p_count = 0
                
                clock.action_status = 40
                clock.save()
                l_obj.save()
                if 20 in clock.anamolies.values_list('status', flat=True):
                    return "A", "Anamoly Not sent for Approval", False
                if 30 in clock.anamolies.values_list('status', flat=True):
                    return "A", "Anamoly Not Approved", False
                if 40 in clock.anamolies.values_list('status', flat=True):
                    return "A", "Anamoly Is Rejected", False

        self.present_days += 1
        # print(self.present_days, clock.date_of_checked_in)
        self.p_count = 1
        if clock.employee.assignedattendancerules_set.first().attendance_rule.enable_over_time and clock.overtime_hours != 0 and clock.action_status==10 and clock.action==60:
            self.overtime_count += clock.overtime_hours
            return "OT", "", False
        leave_models.LeavesHistory.objects.filter(
                        employee=self.employee,
                        leave_rule=leave_models.EmployeeLeaveRuleRelation.objects.filter(leave_rule__name="Loss Of Pay", employee=self.employee).first().leave_rule,
                        start_date=clock.date_of_checked_in,
                        end_date=clock.date_of_checked_in
                    ).delete()
        return "P", "", False
    
    def non_clock_exist(self, date):
        if work_rule_relation := leave_models.EmployeeWorkRuleRelation.objects.filter(
            employee=self.employee, # effective_date__lte=date
        ).first():
            if date >= self.employee.date_of_join:
                work_rule = work_rule_relation.work_rule
                week_number = get_month_weeks(
                    date, need_week_number_only=True
                )
                rule_choice = leave_models.WorkRuleChoices.objects.filter(
                work_rule=work_rule, week_number=week_number
                ).first()
                if is_day_type(choice=rule_choice, dt_input=date):
                    self.present_days += 1.0
                    # print(self.present_days, date)
                    self.p_count = 1
                    self.attendance_data[self.formatted_date] = self.prepare_attendance_data(
                        'WO', None, None, None, None, None, {"count": 0}, "", "", self.p_count
                    )
                    return
        if h := pss_calendar_models.Holidays.objects.filter(
            holiday_date=date, company=self.employee.company, is_deleted=False
        ):
            if date >= self.employee.date_of_join:
                self.present_days += 1.0
                # print(self.present_days, date)
                self.p_count = 1
                self.attendance_data[self.formatted_date] = self.prepare_attendance_data(
                    'H', None, None, None, None, None, {"count": 0}, "", h.first().holiday_name, self.p_count
                )
                return
        if lh_qs := leave_models.LeavesHistory.objects.filter(
                employee=self.employee,
                start_date__lte=date,
                end_date__gte=date,
                status=leave_models.LeavesHistory.APPROVED
        ).exclude(leave_rule__name__in=["Loss Of Pay", 'Additional Leaves']):
            if date >= self.employee.date_of_join:
                if float(lh_qs.first().no_of_leaves_applied) < 1.0:
                    self.leaves_count += 0.5
                    self.present_days += 0.5
                    self.p_count = 0.5
                    self.penalty_details[self.formatted_date] = {
                        "reason": lh_qs.first().reason,
                        "no_of_days_deducted": 0.5,
                        "deducted_from": lh_qs.first().leave_rule.name
                    }
                else:
                    self.leaves_count += 1.0
                    self.p_count = 0  
                    self.penalty_details[self.formatted_date] = {
                        "reason": lh_qs.first().reason,
                        "no_of_days_deducted": 1.0,
                        "deducted_from": lh_qs.first().leave_rule.name
                    }
                # leave_models.LeavesHistory.objects.filter(
                #     employee=self.employee,
                #     leave_rule=leave_models.EmployeeLeaveRuleRelation.objects.filter(leave_rule__name="Loss Of Pay", employee=self.employee).first().leave_rule,
                #     start_date=date,
                #     end_date=date
                # ).delete()
                self.attendance_data[self.formatted_date] = self.prepare_attendance_data(
                    'L', None, None, None, None, None, {"count": 0}, "Approved", lh_qs.first().reason, self.p_count
                )
                return
        if lh_qs := leave_models.LeavesHistory.objects.filter(
                employee=self.employee,
                start_date__lte=date,
                end_date__gte=date,
                status=leave_models.LeavesHistory.APPROVED,
                leave_rule__name='Additional Leaves'
        ):
            if date >= self.employee.date_of_join:
                dedu = 1.0
                self.p_count = 0.0
                if float(lh_qs.first().no_of_leaves_applied) < 1.0:
                    dedu = 0.5
                    self.present_days += 0.5
                    # print(self.present_days, date)
                    self.p_count = 0.5
                    self.penalty_details[self.formatted_date] = {
                        "reason": lh_qs.first().reason,
                        "no_of_days_deducted": dedu,
                        "deducted_from": lh_qs.first().leave_rule.name
                    }
                else:
                    self.penalty_details[self.formatted_date] = {
                        "reason": lh_qs.first().reason,
                        "no_of_days_deducted": 1.0,
                        "deducted_from": lh_qs.first().leave_rule.name
                    }
                self.lop_count += dedu
                self.attendance_data[self.formatted_date] = self.prepare_attendance_data(
                    'L', None, None, None, None, None, {"count": 0}, "Approved", lh_qs.first().reason, self.p_count
                )
                return
            
        if lh_qs := leave_models.LeavesHistory.objects.filter(
                employee=self.employee,
                start_date__lte=date,
                end_date__gte=date,
                status=~db_models.Q((leave_models.LeavesHistory.APPROVED),
                leave_rule__name='Additional Leaves'
        ):
            if date >= self.employee.date_of_join:
                dedu = 1.0
                self.p_count = 0.0
                if float(lh_qs.first().no_of_leaves_applied) < 1.0:
                    dedu = 0.5
                    self.present_days += 0.5
                    # print(self.present_days, date)
                    self.p_count = 0.5
                    self.penalty_details[self.formatted_date] = {
                        "reason": lh_qs.first().reason,
                        "no_of_days_deducted": dedu,
                        "deducted_from": lh_qs.first().leave_rule.name
                    }
                else:
                    self.penalty_details[self.formatted_date] = {
                        "reason": lh_qs.first().reason,
                        "no_of_days_deducted": 1.0,
                        "deducted_from": lh_qs.first().leave_rule.name
                    }
                self.lop_count += dedu
                self.attendance_data[self.formatted_date] = self.prepare_attendance_data(
                    'L', None, None, None, None, None, {"count": 0}, "Not Approved", lh_qs.first().reason, self.p_count
                )
                return
            
        #  if applied leaves - not check in - not approved - not rejected - not cancelled - count as LOP
        # if checkin and applied leaves - as per hallf day and full day ansent -  LOP
            
        if self.attendance_data.get(self.formatted_date) is None:
            # create LOP
            # print(self.employee.user.username, self.formatted_date)
            elr = leave_models.EmployeeLeaveRuleRelation.objects.filter(leave_rule__name="Loss Of Pay", employee=self.employee).first()
            # print(elr.leave_rule)
            l_obj, is_leave_cre = leave_models.LeavesHistory.objects.get_or_create(
                employee=self.employee,
                leave_rule=elr.leave_rule,
                start_date=date,
                end_date=date,
                reason="Absent",
                status=leave_models.LeavesHistory.APPROVED,
                no_of_leaves_applied=1,
            )
            elr.remaining_leaves = float(elr.remaining_leaves) - float(1)
            elr.used_lop_leaves = float(elr.used_lop_leaves) + float(1)
            elr.used_so_far = float(elr.used_so_far) + float(1)
            elr.save()
            l_obj.save()
            # self.penalty_details[self.formatted_date] = {
            #     "reason": "Absent",
            #     "no_of_days_deducted": 1,
            #     "deducted_from": "Loss Of Pay"
            # }
            self.absent_count += 1
            self.attendance_data[self.formatted_date] = self.prepare_attendance_data(
                'A', None, None, None, None, None, {"count": 0}, "", "Absent", 0
            )
            self.p_count = 0

    def main(self):
        # print("hi")
        if attendance_models.EmployeeMonthlyAttendanceRecords.objects.filter(
            employee=self.employee, year=self.start_date.year,
            month=self.start_date.month
        ):
            attendance_models.EmployeeMonthlyAttendanceRecords.objects.filter(
                employee=self.employee, year=self.start_date.year,
                month=self.start_date.month
            ).delete()
        obj, is_created = attendance_models.EmployeeMonthlyAttendanceRecords.objects.get_or_create(
            employee=self.employee, year=self.start_date.year,
            month=self.start_date.month
        )
        # if self.start_date <= self.employee.date_of_join:
        #     self.start_date = self.employee.date_of_join
        for i in range((self.end_date-self.start_date).days + 1):
            date = self.start_date  + datetime.timedelta(days=i)
            self.formatted_date = datetime.datetime.strftime(date, "%Y-%m-%d")
            clock_qs = self.employee.clock_details.filter(date_of_checked_in=date)
            self.p_count = 0
            if not clock_qs.exists():
                self.non_clock_exist(date)
            else:
                clock = clock_qs.first()
                # print(clock.__dict__)
                status, reason, is_leave_approved = self.get_status_reason(clock)
                approval_status = ''
                if is_leave_approved:
                    approval_status = "Approved"
                elif status not in ["WO", "P", "H"]:
                    approval_status = "Rejected"
                if status == "AN":
                    approval_status = 'Rejected'
                self.attendance_data[self.formatted_date] = self.prepare_attendance_data(
                    status=status, reason=reason, time_in=datetime.datetime.strftime(localize_dt(clock.time_in), "%Y-%m-%d %I:%M %p"),
                    time_out=datetime.datetime.strftime(localize_dt(clock.time_out), "%Y-%m-%d %I:%M %p") if isinstance(clock.time_out, datetime.datetime) else None, work_duration=clock.work_duration,
                    break_duration=clock.break_duration, breaks=clock.breaks, over_time_data=mins_to_hrs(clock.overtime_hours),
                    anamolies={"count": clock.anamolies.count()}, approval_status=approval_status, present_count=self.p_count
                )
        # print(self.__dict__)
        obj.present_days = self.present_days
        obj.leaves_count = self.leaves_count
        obj.absent_count = self.absent_count
        obj.anamoly_count = self.anamoly_count
        obj.halfday_count = self.halfday_count
        obj.lop_count = self.lop_count + self.absent_count
        if obj.employee.assignedattendancerules_set.first().attendance_rule.enable_over_time and self.overtime_count!=0:
            fullday_duration = hrs_to_mins(
                obj.employee.assignedattendancerules_set.first().attendance_rule.full_day_work_duration.split(":")[0],
                obj.employee.assignedattendancerules_set.first().attendance_rule.full_day_work_duration.split(":")[1]
            )
            ot_days = math.modf(self.overtime_count/fullday_duration)
            final_ot = ot_days[1]
            if 0 <= ot_days[0] < 0.5:
                final_ot = ot_days[1]
            elif 0.5 <= ot_days[0]:
                final_ot += 0.5
            obj.overtime_count = final_ot
        obj.penalty_details = self.penalty_details
        obj.attendance_data = self.attendance_data
        # print(obj.__dict__)

        obj.save()

if __name__ == "__main__":
    emps = directory_models.Employee.objects.filter(company_id=1,
                                                    payroll_status=True,
                                                    # work_details__employee_status='Active',
                                                    employeeleaverulerelation__isnull=False,
                                                    employeeworkrulerelation__isnull=False,
                                                    assignedattendancerules__isnull=False,
                                                    # work_details__employee_number = 'PSS-1018',
                                                    ).order_by('id').distinct('id')
    attendance_settings = attendance_models.AttendanceRuleSettings.objects.get(company_id=1)
    start_from_day = attendance_settings.attendance_input_cycle_from
    end_of_day = attendance_settings.attendance_input_cycle_to
    today = timezone_now().date()
    start_date, end_date = get_month_pay_cycle_start_end_dates(start_from_day, end_of_day, today)
    sid = transaction.set_autocommit(autocommit=False)
    # start_date = datetime.date(2023, 11, 21)
    # end_date = datetime.date(2023, 12, 20)
    try:
        
        for employee in emps[:2]:
            # print(employee,start_date,end_date)
            EmployeeMontlyAddendanceData(start_date, end_date, employee).main()
    except Exception as e:
        print(f'{e} {employee} Error: {traceback.format_exc()}')
        transaction.rollback(sid)
    # transaction.savepoint_rollback(sid=sid)
    if "commit" in sys.argv:
        transaction.commit()
        print("Employees Monthly Attendance data run successfully!")
    else:
        print("Dry Run!")
        transaction.rollback(sid)


# list(Employee.objects.using('vg').filter(
#        db_models.Q(payroll_status=True, montly_attendance__isnull=True,) 
#     ).annotate(
#         no_ls=db_models.Case(
#             db_models.When(employeeleaverulerelation__isnull=True, then=db_models.Value('True')),
#             default=db_models.Value('False')
#         ),
#         no_wrs=db_models.Case(
#             db_models.When(employeeworkrulerelation__isnull=True, then=db_models.Value('True')),
#             default=db_models.Value('False')
#         ),
#         no_att=db_models.Case(
#             db_models.When(assignedattendancerules__isnull=True, then=db_models.Value('True')),
#             default=db_models.Value('False')
#         ), 
#     ).values('user__username', "work_details__employee_number", "no_ls", "no_wrs", "no_att").order_by('id').distinct('id'))
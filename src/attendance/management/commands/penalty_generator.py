import sys
from typing import Any, Optional
import traceback
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.db.models import QuerySet, Subquery, Q, F, Value, Case, When
from django.contrib.postgres.aggregates import ArrayAgg
from dateutil.relativedelta import relativedelta

from attendance.models import (AnamolyHistory, AssignedAttendanceRules, EmployeeCheckInOutDetails,
                            PenaltyRules, AutoDeductionHistory, AttendanceRuleSettings)
from core.utils import timezone_now
from directory.models import Employee
from leave.models import LeaveRules, LeavesHistory, EmployeeWorkRuleRelation, WorkRuleChoices

from core.utils import get_month_weeks, get_month_pay_cycle_start_end_dates
from leave.services import is_day_type

class Command(BaseCommand):
    """
    Command to generate penalties to all of the submitted company employees

    AJAY, 11.04.2023
    """

    help = "manage.py penalty_generator -cp 1 -c"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument(
            "-c",
            "--commit",
            dest="commit",
            action="store_true",
            default=False,
            help="Commit to database",
        )

        parser.add_argument("-cp", "--company", type=int, dest="company")

    def handle_penalty(
        self,
        no_of_anamolies: int,
        employee: Employee,
        anamolies = None,
        accepted_anamolies: int = 0,
        penalty_interval: int = 0,
        penalty_session: str = "Full Day",
        penalty_type: str = "Default",
        no_of_auto_deductions = 0,
        leave_type_to_deduct = [],
        deductions=None
    ):
        """
        This function handles penalties for employees based on the number and type of anomalies in their
        leave requests.

        :param no_of_anamolies: The number of anomalies that occurred for the employee
        :type no_of_anamolies: int
        :param employee: The employee for whom the penalty is being handled
        :type employee: Employee
        :param anamolies: anamolies is a list or QuerySet of anomalies (unexpected or irregular events)
        for an employee
        :type anamolies: Optional(QuerySet, list)
        :param accepted_anamolies: `accepted_anamolies` is the number of anomalies that have been
        accepted by the manager or supervisor. Any anomalies beyond this number will be considered for
        penalty, defaults to 0
        :type accepted_anamolies: int (optional)
        :param penalty_interval: The number of days between two consecutive penalties. For example, if
        the penalty interval is set to 7, an employee will receive a penalty every 7 days if they
        continue to have anomalies, defaults to 0
        :type penalty_interval: int (optional)
        :param penalty_session: The parameter "penalty_session" is a string that specifies whether the
        penalty should be applied for a full day or half day. It can take the values "Full Day" or "Half
        Day" (case-insensitive). If the value is "Half Day", the penalty will be applied for half,
        defaults to Full Day
        :type penalty_session: str (optional)
        :param penalty_type: The type of penalty being applied, which is a string value, defaults to
        Default
        :type penalty_type: str (optional)
        :return: If the number of anomalies is greater than the accepted anomalies, nothing is returned.
        If the anomalies parameter is None, nothing is returned. Otherwise, the function applies a
        penalty by creating a new LeavesHistory object and saving it, and updates the
        latest_anomaly_date variable. No explicit return statement is provided in this case, so the
        function implicitly returns None.

        AJAY, 11.04.2023
        
        
        Penalty interval: Every 3 days of late coming
        Penalty: Half day deduction of pay
        Leave deduction: Loss of Pay
        According to the policy, the following deductions will be implemented:
        For the first 2 instances of late coming, no penalty will be imposed.
        Starting from the 3th day of late coming, 1 half day will be deducted.
        For every subsequent 3 days of late coming, 1 half day will be deducted.
        In the specific case mentioned, where there were 10 instances of late coming, the total penalty will be 2 days of half day Loss of Pay (LOP). This means that for those 10 late days, 2 days' worth of pay will be deducted

        """
        if not anamolies and no_of_auto_deductions == 0:
            return

        anas = anamolies[accepted_anamolies:]
        auto_deducted = False
        if len(anas) <= 0:
            anas = deductions[accepted_anamolies:]
            auto_deducted = True
        if len(anas) == 0:
            return
        elrs = employee.employeeleaverulerelation_set.filter(leave_rule_id__in=leave_type_to_deduct).exclude(
            leave_rule__name='Loss Of Pay'
        )
        if penalty_interval > 0:
            anamolies_to_generate_ids =  [index-1 for index, elem in enumerate(anas, 1) if  index%penalty_interval==0]
        else:
            anamolies_to_generate_ids = list(range(len(anas)))
        for i in anamolies_to_generate_ids:
            elrs = elrs.filter(remaining_leaves__gt=0)
            if penalty_session.lower() in {"half_day", "half day", "halfday"}:
                no_of_leaves = 0.5
            else:
                no_of_leaves = 1
            anamoly = anas[i]
            if not LeavesHistory.objects.filter(
                employee=employee, start_date__lte=anamoly.request_date,
                end_date__gte=anamoly.request_date, status=LeavesHistory.APPROVED
            ):
                if elrs.exists():
                    elr = elrs.first()
                    leave = LeavesHistory(
                        employee=employee,
                        leave_rule=elr.leave_rule,
                        start_date=anamoly.request_date,
                        end_date=anamoly.request_date,
                        reason=f"{penalty_type} {'penalty applied' if not auto_deducted else 'auto deducted'}",
                        status=LeavesHistory.APPROVED,
                        no_of_leaves_applied=no_of_leaves,
                        is_penalty=True
                    )
                else:
                    elr = employee.employeeleaverulerelation_set.filter(leave_rule__name='Loss Of Pay', leave_rule__is_deleted=False).first()
                    leave = LeavesHistory(
                        employee=employee,
                        leave_rule=elr.leave_rule,
                        start_date=anamoly.request_date,
                        end_date=anamoly.request_date,
                        reason=f"{penalty_type} {'penalty applied' if not auto_deducted else 'auto deducted'}",
                        status=LeavesHistory.APPROVED,
                        no_of_leaves_applied=no_of_leaves,
                    )
                employee.clock_details.filter(date_of_checked_in=anamoly.request_date).update(action_status=40)
                self.stdout.write(self.style.WARNING(f"Leave Added for {employee.first_name} on {anamoly.request_date} - {no_of_leaves} Reason: {penalty_type} {'penalty applied' if not auto_deducted else 'auto deducted'}"))
                elr.remaining_leaves = float(elr.remaining_leaves) - float(no_of_leaves)
                elr.used_lop_leaves = float(elr.used_lop_leaves) + float(no_of_leaves)
                elr.used_so_far = float(elr.used_so_far) + float(no_of_leaves)
                elr.save()
                leave.save()

    # @transaction.atomic
    def handle(self, *args: Any, **options: Any):
        """
        Default peanlty rule handler

        AJAY, 11.04.2023
        """
        

        today = timezone_now().date()
        emps = Employee.objects.filter(
            Q(clock_details__autodeductionhistory__isnull=False) | Q(clock_details__anamolies__isnull=False)
        ).order_by('id').distinct('id')
        if options.get("company", None):
            emps = emps.filter(company=options["company"])
        # if AnamolyHistory.objects.filter(clock__employee_id__in=emps.values_list('id', flat=True), status=30).exists():
        #     sys.exit('There are Anamolies In Processing Please approve or reject')
        for emp in emps:
            sid = transaction.set_autocommit(autocommit=False)
            attendance_rule = emp.assignedattendancerules_set.first().attendance_rule
            attendance_setting_obj = emp.company.attendancerulesettings_set.filter(is_deleted=False).first()
            month_start, month_last = get_month_pay_cycle_start_end_dates(
                attendance_setting_obj.attendance_input_cycle_from,
                attendance_setting_obj.attendance_input_cycle_to,
                today
            )
            anamolies = AnamolyHistory.objects.filter(
                request_date__range=[month_start, month_last],
                clock__employee__assignedattendancerules__attendance_rule__enable_anomaly_tracing=True,
                clock__employee=emp,
                is_deleted=False,
            ).exclude(status=20) 
            deductions = AutoDeductionHistory.objects.filter(
                request_date__gte=month_start,
                request_date__lte=month_last,
                clock__employee__assignedattendancerules__attendance_rule__auto_deduction=True,
                clock__employee=emp,
                is_deleted=False
            )
            no_of_anamolies = anamolies.count()
            main_anamolies, main_deductions = anamolies, deductions
            if no_of_anamolies > 0 or deductions.exists():
                penalty = PenaltyRules.objects.filter(attendance_rule_id=attendance_rule.id)
                try:
                    penalty = penalty.first()
                    if deductions.exists():
                        exclude_deuctions = EmployeeCheckInOutDetails.objects.filter(employee_id=emp.id,
                            date_of_checked_in__range=[month_start, month_last], action_status=10).values_list("date_of_checked_in", flat=True)
                        if exclude_deuctions:
                            main_deductions = deductions.exclude(request_date__in=exclude_deuctions)
                    main_anamolies = main_anamolies.exclude(status=10)
                    # WORK DURATION PENALTY
                    if penalty.work_duration:
                        anamolies = main_anamolies.filter(choice = AnamolyHistory.FULL_DAY_WD_BREACH)
                        deductions = main_deductions.filter(choice='FULL_DAY_WD_BREACH')
                        self.handle_penalty(
                            no_of_anamolies=anamolies.count(),
                            employee=emp,
                            anamolies=anamolies,
                            accepted_anamolies=penalty.shortfall_in_wd_allowed,
                            penalty_interval=penalty.work_penalty_interval,
                            penalty_session=penalty.work_penalty,
                            penalty_type="Work Duration",
                            no_of_auto_deductions=deductions.count(),
                            leave_type_to_deduct=penalty.work_leave_deduction,
                            deductions=deductions
                        )

                    # BREAK DURATION PENALTY
                    if penalty.outstanding_breaks_penalty:
                        anamolies = main_anamolies.filter(choice = AnamolyHistory.MAX_TOTAL_BREAKS_BREACH)
                        deductions = main_deductions.filter(choice='MAX_TOTAL_BREAKS_BREACH')
                        self.handle_penalty(
                            no_of_anamolies=anamolies.count(),
                            employee=emp,
                            anamolies=anamolies,
                            accepted_anamolies=penalty.excess_breaks_allowed,
                            penalty_interval=penalty.break_penalty_interval,
                            penalty_session=penalty.break_penalty,
                            penalty_type="Work Duration",
                            no_of_auto_deductions=deductions.count(),
                            leave_type_to_deduct=penalty.break_leave_deduction,
                            deductions=deductions
                        )
                    # IN TIME PENALTY
                    if penalty.in_time:
                        anamolies = main_anamolies.filter(choice = AnamolyHistory.IN_TIME_BREACH)
                        deductions = main_deductions.filter(choice='IN_TIME_BREACH')
                        self.handle_penalty(
                            no_of_anamolies=anamolies.count(),
                            employee=emp,
                            anamolies=anamolies,
                            accepted_anamolies=penalty.late_coming_allowed,
                            penalty_interval=penalty.in_penalty_interval,
                            penalty_session=penalty.in_penalty,
                            penalty_type="In Time",
                            no_of_auto_deductions=deductions.count(),
                            leave_type_to_deduct=penalty.in_leave_deduction,
                            deductions=deductions
                        )
                    # OUT TIME
                    if penalty.out_time:
                        anamolies = main_anamolies.filter(choice = AnamolyHistory.OUT_TIME_BREACH)
                        deductions = main_deductions.filter(choice='OUT_TIME_BREACH')
                        self.handle_penalty(
                            no_of_anamolies=anamolies.count(),
                            employee=emp,
                            anamolies=anamolies,
                            accepted_anamolies=penalty.early_leaving_allowed,
                            penalty_interval=penalty.out_penalty_interval,
                            penalty_session=penalty.out_penalty,
                            penalty_type="Out Time",
                            no_of_auto_deductions=deductions.count(),                            
                            leave_type_to_deduct=penalty.out_leave_deduction,
                            deductions=deductions
                        )

                    if options["commit"]:
                        transaction.commit()
                        self.stdout.write(self.style.WARNING("Successful Commit !"))
                    else:
                        transaction.rollback(sid)
                        self.stdout.write(self.style.ERROR_OUTPUT(f"Dry Run !!"))
                except Exception as e:
                    transaction.rollback(sid)
                    self.stdout.write(self.style.ERROR_OUTPUT(f"Dry Run !! {e}"))
                    print(traceback.format_exc())

import sys
import os
import django

from django.db import models as db_models
from django.db import transaction


sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]
    
from attendance.models import (
    AnamolyHistory, 
    EmployeeCheckInOutDetails,
    PenaltyRules, 
    AutoDeductionHistory
)
from core.utils import timezone_now
from leave.models import (
    LeavesHistory
)
from directory.models import Employee
from django.db import models as db_models
import pandas as pd
from core.utils import get_month_pay_cycle_start_end_dates


class PenaultyGeneratorDailyRun:

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
                # self.stdout.write(self.style.WARNING(f"Leave Added for {employee.first_name} on {anamoly.request_date} - {no_of_leaves} Reason: {penalty_type} {'penalty applied' if not auto_deducted else 'auto deducted'}"))
                print(f"Leave Added for {employee.first_name} on {anamoly.request_date} - {no_of_leaves} Reason: {penalty_type} {'penalty applied' if not auto_deducted else 'auto deducted'}")
                elr.remaining_leaves = float(elr.remaining_leaves) - float(no_of_leaves)
                elr.used_lop_leaves = float(elr.used_lop_leaves) + float(no_of_leaves)
                elr.used_so_far = float(elr.used_so_far) + float(no_of_leaves)
                elr.save()
                leave.save()

    # @transaction.atomic
    def main(self):
        """
        Default peanlty rule handler

        AJAY, 11.04.2023
        """
        

        today = timezone_now().date()
        emps = Employee.objects.filter(
            db_models.Q(clock_details__autodeductionhistory__isnull=False) | db_models.Q(clock_details__anamolies__isnull=False)
        ).order_by('id').distinct('id')
        # if options.get("company", None):
        emps = emps.filter(company_id= 1)
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

                    if "commit" in sys.argv:
                        transaction.commit()
                        print("Successful Commit !")
                    else:
                        transaction.rollback(sid)
                        print(f"Dry Run !!")
                except Exception as e:
                    transaction.rollback(sid)
                    print((f"Dry Run !! {str(e)}"))
                    # print(traceback.format_exc())


if __name__ == "__main__":
    PenaultyGeneratorDailyRun().main()
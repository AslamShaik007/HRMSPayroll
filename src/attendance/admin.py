from django.contrib import admin

from attendance import models
from core.admin import AbstractModelAdmin

admin.site.register(models.EmployeeMonthlyAttendanceRecords)
admin.site.register(models.ConsolidateNotificationDates)
admin.site.register(models.KeyloggerAttendanceLogs)
admin.site.register(models.EmployeeSystemMapping)


@admin.register(models.AttendanceRules)
class AttendanceRulesAdmin(AbstractModelAdmin):
    list_filter = ("name", "is_default")
    list_display = (
        "id",
        "company",
        "name",
        "description",
        "shift_in_time",
        "shift_out_time",
        "auto_deduction",
        "grace_in_time",
        "grace_out_time",
        "full_day_work_duration",
        "half_day_work_duration",
        "max_break_duration",
        "max_breaks",
        "auto_clock_out",
        "is_default",
        "effective_date",
    )

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(models.AssignedAttendanceRules)
class AssignedAttendanceRulesAdmin(AbstractModelAdmin):
    list_filter = ("employee", "attendance_rule", "effective_date")
    list_display = (
        "id",
        "employee",
        "attendance_rule",
        "effective_date",
        "resend_reminder",
    )

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(models.AttendanceRuleSettings)
class AttendanceRuleSettingsAdmin(AbstractModelAdmin):
    list_filter = (
        "company",
        "attendance_input_cycle_from",
        "attendance_input_cycle_to",
    )
    list_display = (
        "id",
        "company",
        "attendance_input_cycle_from",
        "attendance_input_cycle_to",
        "limit_backdated_ar_application",
        "limit_number_of_ar_application_per_month",
        "daily_attendance_report_reminder",
        "late_early_punch_reminder",
        "pending_regularization_reminder",
    )

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(models.EmployeeCheckInOutDetails)
class EmployeeCheckInOutDetailsAdmin(AbstractModelAdmin):
    list_filter = (
        "employee",
        "status",
        "date_of_checked_in",
        "work_duration",
    )
    list_display = (
        "id",
        "employee",
        "status",
        "date_of_checked_in",
        "time_in",
        "latest_time_in",
        "time_out",
        "work_duration",
        "break_duration",
        "breaks",
        "employee_selfie",
    )

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(models.AnamolyHistory)
class AnamolyHistoryAdmin(AbstractModelAdmin):
    list_filter = ("clock", "choice", "action", "status")
    list_display = (
        "id",
        "clock",
        "choice",
        "request_date",
        "reason",
        "action",
    )

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(models.PenaltyRules)
class PenaltyRulesAdmin(AbstractModelAdmin):
    list_filter = ("attendance_rule", "in_time", "out_time", "work_duration","outstanding_breaks_penalty")
    list_display = (
        "id",
        "attendance_rule",
        "in_time",
        "late_coming_allowed",
        "in_penalty_interval",
        "in_penalty",
        # "in_leave_deduction",
        "out_time",
        "early_leaving_allowed",
        "out_penalty_interval",
        "out_penalty",
        # "out_leave_deduction",
        "work_duration",
        "shortfall_in_wd_allowed",
        "work_penalty_interval",
        "work_penalty",
        # "work_leave_deduction",
        "outstanding_breaks_penalty",
        "excess_breaks_allowed",
        "break_penalty_interval",
        "break_penalty",
        # "break_leave_deduction",
    )

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)

admin.site.register(models.AttendanceShiftsSetup)
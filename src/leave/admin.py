from django.contrib import admin

from core.admin import AbstractModelAdmin
from leave import models


class WorkRuleChoicesInline(admin.TabularInline):
    model = models.WorkRuleChoices
    extra = 0
    raw_id_fields = ("work_rule",)


@admin.register(models.WorkRules)
class WorkRulesAdmin(AbstractModelAdmin):
    list_filter = ("name", "company", "is_default")
    list_display = ("id", "name", "company", "is_default")
    list_select_related = True
    inlines = [WorkRuleChoicesInline]


@admin.register(models.WorkRuleChoices)
class WorkRuleChoicesAdmin(AbstractModelAdmin):
    list_filter = ("work_rule", "week_number")
    list_display = (
        "id",
        "work_rule",
        "week_number",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(models.EmployeeWorkRuleRelation)
class EmployeeWorkRuleRelationAdmin(AbstractModelAdmin):
    list_filter = ("work_rule",)
    list_display = ("id", "employee", "work_rule", "effective_date", "is_deleted")


@admin.register(models.LeaveRules)
class LeaveRulesAdmin(AbstractModelAdmin):
    list_display = ("id", "name", "company")


@admin.register(models.EmployeeLeaveRuleRelation)
class EmployeeLeaveRuleRelationAdmin(AbstractModelAdmin):
    list_filter = ("leave_rule",)
    list_display = (
        "id",
        "employee",
        "leave_rule",
        "effective_date",
        "earned_leaves",
        "remaining_leaves",
        "used_so_far",
        "is_deleted",
    )


@admin.register(models.LeavesHistory)
class LeavesHistoryAdmin(AbstractModelAdmin):
    list_filter = ("employee", "leave_rule")
    list_display = (
        "id",
        "employee",
        "leave_rule",
        "start_date",
        "start_day_session",
        "end_day_session",
        "end_date",
        "is_deleted",
        "status",
    )
    search_fields = ["employee"]


admin.site.register(models.LeaveRuleSettings)
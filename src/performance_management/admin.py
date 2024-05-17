from django.contrib import admin
from performance_management import models
from core.admin import AbstractModelAdmin
# Register your models here.

@admin.register(models.AppraisalSetName)
class AppraisalSetNamesAdmin(AbstractModelAdmin):
    list_display = [
        'id',
        'company',
        'name',
        'author',
        'set_number',
        'is_active'
    ]

    list_filter = ("id", "name", 'set_number', 'is_active')


@admin.register(models.AppraisalSetQuestions)
class AppraisalSetQuestionsAdmin(AbstractModelAdmin):
    list_display = [
        'id',
        'set_name',
        'is_active',
        'creation_date',
        'questions'
    ]

    list_filter = ("id", "set_name")


@admin.register(models.NotificationDates)
class NotificationDateAdmin(AbstractModelAdmin):
    list_display = [
        'id',
        'notification_start_date',
        'notification_end_date',
        'reporting_manager_start_date',
        'reporting_manager_end_date',
        'employees_kra_deadline_date'
    ]

    list_filter = (
        "id",
        "notification_start_date",
        "notification_end_date",
        "reporting_manager_start_date",
        "reporting_manager_end_date",
        "employees_kra_deadline_date"
    )


@admin.register(models.AppraisalFormSubmit)
class AppraisalFormSubmitAdmin(AbstractModelAdmin):
    list_display = [
        'id',
        'employee',
        'set_name',
        'question',
        'answer',
        'sentform_date',
        'candidate_status'
    ]

    list_filter = (
        "id",
        "employee",
        "set_name",
        "question",
        "candidate_status"
    )


@admin.register(models.AppraisalSendForm)
class AppraisalSendFormAdmin(AbstractModelAdmin):
    list_display = [
        'id',
        'employee',
        'set_id',
        'creation_date',
        'candidate_status',
        'Emp_suggestion',
        'manager_acknowledgement',
        'score',
        'monthly_score_status',
        'email_status',
        'is_revoked',
        'comment',
        'reason',
        'form_deadline_date',
    ]

    list_filter = (
        "id",
        "employee",
        "set_id",
        "creation_date",
        "candidate_status"
    )
from django.contrib import admin

from core.admin import AbstractModelAdmin
from directory import models


@admin.register(models.Employee)
class EmployeeAdmin(AbstractModelAdmin):
    list_display = [
        "work_details",
        # "reporting_managers",
        # "salary_details",
        # "addresses",
        # "employeeresignationdetails",
        # "employeereporting3",
        # "employeereporting4",
        # "employeedirect2",
        # "employeedirect3",
        # "education_details",
        # "employeefamily",
        # "emergency_contact",
        # "employee_cetificate",
        # "documentation",
        "id",
        "company",
        "user",
        "first_name",
        "middle_name",
        "last_name",
        "official_email",
        "phone",
        "date_of_join",
        "date_of_birth",
        "gender",
        "blood_group",
        "marital_status",
        "anniversary_date",
        "personal_email",
        "alternate_phone",
        "pre_onboarding",
        "linkedin_profile",
        "facebook_profile",
        "twitter_profile",
        "payroll_status",
    ]

    search_fields = ("first_name", "personal_email", "phone")
    list_filter = ("roles", "gender")
    list_select_related = True
    filter_horizontal = ("roles",)


@admin.register(models.EmployeeWorkDetails)
class EmployeeWorkDetailsAdmin(AbstractModelAdmin):
    search_fields = ("employee", "employee_number", "reporting_manager")
    list_filter = ("employee_type", "designation",)

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(models.EmployeeSalaryDetails)
class EmployeeSalaryDetailsAdmin(AbstractModelAdmin):
    search_fields = ("employee", "employee__first_name")

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(models.EmployeeTypes)
class EmployeeTypesAdmin(AbstractModelAdmin):
    list_display = ["employee_type"]
    search_fields = ("employee_type",)


@admin.register(models.EmployeeAddressDetails)
class EmployeeAddressDetailsAdmin(AbstractModelAdmin):
    search_fields = ("employee", "employee__number")

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(models.EmployeeWorkHistoryDetails)
class EmployeeWorkHistoryDetailsAdmin(AbstractModelAdmin):
    search_fields = ("employee", "employee__number")

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(models.EmployeeReportingManager)
class ReportingManagerAdmin(AbstractModelAdmin):
    search_fields = ("employee",)
    list_filter = ("manager_type",)



@admin.register(models.EmployeeFamilyDetails)
class EmployeeFamilyDetailsrAdmin(AbstractModelAdmin):
    search_fields = ("employee",)    



@admin.register(models.EmployeeDocuments)
class EmployeeDocumentAdmin(AbstractModelAdmin):
    search_fields = ("employee",)    
    
    def __init__(self, model, admin_site) -> None:
            super().__init__(model, admin_site)
            self.get_list_display(include_all_fields=True)

@admin.register(models.DocumentsTypes)
class DocumentsTypesAdmin(AbstractModelAdmin):    
    
    def __init__(self, model, admin_site) -> None:
            super().__init__(model, admin_site)
            self.get_list_display(include_all_fields=True)


@admin.register(models.EmployeeDocumentationWork)
class EmployeeDocumentationWorkAdmin(AbstractModelAdmin):
    search_fields = ("employee",)    
    
    def __init__(self, model, admin_site) -> None:
                super().__init__(model, admin_site)
                self.get_list_display(include_all_fields=True)


@admin.register(models.EmployeeResignationDetails)
class EmployeeResignationDetailsAdmin(AbstractModelAdmin):
    search_fields = ("employee", "employee__number")

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)

from django.contrib import admin

from core.admin import AbstractModelAdmin

from .models import (
    Announcements,
    AuditorDetails,
    AuditorTypes,
    BankAccountTypes,
    BankDetails,
    CompanyDirectorDetails,
    CompanyGrades,
    CustomAddressDetails,
    Departments,
    Designations,
    EntityTypes,
    Policies,
    SecretaryDetails,
    StatutoryDetails,
    SubDepartments,
    LoggingRecord,
    # CompanyPolicyDocuments,
    # CompanyPolicyTypes
)


@admin.register(CustomAddressDetails)
class CustomAddressDetailsAdmin(admin.ModelAdmin):
    """
    CustomAddressDetails Admin View

    SURESH, 06.01.2023
    """

    list_display = (
        "company",
        "address_title",
        "address_line1",
        "address_line2",
        "country",
        "state",
        "city",
        "pincode",
    )


class SubDepartmentsInline(admin.TabularInline):
    model = SubDepartments


@admin.register(Departments)
class CompanyDepartmentsAdmin(admin.ModelAdmin):
    inlines = [
        SubDepartmentsInline,
    ]
    ...


@admin.register(SubDepartments)
class CompanySubDepartmentsAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "is_deleted",
        "name",
        "slug",
        "department",
    ]
    list_filter = ("is_deleted", "department")
    # list_select_related = True


@admin.register(Designations)
class CompanyDesignationsAdmin(admin.ModelAdmin):
    ...


@admin.register(CompanyGrades)
class CompanyGradesAdmin(admin.ModelAdmin):
    ...


@admin.register(Announcements)
class CompanyAnnouncementsAdmin(admin.ModelAdmin):
    ...


@admin.register(Policies)
class CompanyPoliciesAdmin(admin.ModelAdmin):
    ...


@admin.register(EntityTypes)
class EntityTypesAdmin(admin.ModelAdmin):
    ...


@admin.register(StatutoryDetails)
class CompanyStatutoryDetailsAdmin(admin.ModelAdmin):
    ...


@admin.register(CompanyDirectorDetails)
class CompanyDirectorDetailsAdmin(admin.ModelAdmin):
    ...


@admin.register(AuditorTypes)
class AuditorTypesAdmin(admin.ModelAdmin):
    ...


@admin.register(AuditorDetails)
class CompanyAuditorDetailsAdmin(admin.ModelAdmin):
    ...


@admin.register(SecretaryDetails)
class CompanySecretaryDetailsAdmin(admin.ModelAdmin):
    ...


@admin.register(BankAccountTypes)
class BankAccountTypesAdmin(AbstractModelAdmin):
    search_fields = ("account_type",)

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(BankDetails)
class BankDetailsAdmin(admin.ModelAdmin):
    ...

@admin.register(LoggingRecord)
class LoggingRecordAdmin(admin.ModelAdmin):
    ...
    
# @admin.register(CompanyPolicyDocuments)
# class CompanyPolicyDocumentsAdmin(admin.ModelAdmin):
#     ...

# @admin.register(CompanyPolicyTypes)
# class CompanyPolicyTypesAdmin(admin.ModelAdmin):
#     ...
    

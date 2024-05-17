from django.contrib import admin

# Register your models here.
from core.admin import AbstractModelAdmin

from .models import (
    # EmployeeLops,
    EmployeeComplianceNumbers,        
    EpfSetup,
    Esi,
    HealthEducationCess,
    PaySalaryComponents,
    ProfessionTax,
    Regime,
    StatesTaxConfig,
    PayrollInformation,    
    TaxDetails,
    Reimbursement,        
)


@admin.register(EpfSetup)
class EpfSetupAdmin(AbstractModelAdmin):
    list_display = (
        "company",
        "epf_number",
        "employer_contribution",
        "employee_contribution",
        "is_employer_contribution_in_ctc",        
    )
    search_fields = (
        "epf_number",
        "company",
    )
    list_filter = ("epf_number", "company")
    filter_horizontal = ()


@admin.register(Esi)
class EsiAdmin(AbstractModelAdmin):
    list_display = (
        "company",
        "esi_no",
        "employee_contribution_pct",
        "employer_contribution_pct",
        "is_employer_contribution_in_ctc",   
    )
    search_fields = (
        "esi_no",
        "company",
    )
    list_filter = ("esi_no", "company")
    filter_horizontal = ()


@admin.register(ProfessionTax)
class ProfessionTaxAdmin(AbstractModelAdmin):
    list_display = (
        "company",
        "state",
        "is_enabled",
    )
    search_fields = (
        "state",
        "company",
    )
    list_filter = ("state", "company")
    filter_horizontal = ()


@admin.register(PaySalaryComponents)
class PaySalaryComponentsAdmin(AbstractModelAdmin):
    list_display = (
        "company",
        "earning_type",
        "component_name",
        "name_on_payslip",
        "calculation_type",
        "flat_amount",
        "pct_of_basic",
        "threshold_base_amount",
        "is_active",
        "is_part_of_salary_structure",
        "is_taxable",
        "is_prorated",
        "is_part_of_flexible_plan",
        "is_part_of_epf",
        "is_part_of_esi",
        "is_visible_on_payslip",
    )
    search_fields = (
        "component_name",
        "name_on_payslip",
        "company",
    )
    list_filter = ("component_name", "company")
    filter_horizontal = ()



@admin.register(EmployeeComplianceNumbers)
class EmployeeComplianceNumbersAdmin(AbstractModelAdmin):
    list_display = (
        "employee",        
        "uan_num",
        "esi_num",
        "nominee_name",
        "nominee_rel",
        "nominee_dob",
    )


@admin.register(Reimbursement)
class ReimbursementAdmin(AbstractModelAdmin):
    list_display = [field.name for field in Reimbursement._meta.get_fields()]


@admin.register(PayrollInformation)
class PayrollInformationAdmin(AbstractModelAdmin):
    search_fields = ("employee",)
    list_filter = ("employee",)

    list_display = (
        "get_first_name","month_year",                
    )
    def get_first_name(self, obj):
        return obj.employee.first_name



admin.site.register([Regime, HealthEducationCess,StatesTaxConfig,TaxDetails])

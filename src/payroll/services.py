from .models import EpfSetup, Esi, PaySalaryComponents, ProfessionTax, TaxDetails, StatesTaxConfig, PayslipFields, PayslipTemplates, PayslipTemplateFields
import datetime
from django.utils import timezone
from django.db import transaction

# this file is created to store the epf, esi, pt from company when ever it is created check the example of init_leave



def init_epfsetup(self="", company=""):
    if not company:
        return
    EpfSetup.objects.create(company=company, epf_number=None)


def init_esi(self="", company=""):
    if not company:
        return
    Esi.objects.create(
        company=company,
        esi_no=None,
        employee_contribution_pct=0.75,
        employer_contribution_pct=3.25,
    )


def init_professiontax(self, company):
    if not company:
        return
    states = StatesTaxConfig.objects.all().first()
    ProfessionTax.objects.create(company=company, state=states)



def init_paysalarycomponents(self="", company=""):
    if not company:
        return
    # need to store multiple objects with single company
    salary_component = [
        PaySalaryComponents(
            company=company,
            earning_type="Earning",
            component_name="Basic",
            name_on_payslip="Basic",
            pct_of_basic=50,            
            is_default=True,
            is_part_of_salary_structure=True,
            is_taxable=True,
            is_prorated=True,
            is_part_of_flexible_plan=True,
            is_part_of_epf=True,
            is_part_of_esi=True,
            is_visible_on_payslip=True
        ),
        PaySalaryComponents(
            company=company,
            earning_type="Earning",
            component_name="Conveyance",
            name_on_payslip="Conveyance Allowance",
            calculation_type=1,
            flat_amount=1600,
            is_default=True,
            is_part_of_salary_structure=True,
            is_taxable=True,
            is_prorated=True,
            is_part_of_flexible_plan=True,
            is_part_of_epf=True,
            is_part_of_esi=True,
            is_visible_on_payslip=True            
        ),
        PaySalaryComponents(
            company=company,
            earning_type="Employee Deduction",
            component_name="ESI Employee Contribution",
            name_on_payslip="ESI",
            calculation_type=0,
            threshold_base_amount=21000,
            is_default=True,
            is_part_of_salary_structure=True,
            is_taxable=True,
            is_prorated=True,
            is_part_of_flexible_plan=True,
            is_part_of_epf=True,
            is_part_of_esi=True,
            is_visible_on_payslip=True
        ),
        PaySalaryComponents(
            company=company,
            earning_type="Employer Deduction",
            component_name="ESI Employer Contribution",
            name_on_payslip="ESI Employer Contribution",
            calculation_type=0,
            threshold_base_amount=21000,
            is_default=True,
            is_part_of_salary_structure=True,
            is_taxable=True,
            is_prorated=True,
            is_part_of_flexible_plan=True,
            is_part_of_epf=True,
            is_part_of_esi=True,
            is_visible_on_payslip=True
        ),
        PaySalaryComponents(
            company=company,
            earning_type="Earning",
            component_name="HRA",
            name_on_payslip="HRA",
            pct_of_basic=40,
            is_default=True,
            is_part_of_salary_structure=True,
            is_taxable=True,
            is_prorated=True,
            is_part_of_flexible_plan=True,
            is_part_of_epf=True,
            is_part_of_esi=True,
            is_visible_on_payslip=True
        ),
        PaySalaryComponents(
            company=company,
            earning_type="Employee Deduction",
            component_name="PF Employee Contribution",
            name_on_payslip="Provident Fund",
            calculation_type=0,
            threshold_base_amount=15000,
            is_default=True,
            is_part_of_salary_structure=True,
            is_taxable=True,
            is_prorated=True,
            is_part_of_flexible_plan=True,
            is_part_of_epf=True,
            is_part_of_esi=True,
            is_visible_on_payslip=True
        ),
        PaySalaryComponents(
            company=company,
            earning_type="Employer Deduction",
            component_name="PF Employer Contribution",
            name_on_payslip="PF Employer Contribution",
            calculation_type=0,
            threshold_base_amount=15000,
            is_default=True,
            is_part_of_salary_structure=True,
            is_taxable=True,
            is_prorated=True,
            is_part_of_flexible_plan=True,
            is_part_of_epf=True,
            is_part_of_esi=True,
            is_visible_on_payslip=True
        ),
        # PaySalaryComponents(
        #     company=company,
        #     earning_type="Employee Deduction",
        #     component_name="Professional Tax",
        #     name_on_payslip="Professional Tax",
        #     calculation_type=0,
        #     threshold_base_amount=15000,
        #     is_default=True,
        # ),
    ]

    PaySalaryComponents.objects.bulk_create(salary_component)


def init_taxdetails(self="", company=""):
    if not company:
        return
    TaxDetails.objects.create(
        on_company=company       
    )


def init_payslip_fields(self="", company=""):
    default_fields =  {
        'EPF': [True, 2],
        'ESI': [True, 4],
        'PAN': [True, 8],
        'UAN': [True, 6],
        'Basic': [True, 27],
        'Email': [False, 17],
        'Other': [False, 43],
        'Phone': [False, 21],
        'total': [True, 33],
        'Gender': [False, 13],
        'Arrears': [False, 32],
        'LOP_Days': [False, 16],
        'Location': [False, 9],
        'Bank_Name': [False, 10],
        'Incentive': [False, 31],
        'Annual_CTC': [True, 15],
        'Deductions': [True, 36],
        'Department': [False, 5],
        'Net_Salary': [True, 45],
        'companyCin': [False, 55],
        'Designation': [True, 7],
        'Employee_Id': [True, 1],
        'companyLogo': [False, 16],
        'companyName': [True, 19],
        'DateOf_Birth': [False, 11],
        'Gross_Salary': [True, 34],
        'profileImage': [False, 18],
        'Employee_Loan': [False, 42],
        'Employee_Name': [True, 23],
        'DateOf_Joining': [True, 3],
        'Income_Tax_TDS': [True, 40],
        'companyAddress': [True, 64],
        'Bank_Account_No': [True, 12],
        'Earnings_Salary': [True, 35],
        'Professional_Tax': [True, 39],
        'Total_Deductions': [True, 44],
        'Special_Allowance': [True, 30],
        'Total_Working_Days': [False, 14],
        'Net_Salary_In_Words': [True, 46],
        'Conveyance_Allowance': [True, 29],
        'House_Rent_Allowance': [True, 28],
        'Employee_Provident_Fund': [True, 37],
        'Employee_State_Insurance': [True, 38],
        'Salary_Advance_Deduction': [False, 41],
        'PayslipForThe_MonthOf_Jan-2024(Heading/Title)': [True, 25],
        '(Pay_Cycle:21_-Dec-2023To20-Jan-2024)_(Heading/Title)': [False, 22]
                            }
                    
    payslips_fields_obj, payslips_created = PayslipFields.objects.get_or_create(name = "default_all_fields", company=company, defaults={'fields_list':default_fields})

def init_payslip_templates(self="", company=""):
    payslips_templates_obj, payslips_templates_created = PayslipTemplates.objects.get_or_create(name="default_template", path="paysliptemplateone", company=company)

def init_default_list(self="", company=""):
    PayslipTemplateFields.objects.filter(company=company).delete()
    template_obj = PayslipTemplates.objects.filter(company=company).first()
    fields = {'EPF': True,
    'ESI': True,
    'PAN': True,
    'UAN': True,
    'Basic': True,
    'Email': True,
    'Other': True,
    'Phone': True,
    'total': True,
    'Gender': True,
    'Arrears': True,
    'LOP_Days': True,
    'Location': True,
    'Incentive': True,
    'Annual_CTC': True,
    'Deductions': True,
    'Department': True,
    'Net_Salary': True,
    'companyCin': True,
    'Designation': True,
    'Employee_Id': True,
    'companyLogo': True,
    'companyName': True,
    'DateOf_Birth': True,
    'Gross_Salary': True,
    'profileImage': True,
    'Employee_Loan': True,
    'Employee_Name': True,
    'DateOf_Joining': True,
    'Income_Tax_TDS': True,
    'companyAddress': True,
    'Bank_Account_No': True,
    'Earnings_Salary': True,
    'Professional_Tax': True,
    'Total_Deductions': True,
    'Special_Allowance': True,
    'Total_Working_Days': True,
    'Net_Salary_In_Words': True,
    'Conveyance_Allowance': True,
    'House_Rent_Allowance': True,
    'Employee_Provident_Fund': True,
    'Employee_State_Insurance': True,
    'Salary_Advance_Deduction': True,
    'PayslipForThe_MonthOf_Jan-2024(Heading/Title)': True,
    '(Pay_Cycle:21_-Dec-2023To20-Jan-2024)_(Heading/Title)': True}
    PayslipTemplateFields.objects.create(name='Default Payslip', templates=template_obj, fields = fields, company=company, is_selected=True)

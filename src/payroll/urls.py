from django.urls import path

from payroll.web_views import (    
    activeEmployees,
    # createPayRun,
    departments,
    designations,
    employeeBankDetail,
    employeeLopDetail,
    employeePayslips,
    employeePayslipsDetail,
    employeeSalary,
    employeeSalaryEdit,
    esiComplianceReport,
    importOvertimeEmployees,
    # By Uday Shankar Start
    manageEmployees,
    importLeaveEmployees,
    profileViewEmployees, 
    profileEditEmployees, 
    profileAddEmployees, 
    importDataEmployees,
    repAllMonthTDSReport,
    repGratutyReports,
    repHoldSalary,
    savingAllEmpForms,
    savingDeclarationSetup, 
    taxDetailsEdit, 
    organizationSetupEdit, 
    repPayrollOverview,    
    repEmpReports,
    repPtSummary,
    repEpfSummary,
    repEsiSummary,
    repPtSlab,
    leaveReportsView,
    # By Uday Shankar End
    epfDetails,
    epfDetailsEdit,
    esiDetails,
    esiDetailsEdit,
    organizationView,
    payrollMaster,
    paySchedule,
    payScheduleEdit,
    profTaxes,
    profTaxesEdit,
    runPayroll,
    salComponent,
    salComponentAdd,
    salComponentEdit,
    singleSalComponent,
    taxDetails,
    employeeBankDetailEdit,
    rollbackPayroll,
    DashboardView,
    repAuditReport,
    repMissingInfoReport,
    repSalaryInfoReport,    
    repVarianceReport,
    repLogReport,
    savingDeclarationForms,
    savingUserSubmittedForms,
    savingApproveEmpForms,
    reimbursement_employee,
    complianceGovtReport,
    importVariablePayEmployees
)



urlpatterns = [
    #######################################
    # Web urls
    #######################################
    path(
        "epf-details/",
        epfDetails,
        name="epf_details",
    ),
    path(
        "epf-details-edit/<int:epfId>",
        epfDetailsEdit,
        name="epf_details_edit",
    ),
    path(
        "esi-details/",
        esiDetails,
        name="esi_details",
    ),
    path(
        "esi-details-edit/<int:esiId>", 
         esiDetailsEdit, 
         name="esi_details_edit"
         ),
    path(
        "professional-taxes/",
        profTaxes,
        name="professional_taxes",
    ),
    path(
        "professional-tax-edit/<int:ptId>",
        profTaxesEdit,
        name="professional_taxes_edit",
    ),
    path(
        "salary-component/",
        salComponent,
        name="salary_component",
    ),
    path(
        "salary-component-edit/<int:sal_comp_id>",
        salComponentEdit,
        name="salary_component_edit",
    ),
    path(
        "salary-component-view/<int:sal_comp_id>",
        singleSalComponent,
        name="salary_component_view",
    ),
    path(
        "salary-component-add/",
        salComponentAdd,
        name="salary_component_add",
    ),
    path(
        "active-employees/",
        activeEmployees,
        name="active_employees_view",
    ),
    path(
        "rollback-payroll/",
        rollbackPayroll,
        name="rollback_payroll",
    ),
    path(
        "compliance-report/",
        complianceGovtReport,
        name="compliance_govt_report",
    ),
    # By Uday Shankar Start
    path(
        "manage-employees/",
        manageEmployees,
        name="manage_employees_view",
    ),
    path(
        "import-leave-employees/",
        importLeaveEmployees,
        name="import_leave_employees_view",
    ),
    path(
        "import-overtime-employees/",
        importOvertimeEmployees,
        name="import_overtime_employees_view",
    ),
     path(
        "import-variable-pay-employees/",
        importVariablePayEmployees,
        name="import_variable_pay_employee_view",
    ),
    path(
        "profile-edit-employees/<int:emp_id>",
        profileEditEmployees,
        name="profile_edit_employees",
    ),
    path(
        "profile-view-employees/<int:emp_id>",
        profileViewEmployees,
        name="profile_view_employees",
    ),
    path(
        "profile-add-employees/",
        profileAddEmployees,
        name="profile_add_employee",
    ),
    path(
        "import-data-employees/",
        importDataEmployees,
        name="import_data_employee",
    ),
    path(
        "organization/tax-details-edit/",
        taxDetailsEdit,
        name="tax_details_edit",
    ),
    path(
        "organization/organization-setup-edit/",
        organizationSetupEdit,
        name="organization_setup_edit",
    ),
    path(
        "reports/payroll-overview/",
        repPayrollOverview,
        name="rep_payroll_overview",
    ),
    path(
        "reports/epf-summary/",
        repEpfSummary,
        name="rep_epf_summary",
    ),
    path(
        "reports/esi-summary/",
        repEsiSummary,
        name="rep_esi_summary",
    ),
    path(
        "reports/emp-reports/",
        repEmpReports,
        name="rep_emp_reports",
    ),
    path(
        "reports/pt-summary/",
        repPtSummary,
        name="rep_pt_summary",
    ),   
  
    path(
        "reports/pt-slab/",
        repPtSlab,
        name="rep_pt_slab",
    ),

    path(
        "reports/all_monthly_tds/",
        repAllMonthTDSReport,
        name="repAllMonthTDSReport",
    ),
    
    path(
        "reports/hold_salary/",
        repHoldSalary,
        name="repHoldSalary",
    ),        

    path(
        "reports/leave/reports/",
        leaveReportsView,
        name="leave_report",
    ),

    path(
        "reports/gratuty/",
        repGratutyReports,
        name="gratuty_report",
    ),    
    
    path(
        "saving/declaration/forms/",
        savingDeclarationForms,
        name="saving_declaration_forms",
    ),
    path(
        "saving/declaration/setup/",
        savingDeclarationSetup,
        name="saving_declaration_setup",
    ),    
    
    path(
        "saving/declaration/user-submitted/<int:id>",
        savingUserSubmittedForms,
        name="user_submitted_forms",
    ),
    
    path(
        "saving/declaration/approve-employee/forms/",
        savingApproveEmpForms,
        name="approve_employee_form",
    ),
    path(
        "saving/declaration/submitted-employee/forms/",
        savingAllEmpForms,
        name="saving_all_employee_forms",
    ),
    path(
        "reports/audit-report",
        repAuditReport,
        name="audit_report"
    ),
    path(
        "reports/missing-info-report",
        repMissingInfoReport,
        name="missing_info_report"
    ),
    path(
        "reports/salary-info-report",
        repSalaryInfoReport,
        name="salary_info_report"
    ),
    # path(
    #     "reports/monthly-tds-report",
    #     repMonthlyTDSReport,
    #     name="monthly_tds_report"
    # ),    
    # path(
    #     "reports/salary-breakup-report",
    #     repSalaryBreakupReport,
    #     name="salary_breakup_report"
    # ),  

    path(
        "reports/esi-compliance-report",
        esiComplianceReport,
        name="esi_compliance_report"
    ),     
    path(
        "reports/variance-report",
        repVarianceReport,
        name="variance_report"
    ), 
    path(
        "reports/log-report",
        repLogReport,
        name="log_report"
    ),        
    path(
        "employee-salary/<int:id>",
        employeeSalary,
        name="employee_salary",
    ),
    path(
        "employee-salary-edit/<int:id>",
        employeeSalaryEdit,
        name="employee_salary_edit",
    ),
    path(
        "employee-bank-details/<int:id>",
        employeeBankDetail,
        name="employee_bank_details",
    ),
    path(
        "employee-bank-details-edit/<int:id>",
        employeeBankDetailEdit,
        name="employee_bank_details_edit",
    ),
    path(
        "employee-lop-details/<int:id>", employeeLopDetail, name="employee_lop_details"
    ),
    path("employee-payslips/<int:emp_id>", employeePayslips, name="employee_payslips"),
    path(
        "employee-payslip-view/",
        employeePayslipsDetail,
        name="employee_payslips_details",
    ),
    path("run-payroll/", runPayroll, name="run_payroll"),
    # path("create-pay-run/", createPayRun, name="create_pay_run"),
    path("payroll-master/", payrollMaster, name="payroll_master"),
    
    path("organization/", organizationView, name="organization_view"),
    path("dashboard/<int:company_id>/<str:token>", DashboardView, name="Dashboard_view"),
    
    path("reimbursement/", reimbursement_employee, name="reimbursement"),


    path("organization/pay-schedule/", paySchedule, name="pay_schedule"),
    path("organization/pay-schedule-edit/", payScheduleEdit, name="pay_schedule_edit"),
    
    path("organization/tax-details/", taxDetails, name="tax_details"),
    path("organization/departments/", departments, name="departments"),
    path("organization/designations/", designations, name="designations"),
    
]

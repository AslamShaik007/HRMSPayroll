from django.urls import path

from payroll.api_views import (
    ActiveEmployees,
    CnameCimg,
    EmployeeBulkLops,
    EmployeeBulkVariablePay,    
    EmployeeLop,
    EmployeeViewSalary,
    EpfDetailsRetrieveUpdateView,
    EpfDetailsRetriveView,
    EsiComplianceApi,
    EsiComplianceReminder,
    EsiDetailsRetrieveUpdateView,
    EsiDetailsRetriveView,
    GetEmployeeDescription,
    GetPaySlipDetail,
    GetPaySlipList,
    GetPayrollSummary,
    GetTaxDetails,
    PaySalaryComponentListCreateView,
    PaySalaryComponentRetrieveUpdateView,   
    ProfessionTaxsRetrieveUpdateView ,
    BankDetailsRetrieveView,
    CheckRunPayroll,    
    EmployeeBulkImport,
    PayScheduleView,
    SalaryInfoReportApi,
    TaxDetailsView,
    DepartmentListCreateAPIView,
    EmployeesList,
    EmployeeUpdateStatus,
    AddEmployee,   
    GetEmpCount,
    GetPayDay,
    GetNoOfPayslipPerMonth,
    GetEmpPayrollAnalytics,
    GetDepartmentCount,
    GetNetSalaryCount,
    GetEmpCountBySalaryRange,
    GetActiveInactiveEmp,
    VarianceReportApi,
    getCompliancePaidReport,
    getListofPayslipsForEmployeeApi,
    getRepVarianceReportUd,    
    CheckPayrollExecuted,
    CheckPayrollMaster,
    InvestmentDeclarationUpdateViewAdmin,
    ThirdPartyData,
    ThirdPartyDataV2,
    StateProfessionalTax,
    LeaveReport,
    ManageEmployees,
    PayrollOverviewApi,
    EpfSummaryApi,
    EsiSummaryApi,
    PtSummaryApi,
    PtSlabApi,
    EmployeeReportsApi,
    DepartmentEmployees,
    EmployeeOTApi,
    EmployeeGratuity,
    MissingInfoApi,    
    PayrollEmps,
    getSavingDeclarationEmployees,
    getTaxStatesList,
    processPayrollApi,
    rollbackPayrollApi,
    checkNullUANEmployees,
    get_payroll_completed_month_year_list,
    MissingEmployeeInfo,
    GetPayslip,
    HoldSalaryReport,
    InvestmentDeclarationUpdateResubmit,
    runPayrollApi,
    EmployeeAllLops,
    GetPayrollMonthYear,
    GetPaySlipFields,
    GetPayslipTemplates,
    TemplateFields,
    EpfEmployeesApi,
    EmployeesHold,
    EmpTdsReportV2,
    PayRollAddComment,
    PayrollOverviewApiV2,
    IciciBankReport,
    PtSlabApiV2,
    EsiComplianceApiV2,
    EmployeeEsiResignation,
    EsiResignationChoices,
)


urlpatterns = [
   
    #######################################
    # API urls
    #######################################
    # Payroll module

    path("cname_cimg/<int:company_id>/", CnameCimg.as_view(), name="cname_cimg"),    
    path(
        "epf_details/<int:company_id>/",
        EpfDetailsRetriveView.as_view(),
        name="get_epf_details",
    ),
    path(
        "update_epf_details/<int:id>/",
        EpfDetailsRetrieveUpdateView.as_view(),
        name="update_epf_details",
    ),
    path(
        "esi_details/<int:company_id>/",
        EsiDetailsRetriveView.as_view(),
        name="get_esi_details",
    ),
    path(
        "update_esi_details/<int:id>/",
        EsiDetailsRetrieveUpdateView.as_view(),
        name="update_esi_details",
    ),
    path(
        "profession_tax_details/<int:company_id>/",
        ProfessionTaxsRetrieveUpdateView,
        name="get_profession_tax_details",
    ),
    path(
        "update_profession_tax_details/<int:id>/",
        ProfessionTaxsRetrieveUpdateView,
        name="update_profession_tax_details",
    ),
    path(
        "get_bank_details/<int:id>/",
        BankDetailsRetrieveView,
        name="get_bank_details",
    ),
    path(
        "pay_salary_component/<int:company_id>/",
        PaySalaryComponentListCreateView.as_view(),
        name="get_pay_salary_components",
    ),
    path(
        "pay_salary_component_update_retrive/<int:id>/",
        PaySalaryComponentRetrieveUpdateView.as_view(),
        name="update_pay_salary_component",
    ),
    # EMPLOYEE MODULE   
    path(
        "active_employees/<int:company_id>/",
        ActiveEmployees.as_view(),
        name="active_employees",
    ),
    path(
        'department_emps/',
        DepartmentEmployees.as_view(),
        name = "department_emps",
    ),

    path(
        'run_payroll_api',
        runPayrollApi.as_view(),
        name = "runPayrollApi",
    ),
  
    # salary details
    path(
        "employees/view_salary/<int:id>/",
        EmployeeViewSalary.as_view(),
        name="employee_view_salary",
    ),

    path(
        "get_employee_few_info/",
        GetEmployeeDescription.as_view(),
        name="get_employee_few_info",
    ),
 
    # LOPSetup
    path(
        "employee_lops/<int:emp_id>/",
        EmployeeLop.as_view(),
        name="Employee_Lop",
    ),
    path(
        "employee_lops/",
        EmployeeAllLops.as_view(),
        name="Employee_all_lops",
    ),
    path(
        "emp_bulk_import/",EmployeeBulkImport.as_view(),name="Employee_Bulk_Import",
    ),
    path("emp_bulk_lops/", EmployeeBulkLops.as_view(),name="employee_bulk_lop"),    
    path("emp_bulk_variable_pay/", EmployeeBulkVariablePay.as_view(),name="emp_bulk_variable_pay"),

    # API to check if payroll can be run    
    path(
        "check_can_payroll_run/<int:company_id>/",
        CheckRunPayroll,
        name="check_can_payroll_run",
    ),
    # API to process payroll
    path(
        "process_payroll/",
        processPayrollApi.as_view(), 
        name="process_payroll",
    ),
    path(
        "rollback_payroll/",
        rollbackPayrollApi.as_view(), 
        name="rollback_payroll",
    ),
    path(
        "get_list_of_payslips/",
        getListofPayslipsForEmployeeApi.as_view(), 
        name="get_list_of_payslips",
    ),
    path("pay-schedule/<int:cmp_id>/",PayScheduleView.as_view(),name="pay_schedule"),    
    path("tax_details/<int:cmp_id>/",TaxDetailsView.as_view(),name="tax_details"),
    path("department/<int:cmp_id>",DepartmentListCreateAPIView.as_view(),name="department_list_create"),
  
    
    #AJAX URLS
    #these ajax urls will filters by company id and status

    path("employees_list",EmployeesList.as_view(),name="employee_list"),
    path("employees_update_status",EmployeeUpdateStatus.as_view(),name="employee_update_status"),
    path("add_employee",AddEmployee.as_view(),name="add_employee_api"),
        
    path("check_payroll_executed",CheckPayrollExecuted.as_view(),name="check_payroll_executed"),
    path("check_payroll_master",CheckPayrollMaster.as_view(),name="check_payroll_master"),    
    path("get_employee_saving_list",getSavingDeclarationEmployees.as_view(),name="get_employee_saving_list"),

    path("update_employee_saving_resubmit",InvestmentDeclarationUpdateResubmit.as_view(),name="update_employee_saving_resubmit"),


    # Mobile URLs
   
    path(
        "get_pay_slips_list/",
        GetPaySlipList            
    ), 

    path(
        "get_pay_slip_detail/",
        GetPaySlipDetail        
    ),    
    path(
        "get_tax_details/",
        GetTaxDetails
    ),
    path(
        "get_payroll_summary/",
        GetPayrollSummary
    ),

    path(
        "get-emp-count/",
        GetEmpCount,
        name="get_emp_count",
    ),    
    
    path(
        "get-pay-day/",
        GetPayDay,
        name="get_pay_day",
    ),    
    
    
    path(
        "get-payslip-monthly/",
        GetNoOfPayslipPerMonth,
        name="get_no_of_payslip_per_month",
    ),    
    
    
    path(
        "get-emp-payroll-analytics/",
        GetEmpPayrollAnalytics,
        name="get_emp_payroll_analytics",
    ),    
    
    path(
        "get-all-department-count/",
        GetDepartmentCount,
        name="get_all_dep_count",
    ),    
    
    path(
        "get-net-salary/",
        GetNetSalaryCount,
        name="get_net_salary_count",
    ),    
    
    path(
        "get-emp-count-by-salary-range/",
        GetEmpCountBySalaryRange,
        name="get_emp_count_by_salary_range",
    ),    
    
    path(
        "get/active/inactive/employee/",
        GetActiveInactiveEmp,
        name="get_active_inactive_employee",
    ),    
    
    path(
        "get/compliance/paid/report/",
        getCompliancePaidReport,
        name="get_compliance_paid_report",
    ),    
    
    path(
        "get/variance/report/",
        getRepVarianceReportUd,
        name="get_variance_report",
    ),    

    path(
        "update/investment-declaration/admin/<int:id>/",
        InvestmentDeclarationUpdateViewAdmin.as_view(),
        name="update_investment_declaration_admin",
    ),    
    
    path(
        "get/third-party-data/",
        ThirdPartyData.as_view(),
        name = "third_party_data",
    ),

    path(
        "get/third-party-data/v2",
        ThirdPartyDataV2.as_view(),
        name = "third_party_data_v2",
    ),
    path(
        "get/state-professional-tax",
        StateProfessionalTax.as_view(),
        name = "state-professional-tax",
    ),

    path(
        "get/leave-report",
        LeaveReport.as_view(),
        name="leave-report",
    ),
    path(
        "get/manage-employees",
        ManageEmployees.as_view(),
        name="manage-employees",
        ),
    path(
        "get/payroll-info",
        PayrollOverviewApi.as_view(),
        name = "get-payroll-info",
    ),
    path(
        "get/epf-summary",
        EpfSummaryApi.as_view(),
        name = "get-epf-summary",
    ),
    path(
        "get/esi-summary",
        EsiSummaryApi.as_view(),
        name = "get-esi-summary",
        ),
    path(
        "get/esi-compliance-report",
        EsiComplianceApi.as_view(),
        name = "get-esi-complaince-report",
        ),        
    path(
        "get/pt-summary",
        PtSummaryApi.as_view(),
        name = "get-pt-summary",        
    ),
    path(
        "get/pt-slab",
        PtSlabApi.as_view(),
        name = "get-pt-slab",
    ),
    path(
        "get/pt-slab/v2/",
        PtSlabApiV2.as_view(),
        name = "get-pt-slab-v2",
    ),
    
    path(
        "get/emp-reports",
        EmployeeReportsApi.as_view(),
        name="get-emp-reports",
    ),
    path(
        "emp-ot",
        EmployeeOTApi.as_view(),
        name = "ot-report"
    ),
    path(
        "emp-gratuity",
        EmployeeGratuity.as_view(),
        name = "emp-gratuity",
    ),
    path(
        "get/variance-report",
        VarianceReportApi.as_view(),
        name = "variance-report",
    ),
    path(
        "missing-info",
        MissingInfoApi.as_view(),
        name = "missing-info"
    ),
    # path(
    #     "get-tds-report",
    #     TDSReport.as_view(),
    #     name = "tds-report",
    # ),
    path(
        "salary-info-report",
        SalaryInfoReportApi.as_view(),
        name = "salary-info-report",
    ),
    path(
        "payroll-emps",
        PayrollEmps.as_view(),
        name="payroll-emps",
    ),

     path(
        "get/tax-config/states",
        getTaxStatesList,
        name="get_tax_states_list",
    ),   
    path(
        "get/tds-report-v2",
        EmpTdsReportV2.as_view(),
        name='get-tds-report-v2',
    ),
     path(
        "check-null-uan-employees",
        checkNullUANEmployees.as_view(),
        name='check-null-uan-employees',
    ),
    path(
        "get_payroll_completed_month_year_list",
        get_payroll_completed_month_year_list,
        name='get_payroll_completed_month_year_list',
    ),
    path(
        "get/missing-info",
        MissingEmployeeInfo.as_view(),
        name='get-missing-employee-info'
    ),
    path(
        "get/payslip",
        GetPayslip.as_view(),
        name = "get-payslip" 
    ),
    path(
        "get/hold_salary_report",
        HoldSalaryReport.as_view(),
        name = "get-hold-salary",
    ),
    path(
        "esi_compliance_reminder",
        EsiComplianceReminder.as_view(),
        name = "esi-compliance-reminder",
    ),
    path(
        "get-month-payroll",
        GetPayrollMonthYear.as_view(),
        name = "get-month-payroll"
    ),
    path(
        "get/payslip-fields",
        GetPaySlipFields.as_view(),
        name = "get-payslip-fields",
    ),
    path(
        "get/payslip-templates",
        GetPayslipTemplates.as_view(),
        name = "get-payslip-templates",
    ),
    path(
        "template-fields",
        TemplateFields.as_view(),
        name =  "template-fields",
    ),
    path(
        "epfemployeesapi",
        EpfEmployeesApi.as_view(),
        name="epf-employees-api",
    ),
    path(
        "hold-emps",
        EmployeesHold.as_view(),
        name =  "hold-emps",
    ),
    path(
        'payroll-add-comment',
        PayRollAddComment.as_view(),
        name = 'payroll-add-comment'
    ),
    path(
        'payroll-overview-api-v2',
        PayrollOverviewApiV2.as_view(),
        name='payroll-overview-api-v2'
    ),
    path('icici-bank-report',
        IciciBankReport.as_view(),
        name = 'icici-bank-report'
        ),
    path(
        "get/esi-compliance-report/v2/",
        EsiComplianceApiV2.as_view(),
        name = "get-esi-complaince-report-v2",
        ),
    path(
        "employee-esi-resignation",
        EmployeeEsiResignation.as_view(),
        name='employee-esi-resignation'
    ),
    path(
        'get/esi-resignation-choices',
        EsiResignationChoices.as_view(),
        name = 'esi-resignation-choices'
    )
]

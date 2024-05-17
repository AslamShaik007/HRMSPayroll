from django.urls import path

from leave import views
from leave import v2_views
from leave import dashboard_views

urlpatterns = [
    path(
        "workrule/",
        views.WorkRulesCreateView.as_view(),
        name="create_workrule",
    ),
    path(
        "update/workrule/<int:id>/",
        views.WorkRulesUpdateView.as_view(),
        name="update_workrule",
    ),
    path(
        "workrule/<int:company_id>/",
        views.WorkRulesRetrieveView.as_view(),
        name="get_workrule",
    ),
    path(
        "workrule_choices/",
        views.WorkRuleChoicesCreateView.as_view(),
        name="create_workrule_choices",
    ),
    path(
        "update/workrule_choices/<int:id>/",
        views.WorkRuleChoicesUpdateView.as_view(),
        name="update_workrule_choices",
    ),
    path(
        "workrule_choices/<int:work_rule_id>/",
        views.WorkRuleChoicesRetrieveView.as_view(),
        name="get_workrule_choices",
    ),
    path(
        "retrieve/employee/work_rule/relation/<int:company_id>/",
        views.EmployeeWorkRuleRelationRetrieveView.as_view(),
        name="retrieve_emp_work_rule_relation",
    ),
    path(
        "assign/employee/work_rule/relation/",
        views.EmployeeWorkRuleRelationCreateView.as_view(),
        name="assign_emp_work_rule_relation",
    ),
    path(
        "update/employee/work_rule/relation/",
        views.EmployeeWorkRuleRelationUpdateView.as_view(),
        name="update_emp_work_rule_relation",
    ),
    path(
        "assign/bulk/employee/work_rule/relation/<int:company>/",
        views.EmployeeWorkRuleBulkAPIView.as_view(),
        name="assign_bulk_emp_work_rule_relation",
    ),
    path(
        "get/employee/work_rule/relation/<int:employee_id>/",
        views.EmpGetEmployeeWorkRuleRelationRetrieveView.as_view(),
        name="get_employee_work_rule_relation",
    ),
    path(
        "add/leaverule/",
        views.LeaveRulesCreateView.as_view(),
        name="create_leaverule",
    ),
    path(
        "update/leaverule/<int:id>/",
        views.LeaveRulesUpdateView.as_view(),
        name="update_leaverule",
    ),
    path(
        "get/leaverule/<int:company_id>/",
        views.LeaveRulesRetrieveView.as_view(),
        name="get_leaverule",
    ),
    path(
        "assign/employee/leaverule/relation/<int:company>/",
        views.EmployeeLeaveRulesCreationView.as_view(),
        name="assign_employee_leaverule_relation",
    ),
    path(
        "get/employee/leaverule/relation/<int:employee_id>/",
        views.EmployeeLeaveRuleRelationRetrieveView.as_view(),
        name="retrive_employee_leaves_rule_relation",
    ),
    path(
        "apply/",
        views.LeavesHistoryCreateView.as_view(),
        name="apply_leaves",
    ),
    path(
        "update/history/<int:id>/",
        views.LeavesHistoryUpdateView.as_view(),
        name="update_leaves",
    ),
    path(
        "approve-leave/",
        views.ApproveLeaveMultitenant.as_view(),
        name="update_leaves",
    ),
    path(
        "employee/rule/deletion/",
        views.LeaveRuleDeletion.as_view(),
        name="employee_rule_deletion",
    ),
    path(
        "approve/",
        views.LeavesBulkApprovalView.as_view(),
        name="approve_leaves",
    ),
    path(
        "get/history/<int:employee_id>/",
        views.LeavesHistoryRetrieveView.as_view(),
        name="retrive_leaves_history",
    ),
    path(
        "get/history/company/<int:company_id>/",
        views.CompanyLeavesHistoryRetrieveView.as_view(),
        name="retrive_company_leaves_history",
    ),
    path(
        "view/emp/leaves/",
        views.GetEmpLeavesView.as_view(),
        name="view_emp_leaves",
    ),
    path(
        "emp/monthly/leaves/",
        views.MonthlyLeavesView.as_view(),
        name="employee_monthly_leaves",
    ),
    path("emp/leave_balance/",views.EmployeeLeaveBalance.as_view(),name="employee_leave_balance"),
    path("emp/leave_balance/import/",views.EmployeeLeaveBalanceImport.as_view(),name="employee_leave_balance_import"),  
    path("emp/leave_balance/import_file/",views.EmployeeLeaveBalanceImportFile.as_view(),name="employee_leave_balance_import_file"),  
    
    # V2 Views
    path("v2/get/leaverule/<int:company_id>/", v2_views.LeaveRulesAPIViewV2.as_view(), name="v2_get_leave_rule_company"),
    path("v2/update/leaverule/<int:id>/", v2_views.LeaveRuleDetailsGetUpdateAPIViewV2.as_view(), name="v2_update_leaverule"),
    path("v2/assign/employee/leaverule/relation/<int:company_id>/", v2_views.EmployeeLeaveRuleRelationAPIViewV2.as_view(), name="v2_assign_employee_leaverule_relation"),
    path("v2/get/history/<int:employee_id>/", v2_views.LeavesHistoryRetrieveViewV2.as_view(), name="v2_retrive_leaves_history",),
    path("v2/get/history/company/<int:company_id>/", v2_views.LeavesHistoryCompanyRetrieveViewV2.as_view(), name="v2_retrive_leaves_history",),
    path("v2/get/employee/leaverule/relation/<int:employee_id>/", v2_views.EmployeeLeaveRuleRelationRetrieveViewV2.as_view(), name="v2_retrive_employee_leaves_rule_relation"),
    path("v2/get/employee/work_rule/relation/<int:employee_id>/", v2_views.EmpGetEmployeeWorkRuleRelationRetrieveViewV2.as_view(), name="v2_get_employee_work_rule_relation"),
    
    #work_rule apis
    path("v2/workrule/<int:company_id>/",v2_views.WorkRulesRetrieveViewV2.as_view(),name="v2_get_workrule"),
    path("v2/retrieve/employee/work_rule/relation/<int:company_id>/",v2_views.EmployeeWorkRuleRelationRetrieveViewV2.as_view(),
        name="v2_retrieve_emp_work_rule_relation"),
    path(
        "v2/assign/bulk/employee/work_rule/relation/<int:company>/",v2_views.EmployeeWorkRuleBulkAPIViewV2.as_view(),
        name="v2_assign_bulk_emp_work_rule_relation",
    ),
    path("v2/leaverule/settings/",v2_views.CompanyLeaveRuleSettingsAPIViewV2.as_view(),name="v2_company_leaverule_settings"),
    path("v2/leave/requests/",dashboard_views.AdminLeaveRequestsCountAPIViewV2.as_view(),name="v2_leave_requests"),

]

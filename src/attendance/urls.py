from django.urls import path

from attendance import views
from attendance import v2_views, dashboard_views, biometric_views

urlpatterns = [
    path(
        "add/attendance_rule/",
        views.AttendanceCreateAPIView.as_view(),
        name="attendance_create",
    ),
    path(
        "get/attendance_rule/<int:company_id>/",
        views.AttendanceRulesRetriveView.as_view(),
        name="attendance_list",
    ),
    path(
        "update/attendance_rule/<int:id>/",
        views.AttendanceRetrieveUpdateView.as_view(),
        name="attendance_update",
    ),
    path(
        "retrieve/employee/attendance_rule/relation/<int:company_id>/",
        views.EmployeeAttendanceRuleRelationRetrieveView.as_view(),
        name="retrieve_emp_attendance_rule_relation",
    ),
    path(
        "assign/bulk/employee/attendance_rule/relation/<int:company>/",
        views.EmployeeAttendanceRuleBulkAPIView.as_view(),
        name="assign_update_bulk_emp_attendance_rule_relation",
    ),
    path(
        "get/employee/assigned/attendance_rule/<int:employee_id>/",
        views.EmpAttendanceRuleRetrieveView.as_view(),
        name="get_employee_attendance_rule",
    ),
    path(
        "get/attendance_setting/<int:company_id>/",
        views.AttendanceRuleSettingsRetrieveView.as_view(),
        name="attendance_setting_list",
    ),

    path(
        "get/absent_approvals/<int:company_id>/",
        views.AbsentApprovalCompanyRetrieveViewV2.as_view(),
        name="absent_approvals_list",
    ),    

 path(
        "update/absent_approvals/<int:id>/",
        views.AbsentApprovalCompanyUpdateViewV2.as_view(),
        name="absent_approvals_update",
    ),

    path(
        "update/attendance_setting/<int:id>/",
        views.AttendanceRuleSettingsUpdateView.as_view(),
        name="attendance_setting_update",
    ),
    path(
        "retrieve/clock/history/",
        views.ClockDetailsView.as_view(),
        name="retrieve_clock_history",
    ),
    path(
        "update/check_in/",
        views.EmployeeCheckInView.as_view(),
        name="check_in",
    ),
    path(
        "update/check_out/",
        views.EmployeeCheckOutView.as_view(),
        name="check_out",
    ),
    path(
        "update/clock/history/",
        views.CheckInOutUpdateView.as_view(),
        name="update_clock",
    ),
    path(
        "anamoly/history/",
        views.AnamolyHistoryView.as_view(),
        name="attendance_history",
    ),
    path(
        "resend/reminder/",
        views.AttendanceResendRemiderView.as_view(),
        name="attendance_resend_reminder",
    ),
    path("employee/month/view/", views.AttendanceMontlyEmployeeView.as_view(), name="employee_month_view"),
    path("month/view/", views.AttendanceMontlyManagerHRView.as_view(), name="employee_manager_hr_view"),
    path("month/update/", views.AttendanceMontlyManagerHRView.as_view(), name="employee_manager_hr_update"),
    path("get_update/consolidate_notification_dates/", views.ConsolidateNotificationDatesView.as_view(), name="consolidate_notification_dates",),
    
    # v2 Views
    path("v2/retrieve/clock/history/", v2_views.ClockDetailsViewV2.as_view(), name="v2_retrieve_clock_history"),
    path("v3/retrieve/clock/history/", v2_views.ClockDetailsViewV3.as_view(), name="v2_retrieve_clock_history"),
    path("v2/get/attendance_rule/<int:company_id>/", v2_views.AttendanceRulesAPIViewV2.as_view(), name="v2_attendance_list"),
    path("v2/update/attendance_rule/<int:id>/", v2_views.AttendanceDetailAPIViewV2.as_view(), name="v2_attendance_update"),
    path("v2/retrieve/employee/attendance_rule/relation/<int:company_id>/", v2_views.EmployeeAttendanceRuleRelationRetrieveViewV2.as_view(), name="v2_retrieve_emp_attendance_rule_relation"),
    path("v2/get/employee/assigned/attendance_rule/<int:employee_id>/", v2_views.EmpAttendanceRuleAPIViewV2.as_view(), name="v2_get_employee_attendance_rule"),
    path("v2/attendance/shiftssetup/", v2_views.AttendanceShiftsSetupAPIViewV2.as_view(), name="v2_attendance_shifts_setup"),
    path("v2/vg/logs/", v2_views.VgAttendanceLogsAPIViewV2.as_view(), name="v2_vg_attendance_logs"),
    # path("v2/payschedule/", v2_views.PayScheduleEndDateV2.as_view(), name="v2_payschedule"),
    path("v2/get/timezones/", v2_views.GetAllTimeZoneDetails.as_view(), name="v2_get_timezones"),
    path("v2/get/paycycledates/", v2_views.GetPaycycledates.as_view(), name="v2_get_paycycledates"),
    path("consolidatebuttonstatus/", views.ConsolidateButtonStatus.as_view(), name="consolidate-button-status"),
    
    #Dashboard APIs
    path("emp/clock/details/", dashboard_views.EmployeeClockDetailsView.as_view(), name="emp_clcok_details"),
    path("company/work/shifts/", dashboard_views.CompanyWorkShiftsAPiView.as_view(), name="company_work_shifts"),
    path("company/emp/logins/", dashboard_views.EmployeeCheckinAndCheckoutDetails.as_view(), name="company_emp_logins"),
    path("company/emp/anomolies/", dashboard_views.ManagerAnomomoliesRequests.as_view(), name="company_emp_anomolies"),
    path("company/emp/penalty/", dashboard_views.MonthlyPenaltyDetails.as_view(), name="company_emp_anomolies"),
    
    #Biometric View
    # path("biometric/logs/", biometric_views.BiometricAttandanceLogsAPIView.as_view(), name="biometric_details"),
    path("biometric/logs/export/", biometric_views.BiometricAttandanceLogsExportAPIView.as_view(), name="biometric_details_export"),
    path("biometric/logs/", biometric_views.BiometricAttandanceLogsFiltersAPIView.as_view(), name="biometric_details"),
    
    #keylogger view
    path("keylogger/logs", views.KeyLoggerApi.as_view(), name="keylogger_logs"), 
    path("keylogger/logs/v2", views.KeyLoggerV2.as_view(), name="keylogger_logs"),   

]

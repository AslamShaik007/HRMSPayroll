from django.urls import path

from .views import (
    EmployeeExportView,
    EmployeeReportRetrieveView,
    ExportAttendanceAPIView,
    ExportLeaveHistoryAPIView,
    ExportLeaveHistoryBalanceAPIView,
    ImportLeaveHistoryBalanceAPIView,
)

from .v2_views import EmployeeExportViewV2, EmployeeDynamicReportView, EmployerDynamicReportView

urlpatterns = [
    path(
        "genearate/employee/",
        EmployeeExportView.as_view(),
        name="generate-report",
    ),
    path(
        "get/employee/",
        EmployeeReportRetrieveView.as_view(),
        name="get-report",
    ),
    path(
        "export/leave/logs/",
        ExportLeaveHistoryAPIView.as_view(),
        name="export_company_leave_history",
    ),
    path(
        "export/attendance/log/",
        ExportAttendanceAPIView.as_view(),
        name="export_emp_details",
    ),
    path(
        "export/leave/balance/<int:pk>",
        ExportLeaveHistoryBalanceAPIView.as_view(),
        name="export_emp_balance",
    ),
    path(
        "import/leave/balance",
        ImportLeaveHistoryBalanceAPIView.as_view(),
        name="export_emp_balance",
    ),
    
    
    
    # v2 Views
    path("v2/genearate/employee/", EmployeeExportViewV2.as_view(), name="v2_generate-report"),
    path("employee/dynamic/report/", EmployeeDynamicReportView.as_view(), name="employee_dynamic_report"),
    path("employer/dynamic/report/", EmployerDynamicReportView.as_view(), name="employer_dynamic_report")

]

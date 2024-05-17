from django.urls import path
from aiml_app import views

urlpatterns = [
    path(
        "quick-change-data/",
        views.QuckChangeDataApi.as_view(),
        name="quick_change_data",
    ),
    path(
        "get-payroll-info/",
        views.PayrollInfo.as_view(),
        name = "retrive_payrollinfo",
    ),
    path(
        "get-attendance-info/",
        views.AttendanceInfo.as_view(),
        name = 'retrive_attendanceinfo'
    ),

]
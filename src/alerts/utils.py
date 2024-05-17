from django.conf import settings
from django.db import models as db_models
from .models import Alert

def check_alert_notification(name, sub_module_name, whatsapp=None, email=None, sms=None):
    q_filter = db_models.Q(name=name, desc_name=sub_module_name)
    if whatsapp:
        q_filter &= db_models.Q(is_whatsapp=whatsapp)
    elif email:
        q_filter &= db_models.Q(is_email=email)
    elif sms:
        q_filter &= db_models.Q(is_sms=sms)
    else:
        return False
    alert_query = Alert.objects.filter(q_filter)
    return alert_query.exists()

INITIAL_ALERTS_DATA = {
    "alerts": {
        "AnamoliesGenerator": {
            "desc_name": "Anamolies Generator",  
            "path": str(settings.BASE_DIR.parent / 'scripts/attendance/generate_anamolies.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "AnamolyReportToManager": {
            "desc_name": "Anamoly Report To Manager",  
            "path": str(settings.BASE_DIR.parent / 'scripts/attendance/anamolie_pending_report_to_manager.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "EarlyAndLateCheckInOut": {
            "desc_name": "Early And Late CheckInOut",  
            "path": str(settings.BASE_DIR.parent / 'scripts/attendance/early_and_late_checkout_report.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "EarlyCheckIn": {
            "desc_name": "Early CheckIn",  
            "path": str(settings.BASE_DIR.parent / 'scripts/attendance/early_checkin.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "EarlyCheckOut": {
            "desc_name": "Early CheckOut",  
            "path": str(settings.BASE_DIR.parent / 'scripts/attendance/early_checkout.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "EmployeeCheckInOutReminder": {
            "desc_name": "Employee CheckInOut Reminder", 
            "path": str(settings.BASE_DIR.parent / 'scripts/attendance/employee_checkin_checkout_reminders.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "LeavePendingReminder": {
            "desc_name": "Leave Pending Reminder", 
            "path": str(settings.BASE_DIR.parent / 'scripts/attendance/Leave_pending_emails.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "ManagerWeeklyAttendance": {
            "desc_name": "Manager Weekly Attendance", 
            "path": str(settings.BASE_DIR.parent / 'scripts/attendance/manager_weekly_attendance_reminder.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "WeeklyAttendanceReminder": {
            "desc_name": "Weekly Attendance Reminder", 
            "path": str(settings.BASE_DIR.parent / 'scripts/attendance/weekly_attedance_reminders.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "EmployeeEmptyInfo": {
            "desc_name": "Employee EmptyInfo", 
            "path": str(settings.BASE_DIR.parent / 'scripts/company_profile/employee_empty_info_send_admin.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "RepeatedReminders": {
            "desc_name": "Repeated Reminders", 
            "path": str(settings.BASE_DIR.parent / 'scripts/company_profile/repeated_manager_reminders_to_admin.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "SDapprovalPendingReminder": {
            "desc_name": "Saving Declaration Approval PendingReminder", 
            "path": str(settings.BASE_DIR.parent / 'scripts/investment_declaration/approval_pending_remider_to_hr_admin.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "InCompleteDeclaration": {
            "desc_name": "Incomplete Declaration",
            "path": str(settings.BASE_DIR.parent / 'scripts/investment_declaration/incomplete_declaration_notification.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "ManagerApprovalPending": {
            "desc_name": "Investment Declation Manager Approval Pending",
            "path": str(settings.BASE_DIR.parent / 'scripts/investment_declaration/manager_pending_approval_reminders.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "YearEndSummary": {
            "desc_name": "Investment Declation Year End Summary",
            "path": str(settings.BASE_DIR.parent / 'scripts/investment_declaration/sd_year_end_summary_mails.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "UpComingSubmissionDeadline": {
            "desc_name": "Investment Declation UpComing Submission Deadline",
            
            "path": str(settings.BASE_DIR.parent / 'scripts/investment_declaration/upcoming_submission_deadline.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "PayCycleAfterNotification": {
            "desc_name": "PayCycle After Notification",
            "path": str(settings.BASE_DIR.parent / 'scripts/payroll/send_paycycle_after_notification.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "PayCycleBeforeNotification": {
            "desc_name": "PayCycle Before Notification",
            "path": str(settings.BASE_DIR.parent / 'scripts/payroll/send_paycycle_before_notification.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "AuditReport": {
            "desc_name": "AuditReport",
            "path": str(settings.BASE_DIR.parent / 'scripts/audit_report_mails.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "ExitInterview": {
            "desc_name": "Exit Interview",
            "path": str(settings.BASE_DIR.parent / 'scripts/exit_interview.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "KraNotification": {
            "desc_name": "Kra Notification",
            "path": str(settings.BASE_DIR.parent / 'scripts/kra_notifications.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        },
        "ExitInterview": {
            "desc_name": "Exit Interview",
            "path": str(settings.BASE_DIR.parent / 'scripts/exit_interview.py'),
            "description": "Some Desc",
            "roles": [],
            "interval": "",
            "run_time": [],
            "days": [],
            "week_days": [],
            "is_active": False
        }
    }
}


NOTIFICATION_ALERTS_DATA = [
    {"name":"Company Profile", 'sub_module_name': 'Setup Wizard'},
    {"name":"Company Profile", 'sub_module_name': 'Sign Up'}, 
    {"name":"Company Profile", 'sub_module_name': 'Change Password'}, 
    {"name":"Company Profile", 'sub_module_name': 'Forgot password'}, 
    
    {"name":"Employee Management",'sub_module_name': 'Invite'},
    {"name":"Employee Management",'sub_module_name': 'Add Employee'},
    {"name":"Employee Management",'sub_module_name': 'HRMS/Payroll Status Update'},
    {"name":"Employee Management",'sub_module_name': 'Work Location Update'},
    {"name":"Employee Management",'sub_module_name': 'Department Update'},
    {"name":"Employee Management",'sub_module_name': 'Designation Update'},
    {"name":"Employee Management",'sub_module_name': 'Reporting Manager Update'},
    
    {"name":"My Profile",'sub_module_name': 'Reporting Manager Update'},
    {"name":"My Profile",'sub_module_name': 'Exit Interview'},
    
    {"name":"Saving Declaration",'sub_module_name': 'Form Submission'},
    {"name":"Saving Declaration",'sub_module_name': 'Form Decline/Revoked'},
    {"name":"Saving Declaration",'sub_module_name': 'Form Rejected'},
    {"name":"Saving Declaration",'sub_module_name': 'Form Approved'},
    
    {"name":"Attendance",'sub_module_name': 'Employee Attendance Rule Update'},
    {"name":"Attendance",'sub_module_name': 'Check In'},
    {"name":"Attendance",'sub_module_name': 'Check Out'},
    {"name":"Attendance",'sub_module_name': 'Approvals'},
    
    {"name":"Leave Management",'sub_module_name': 'Employee Leave Rule Update'},
    {"name":"Leave Management",'sub_module_name': 'Apply Leave'},
    {"name":"Leave Management",'sub_module_name': 'Backdated Leave Apply'},
    {"name":"Leave Management",'sub_module_name': 'Leave Approvals'},
    
    {"name":"Performance Review",'sub_module_name': 'Send Form'},
    {"name":"Performance Review",'sub_module_name': 'Manager Review'},
    {"name":"Performance Review",'sub_module_name': 'Revoke Employee'},
    
    {"name":"Calender",'sub_module_name': 'Add Event'},
    {"name":"Calender",'sub_module_name': 'Update Event'},
  ]
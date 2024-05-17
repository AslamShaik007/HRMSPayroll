from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.conf import settings

from attendance.managers import AttendanceRuleManager
from company_profile.models import CompanyDetails
from core.models import AbstractModel
from directory.models import SessionYear
import boto3

class AttendanceRules(AbstractModel):
    company = models.ForeignKey(
        CompanyDetails,
        on_delete=models.CASCADE,
        verbose_name="Company",
        help_text="Enter Primary Key Of CompanyDetails Table",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="Rule Name",
        help_text="Enter Rule Name",
    )

    description = models.CharField(
        max_length=100,
        verbose_name="Description",
        help_text="Enter Description",
        default="This is Default description for the attendance. You can customise this.",
    )

    shift_in_time = models.TimeField(
        verbose_name="Shift In Time",
        help_text="Enter Shift In Time, For Assign To An Employee",
        null=True,
    )

    shift_out_time = models.TimeField(
        verbose_name="Shift Out Time",
        help_text="Enter Shift Out Time, For Assign To An Employee",
        null=True,
    )

    auto_deduction = models.BooleanField(
        verbose_name="Auto Deduction",
        help_text="Enable Auto Deduction",
        default=False,
    )

    enable_anomaly_tracing = models.BooleanField(
        default=False,
        verbose_name="Anomaly Trace Enabled?",
        help_text="A flat to track anamolies based upon the settings",
    )

    grace_in_time = models.CharField(
        max_length=20,
        verbose_name="Grace In Time",
        help_text="Enter Grace In Time in hours and minutes (%H:%M)",
        null=True,
    )

    grace_out_time = models.CharField(
        max_length=20,
        verbose_name="Grace Out Time",
        help_text="Enter Grace Out Time in hours and minutes (%H:%M)",
        null=True,
    )

    full_day_work_duration = models.CharField(
        max_length=20,
        verbose_name="Full Day Work Duration",
        help_text="Enter Full day working time in hours and minutes (%H:%M)",
        null=True,
    )

    half_day_work_duration = models.CharField(
        max_length=20,
        verbose_name="Half Day Work Duration",
        help_text="Enter Half day working time in hours and minutes (%H:%M)",
        null=True,
    )

    max_break_duration = models.CharField(
        max_length=20,
        verbose_name="Maximum Break Duration",
        help_text="Total Break Time taken by the employee",
        null=True,
    )

    max_breaks = models.IntegerField(
        verbose_name="Maximum No.Of Breaks",
        help_text="No Of Breaks Taken By the employee",
        null=True,
    )

    auto_clock_out = models.BooleanField(
        verbose_name="Auto Clock Out",
        help_text="If auto clock out is enabled, after completion of shift it clockout",
        default=False,
    )

    is_default = models.BooleanField(
        verbose_name="Set As Company Default",
        help_text="Enable Company Default",
        default=False,
    )

    effective_date = models.DateField(
        verbose_name="Effective Date",
        help_text="Enter Effective Date",
        null=True,
    )
    enable_over_time = models.BooleanField(
        verbose_name="Enable Over Time",
        help_text="Allow employee to do over time",
        default=False,
    )
    minimum_minitues_to_over_time = models.IntegerField(default=60, null=True, blank=True)
    enable_attendance_selfie = models.BooleanField(
        verbose_name="Enable Attendance Selfie",
        help_text="Allow employee to take selfie while check_in",
        default=False,
    )
    enable_geo_fencing = models.BooleanField(
        verbose_name="Enable Geo Fencing",
        help_text="If Admin enable, show two fields under the section Location, Distance",
        default=False,
    )
    location_address = models.CharField(
        max_length=500,
        verbose_name="Adress for Geo Fencing",
        help_text="employee need to checkin from the address",
        null=True,
    )
    distance = models.IntegerField(
        verbose_name="Distance",
        help_text="Distance in meters to employee checkin",
        null=True,
    )
    longitude = models.CharField(
        max_length=50,
        verbose_name="Logitude",
        help_text="Office Longitude Location",
        null=True,
    )
    latitude = models.CharField(
        max_length=50,
        verbose_name="Latitude",
        help_text="Office Latitude Location",
        null=True,
    )
    enable_comp_off = models.BooleanField(
        verbose_name="Enable Comp Off",
        help_text="If Employee worked in weekends and holidays it will add count to compoff balance in leave rules",
        default=False,
    )
    enable_penalty_rules = models.BooleanField(
        verbose_name="Enable Penalty Rules",
        help_text="If Admin enable, so here some penalty rules will set in another table",
        default=False,
    )
    comp_off_full_day_work_duration = models.CharField(max_length=16, default = '0:0', null=True, blank=True)
    comp_off_half_day_work_duration = models.CharField(max_length=16, default = '0:0', null=True, blank=True)
    minimum_hours_to_consider_ot = models.CharField(max_length=8, default='0:0', blank=True, null=True)
    selected_time_zone = models.CharField(max_length=256, default=settings.TIME_ZONE, null=True, blank=True)

    objects = AttendanceRuleManager()

    class Meta:
        verbose_name = "Attendance Rule"
        verbose_name_plural = "Attendance Rules"

    def __str__(self) -> str:
        return self.name


class PenaltyRules(AbstractModel):
    attendance_rule = models.ForeignKey(
        AttendanceRules,
        related_name="penalty_rules",
        verbose_name="attendance_rule_id",
        on_delete=models.CASCADE,
        help_text="Enter Primary Key Of attendance_rule Table",
        null=True,
    )

    in_time = models.BooleanField(
        default=False,
        verbose_name="In Time",
        help_text="Enable Button For In Time True Or False",
        null=True,
    )

    late_coming_allowed = models.IntegerField(
        verbose_name="Leave Count Allowed",
        help_text="Enter a number of Leave Count Allowed",
        null=True,
    )

    in_penalty_interval = models.IntegerField(
        verbose_name="In penalty Interval",
        help_text="Enter a number of In Penalty Interval",
        null=True,
    )

    in_penalty = models.CharField(
        max_length=100,
        verbose_name="In Penalty",
        help_text="Enter Penalty",
        null=True,
    )

    in_leave_deduction = models.JSONField(null=True, blank=True, default=dict)
    
    out_time = models.BooleanField(
        default=False,
        verbose_name="Out Time",
        help_text="Enable True Or False For Out Time",
        null=True,
    )

    early_leaving_allowed = models.IntegerField(
        verbose_name="Early Leaving Allowed",
        help_text="Enter a Number For Early Leaving Allowed",
        null=True,
    )

    out_penalty_interval = models.IntegerField(
        verbose_name="Out Penalty Interval",
        help_text="Enter a Number For Out Penalty Interval",
        null=True,
    )

    out_penalty = models.CharField(
        max_length=100,
        verbose_name="Out Penalty",
        help_text="Enter Out Penalty",
        null=True,
    )

    out_leave_deduction = models.JSONField(null=True, blank=True, default=dict)

    work_duration = models.BooleanField(
        default=False,
        verbose_name="Work Duration",
        help_text="Enable True Or False For Work Duration",
        null=True,
    )

    shortfall_in_wd_allowed = models.IntegerField(
        verbose_name="ShortFall In WD Allowed",
        help_text="Enter a Number For ShortFall In WD Allowed",
        null=True,
        blank=True,
    )

    work_penalty_interval = models.IntegerField(
        verbose_name="Work Penalty Interval",
        help_text="Enter a Number For Work Penalty Interval",
        null=True,
        blank=True,
    )

    work_penalty = models.CharField(
        max_length=100,
        verbose_name="Word Penalty",
        help_text="Enter a Word Penalty",
        null=True,
        blank=True,
    )

    work_leave_deduction = models.JSONField(null=True, blank=True, default=dict)
    outstanding_breaks_penalty = models.BooleanField(
        default=False,
        verbose_name="Outstanding Breaks Penalty ",
        help_text="Enable True Or False For Outstanding Breaks Penalty ",
        null=True,
    )
    excess_breaks_allowed = models.IntegerField(
        verbose_name="On Of Breaks Allowed",
        help_text="Enter a Number For Work Penalty Interval",
        null=True,
    )
    break_penalty_interval = models.IntegerField(
        verbose_name="Breaks Penalty Interval",
        help_text="Enter a Number For Work Penalty Interval",
        null=True,
    )
    break_penalty = models.CharField(
        max_length=100,
        verbose_name="Breaks Penalty",
        help_text="Enter the Break Penalty",
        null=True,
    )
    break_leave_deduction = models.JSONField(null=True, blank=True, default=dict)
    class Meta:
        verbose_name = "Penalty Rule"
        verbose_name_plural = "Penalty Rules"


class AssignedAttendanceRules(AbstractModel):
    employee = models.ForeignKey(
        "directory.Employee",
        on_delete=models.CASCADE,
        verbose_name="Employee Id",
        help_text="Employe PRimary Key Of Employee",
    )
    session_year = models.ForeignKey(SessionYear, on_delete=models.CASCADE, null=True, blank=True)
    attendance_rule = models.ForeignKey(
        "AttendanceRules",
        on_delete=models.CASCADE,
        related_name="attendance_id",
        verbose_name="Attendance Rules",
        help_text="Enter Attendance Rule Primary Key",
    )

    effective_date = models.DateField(
        verbose_name="Effective Date",
        help_text="Enter Effective Date",
    )

    resend_reminder = models.BooleanField(
        verbose_name="Resend Reminder",
        help_text="Enable Resend Reminder",
        default=False,
    )

    class Meta:
        verbose_name = "Assign Attendance Rule"
        verbose_name_plural = "Assign Attendance Rules"
        unique_together = ("employee", "attendance_rule")

    def __str__(self) -> str:
        return f"{self.employee.name}-{self.attendance_rule.name}"


class AttendanceRuleSettings(AbstractModel):
    """
    this model is used in company profile payroll settings relating to that company
    """
    class CalendarTypeChoice(models.TextChoices):
        CALENDARYEAR = 'calendaryear', 'CalendarYear'
        FINANCIALYEAR = 'financialyear', 'FinancialYear'

    company = models.ForeignKey(
        CompanyDetails,
        on_delete=models.CASCADE,
        verbose_name="Company Id",
        help_text="Enter Primary Key Of CompanyDetails Table",
    )

    attendance_input_cycle_from = models.IntegerField(
        verbose_name="Attendance Input Cycle",
        help_text="Enter Attendance Input Cycle",
        null=True,
        default=21,
    )
    attendance_start_month = models.IntegerField(default=1, null=True, blank=True)
    attendance_input_cycle_to = models.IntegerField(
        verbose_name="Attendance Input Cycle",
        help_text="Enter Attendance Input Cycle",
        null=True,
        default=20,
    )
    attendance_paycycle_end_date = models.DateField(
        null=True, blank=True
    )

    limit_backdated_ar_application = models.IntegerField(
        verbose_name="Limit Backdated AR Application",
        help_text="Enter Limit Backdated AR Application",
        null=True,
    )

    limit_number_of_ar_application_per_month = models.IntegerField(
        verbose_name="Limit Number Of AR Per Month Application",
        help_text="Enter Limit Number Of AR Application Per Month",
        null=True,
    )

    daily_attendance_report_reminder = models.BooleanField(
        verbose_name="Daily Attendance Report Reminder",
        help_text="Enable Daily Attendance Report Reminder",
        default=False,
    )

    late_early_punch_reminder = models.BooleanField(
        verbose_name="Late Early Punch Reminder",
        help_text="Enable Late Early Punch Reminder",
        default=False,
    )

    pending_regularization_reminder = models.BooleanField(
        verbose_name="Pending Regularization Reminder",
        help_text="Enable Pending Regularization Reminder",
        default=False,
    )

    ip_restriction = models.BooleanField(
        verbose_name="IP Restriction",
        help_text="Enable IP Restriction",
        default=False,
    )
    calendar_type = models.CharField(max_length=50, choices=CalendarTypeChoice.choices,null=True,blank=True)


    class Meta:
        verbose_name = "Payroll Setting"
        verbose_name_plural = "Payroll Settings"


class EmployeeCheckInOutDetails(AbstractModel):
    APPROVED = 10
    PENDING = 20
    CANCELLED = 30
    REJECTED = 40
    OK = 50

    ACTION_STATUS_CHOICES = (
        (APPROVED, "Approved"),
        (PENDING, "Pending"),
        (CANCELLED, "Cancelled"),
        (REJECTED, "Rejected"),
        (OK, "Ok"),
    )

    MARK_AS_PRESENT = 10
    MARK_AS_EXACT_TIME = 20
    MARK_AS_LEAVE = 30
    MARK_AS_LOP = 40
    MARK_AS_COMPOFF = 50
    MARK_AS_OT = 60

    ACTION_CHOICES = (
        (MARK_AS_PRESENT, "Mark as Present"),
        (MARK_AS_EXACT_TIME, "Mark as Exact Time"),
        (MARK_AS_LEAVE, "Mark as Leave"),
        (MARK_AS_LOP, "Mark as LOP"),
        (MARK_AS_OT, "Mark as OT"),
        (MARK_AS_COMPOFF, "Mark as COMPOFF"),
    )
    
    CHECKIN_LOCATIONS = (
            ("Work From Home", "Work From Home"),
            ("Work From Remote", "Work From Remote"),
            ("Work From Office", "Work From Office")
        )

    employee = models.ForeignKey(
        "directory.Employee",
        on_delete=models.CASCADE,
        verbose_name="Employee",
        related_name="clock_details",
        help_text="Enter Primary Key of Employee Table",
    )

    status = models.CharField(
        max_length=20,
        verbose_name="Status",
        help_text="Its Shows, If Employee Check In Status Will Active",
        default="A",
    )

    date_of_checked_in = models.DateField(
        verbose_name="Date Of Checked In",
        help_text="Employee Check In Date",
        null=True,
        blank=True,
    )

    time_in = models.DateTimeField(
        verbose_name="Clock In Time", help_text="Employee Clock In Time", null=True
    )

    latest_time_in = models.DateTimeField(
        verbose_name="Latest Clock In Time",
        help_text="Employee Latest Clock In Time",
        null=True,
    )

    time_out = models.DateTimeField(
        verbose_name="Clock Out Time",
        help_text="Employee Clock Out Time",
        null=True,
        blank=True,
    )

    work_duration = models.CharField(
        max_length=20,
        verbose_name="Work Duration",
        help_text="Working time in hours and minutes",
        null=True,
        blank=True,
    )

    break_duration = models.CharField(
        max_length=20,
        verbose_name="Break Duration",
        help_text="Break time in hours and minutes format",
        blank=True,
        null=True,
    )

    breaks = models.IntegerField(
        verbose_name="Breaks",
        help_text="It will Count,How Many Breaks You Have Taken in your Duty Period",
        blank=True,
        null=True,
    )
    employee_selfie = models.FileField(
        verbose_name="Employee Selfie",
        help_text="Employee Selfie to identify",
        upload_to="emplyee_attendance_selfie/",
        null=True,
        blank=True,
        max_length=512
    )

    employee_selfie_binary = models.TextField(
        verbose_name="Employee Selfie Binary",
        help_text="Employee Selfie to identify",
        null=True,
        blank=True,
    )
    location = models.CharField(
        max_length=500,
        verbose_name="Employee Geo Location",
        help_text="Employee Geo Location while clock in",
        blank=True,
        null=True,
    )
    distance = models.IntegerField(
        verbose_name="Distance",
        help_text="Employee Geo Location Distance",
        default=0,
        blank=True,
        null=True,
    )
    action_status = models.PositiveSmallIntegerField(
        choices=ACTION_STATUS_CHOICES,
        verbose_name="Approval Status",
        help_text="It indicates the approval status",
        default=OK,
    )

    action = models.PositiveSmallIntegerField(
        choices=ACTION_CHOICES,
        verbose_name="Action",
        help_text="action requested by the user",
        null=True,
        blank=True,
    )

    action_reason = models.CharField(
        verbose_name="Reason",
        max_length=512,
        help_text="Reason for action apply",
        blank=True,
        null=True,
    )

    approval_reason = models.CharField(
        verbose_name="Approval Reason",
        max_length=512,
        help_text="Reason for action approval",
        blank=True,
        null=True,
    )
    reject_reason = models.CharField(
        verbose_name="Approval Reason",
        max_length=512,
        help_text="Reason for action reject",
        blank=True,
        null=True,
    )
    extra_data = models.JSONField(
        verbose_name="Extra Info",
        default=dict,
        blank=True,
        help_text="to store the approval information",
    )
    overtime_hours = models.PositiveIntegerField(
        default=0,
        verbose_name="OT Working Hours",
    )
    compoff_added = models.CharField(max_length=32, null=True, blank=True)
    is_logged_out = models.BooleanField(default=False, null=True, blank=True)
    checkin_location = models.CharField(
        choices=CHECKIN_LOCATIONS,
        default="Work From Office",
        max_length=32,
        null=True,
        blank=True,
    )
    absent_period = models.CharField(max_length=32, null=True, blank=True)
    class Meta:
        verbose_name = "Attendance History"
        verbose_name_plural = "Attendance History"

    def __str__(self) -> str:
        return f"{self.employee.name} - {self.status}"

    def save(self, *args, **kwargs):            
        if self.employee_selfie and 'https://bharatpayroll.s3.amazonaws.com/' not in self.employee_selfie.url:
            file_key = f"{self.employee_selfie.field.upload_to}{self.employee_selfie.name}"
            s3_url = "https://bharatpayroll.s3.amazonaws.com/media/public/"+file_key
            self.employee_selfie = s3_url        
        return super().save(*args, **kwargs)

class AnamolyHistory(AbstractModel):
    """
    Employee anamolies history

    AJAY, 22.03.2023
    """

    APPROVED = 10
    PENDING = 20
    PROCESSING = 30
    REJECTED = 40

    STATUS_CHOICES = (
        (APPROVED, "Approved"),
        (PENDING, "Pending"),
        (PROCESSING, "Processing"),
        (REJECTED, "Rejected"),
    )

    IN_TIME_BREACH = 10
    OUT_TIME_BREACH = 20
    FULL_DAY_WD_BREACH = 30
    HALF_DAY_WD_BREACH = 40
    MAX_BREAK_DURATION_BREACH = 50
    MAX_TOTAL_BREAKS_BREACH = 60

    ANAMOLY_CHOICES = (
        (IN_TIME_BREACH, "In Time"),
        (OUT_TIME_BREACH, "Out Time"),
        (FULL_DAY_WD_BREACH, "Full Day Work Duration"),
        (HALF_DAY_WD_BREACH, "Half Day Work Duration"),
        (MAX_BREAK_DURATION_BREACH, "Break Duration"),
        (MAX_TOTAL_BREAKS_BREACH, "No Of Breaks"),
    )

    MARK_AS_PRESENT = 10
    MARK_AS_EXACT_TIME = 20
    MARK_AS_LEAVE = 30
    MARK_AS_LOP = 40
    MARK_AS_COMPOFF = 50
    MARK_AS_OT = 60

    ACTION_CHOICES = (
        (MARK_AS_PRESENT, "Mark as Present"),
        (MARK_AS_EXACT_TIME, "Mark as Exact Time"),
        (MARK_AS_LEAVE, "Mark as Leave"),
        (MARK_AS_LOP, "Mark as LOP"),
        (MARK_AS_OT, "Mark as OT"),
        (MARK_AS_COMPOFF, "Mark as COMPOFF"),
    )

    clock = models.ForeignKey(
        "EmployeeCheckInOutDetails",
        on_delete=models.CASCADE,
        related_name="anamolies",
        verbose_name="Employee Clock",
        help_text="Relate to the employee clock in details",
    )
    request_date = models.DateField(
        verbose_name="Anomaly request date",
        help_text="Employee Anomalie Date",
    )

    choice = models.PositiveSmallIntegerField(
        choices=ANAMOLY_CHOICES, verbose_name="Type", help_text="Type of Anamoly"
    )
    result = models.CharField(
        max_length=20,
        verbose_name="result",
        help_text="Anamoly calculation result",
        null=True,
        blank=True,
    )
    reason = models.CharField(
        max_length=100,
        verbose_name="reason for anomalie",
        help_text="Employee reason for anomalie",
        blank=True,
    )
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES,
        verbose_name="Approval Status",
        help_text="It indicates the approval status",
        default=PENDING,
    )

    action = models.PositiveSmallIntegerField(
        choices=ACTION_CHOICES,
        verbose_name="Action",
        help_text="action requested by the user",
        null=True,
        blank=True,
    )
    deducted_from = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        verbose_name = "Anamoly History"
        verbose_name_plural = "Anamoly History"
        ordering = ["request_date"]

class AutoDeductionHistory(AbstractModel):

    DEDUCTION_CHOICES = (
        ('IN_TIME_BREACH', "In Time"),
        ('OUT_TIME_BREACH', "Out Time"),
        ('FULL_DAY_WD_BREACH', "Full Day Work Duration"),
        ('HALF_DAY_WD_BREACH', "Half Day Work Duration"),
        ('MAX_BREAK_DURATION_BREACH', "Break Duration"),
        ('MAX_TOTAL_BREAKS_BREACH', "No Of Breaks"),
    )

    clock = models.ForeignKey(
        "EmployeeCheckInOutDetails",
        on_delete=models.CASCADE,
    )
    request_date = models.DateField()

    choice = models.CharField(
        choices=DEDUCTION_CHOICES, max_length=256
    )
    result = models.CharField(
        max_length=20,
        verbose_name="result",
        null=True,
        blank=True,
    )
    reason = models.CharField(
        max_length=100,
        blank=True,
    )
    is_anamoly_created = models.BooleanField(default=False)
    deducted_from = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        verbose_name = "Auto Deduction History"
        verbose_name_plural = "Auto Deduction Historys"
        ordering = ["request_date"]


class EmployeeMonthlyAttendanceRecords(AbstractModel):
    
    employee = models.ForeignKey("directory.Employee", on_delete=models.DO_NOTHING, related_name="montly_attendance", null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    month = models.IntegerField(null=True, blank=True)
    attendance_data = models.JSONField(default=dict, null=True, blank=True)
    present_days = models.FloatField(default=0.0)
    leaves_count = models.FloatField(default=0.0)
    absent_count = models.FloatField(default=0.0)
    anamoly_count = models.FloatField(default=0.0)
    halfday_count = models.FloatField(default=0.0)
    lop_count = models.FloatField(default=0.0)
    overtime_count = models.FloatField(default=0.0)
    updated_manager_lop_count = models.FloatField(default=0.0)
    updated_hr_lop_count = models.FloatField(default=0.0)
    penalty_details = models.JSONField(default=dict, null=True, blank=True)
    is_manager_updated = models.BooleanField(default=False)
    is_hr_updated = models.BooleanField(default=False)
    hr_comment = models.TextField(null=True, blank=True, default='')
    manager_comment = models.TextField(null=True, blank=True, default='')
    manager_hosted_by = models.ForeignKey("directory.Employee",
                                        on_delete=models.DO_NOTHING,
                                        related_name="manager_updated_montly_attendance", null=True, blank=True)
    hr_hosted_by = models.ForeignKey("directory.Employee",
                                        on_delete=models.DO_NOTHING,
                                        related_name="hr_updated_montly_attendance", null=True, blank=True)
    is_payroll_run = models.BooleanField(default=False)
    leaves_encash_count = models.FloatField(default=0.0, null=True, blank=True)
    is_cron_run = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Consolidated Reports"
        verbose_name_plural = "Consolidated Reports"

    def __str__(self):
        return f'{self.employee.name}-YEAR-{self.year}-{self.month}'


class VgAttendanceLogs(AbstractModel):

    class DirectionType(models.TextChoices):
        IN = 'in', 'in'
        OUT = 'out', 'out'

    employee_code = models.CharField(max_length=100, null=True,blank=True)
    log_datetime = models.DateTimeField(null=True,blank=True)
    log_date = models.DateTimeField(null=True,blank=True)
    log_time = models.DateTimeField(null=True,blank=True)
    direction = models.CharField(max_length=50, choices=DirectionType.choices,null=True,blank=True)
    work_code = models.CharField(max_length=100,null=True,blank=True)
    device_short_name = models.CharField(max_length=100,null=True,blank=True)
    serial_number = models.CharField(max_length=100,null=True,blank=True)
    verification_mode = models.CharField(max_length=100,null=True,blank=True)
    reserved_field_1 = models.CharField(max_length=100,null=True,blank=True)
    reserved_field_2 = models.CharField(max_length=100,null=True,blank=True)
    attendance_log = models.IntegerField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Boimetric Attendance Logs"
        verbose_name_plural = "Biometric Attendance Logs"
    
    
class ConsolidateNotificationDates(AbstractModel):
    company = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE, related_name="consolidate_notification_date")
    employee_start_date = models.DateField( null=True, blank=True)
    employee_end_date = models.DateField( null=True, blank=True)
    reporting_manager_start_date = models.DateField( null=True, blank=True)
    reporting_manager_end_date = models.DateField( null=True, blank=True)
    hr_manager_start_date = models.DateField( null=True, blank=True)
    hr_manager_end_date = models.DateField( null=True, blank=True)
    
    class Meta:
        verbose_name = "Consolidate Reminder"
        verbose_name_plural = "Consolidate Reminders"
        
    def __str__(self):
        return str(self.id)
    
class AttendanceShiftsSetup(AbstractModel):

    class CalendarTypeChoice(models.TextChoices):
        CALENDARYEAR = 'calendaryear', 'CalendarYear'
        FINANCIALYEAR = 'financialyear', 'FinancialYear'
    
    company = models.ForeignKey(CompanyDetails,on_delete=models.CASCADE,verbose_name="Company")
    session_year = models.ForeignKey(SessionYear, on_delete=models.CASCADE, null=True, blank=True)
    calendar_type = models.CharField(max_length=50, choices=CalendarTypeChoice.choices,null=True,blank=True)
    start_date = models.DateField(null=True,blank=True)
    end_date = models.DateField(null=True,blank=True)
    is_shiftsetup_updated = models.BooleanField(default=False, null=True, blank=True)

    class Meta:
        verbose_name = "Shifts Setup"
        verbose_name_plural = "Shifts Setups"
        
    def __str__(self):
        return str(self.id)

class EmployeeSystemMapping(AbstractModel):
    """
    this table is used to map the system name with employee using in key logger
    """
    emp = models.ForeignKey("directory.Employee",on_delete=models.CASCADE, related_name="employee_relation")
    system_name = models.CharField(max_length=100)


class KeyloggerAttendanceLogs(models.Model):
    
    emp_id = models.CharField(max_length=25) #need to change the relation here
    system_on = models.DateTimeField(null=True, blank=True)
    system_off = models.DateTimeField(null=True, blank=True)
    break_duration = models.IntegerField(null=True, blank=True)
    system_ip = models.CharField(max_length=50, null=True, blank=True)
    system_name = models.CharField(max_length=50, null=True, blank=True)
    internet_ip = models.CharField(max_length=50, null=True, blank=True)
    break_start = models.DateTimeField(null=True, blank=True)
    break_end = models.DateTimeField(null=True, blank=True)
    system_location = models.CharField(max_length=500, null=True, blank= True)
    internet_location = models.CharField(max_length=100, null=True, blank= True)
    break_cause = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return str(self.emp_id)+"----"+str(self.id)

class ConsolidateButton(AbstractModel):
    """
    this button helps to check the consolidate status
    """
    year = models.IntegerField(null=True, blank=True)
    month = models.IntegerField(null=True, blank=True)
    # consolidate_finalized = models.BooleanField(default=False)
    company = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE, related_name='employee_consolidate')


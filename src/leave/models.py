from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField

from company_profile.models import CompanyDetails
from core.models import AbstractModel

from directory.models import SessionYear

class WorkRules(AbstractModel):
    company = models.ForeignKey(
        CompanyDetails,
        on_delete=models.CASCADE,
        verbose_name="Company Id",
        help_text="Select Company Primary Key To Post Work Week Rules According To Company Wise",
    )
    name = models.CharField(
        verbose_name="Rule Name",
        max_length=100,
        help_text="Enter Work Rule Maximum Length of 100",
    )
    description = models.CharField(
        verbose_name="Rule Description",
        max_length=100,
        help_text=" Enter Description Maximum Length of 100",
        default="Custom Rule created",
        null=True,
        blank=True,
    )
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Create Work Week"
        verbose_name_plural = "Create Work Week"
        ordering = ["-created_at"]
        get_latest_by = "created_at"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            WorkRules.objects.filter(is_default=True).update(is_default=False)

        return super().save(*args, **kwargs)


class WorkRuleChoices(AbstractModel):
    FULL_DAY = 2
    HALF_DAY = 1
    WEEK_OFF = 0

    WORK_TYPE_CHOICES = (
        (FULL_DAY, "Full Day"),
        (HALF_DAY, "Half Day"),
        (WEEK_OFF, "Week Off"),
    )
    work_rule = models.ForeignKey(
        WorkRules,
        related_name="work_rule_choices",
        on_delete=models.CASCADE,
    )
    monday = models.PositiveSmallIntegerField(
        verbose_name="Monday",
        choices=WORK_TYPE_CHOICES,
        default=FULL_DAY,
    )
    tuesday = models.PositiveSmallIntegerField(
        verbose_name="Tuesday",
        choices=WORK_TYPE_CHOICES,
        default=FULL_DAY,
    )
    wednesday = models.PositiveSmallIntegerField(
        verbose_name="Wednesday",
        choices=WORK_TYPE_CHOICES,
        default=FULL_DAY,
    )
    thursday = models.PositiveSmallIntegerField(
        verbose_name="Thursday",
        choices=WORK_TYPE_CHOICES,
        default=FULL_DAY,
    )
    friday = models.PositiveSmallIntegerField(
        verbose_name="Friday",
        choices=WORK_TYPE_CHOICES,
        default=FULL_DAY,
    )
    saturday = models.PositiveSmallIntegerField(
        verbose_name="Saturday",
        choices=WORK_TYPE_CHOICES,
        default=FULL_DAY,
    )
    sunday = models.PositiveSmallIntegerField(
        verbose_name="Sunday",
        choices=WORK_TYPE_CHOICES,
        default=FULL_DAY,
    )
    week_number = models.IntegerField()

    class Meta:
        verbose_name = "Work Week"
        verbose_name_plural = "Work Weeks"
        unique_together = ("work_rule", "week_number")

    def __str__(self) -> str:
        return f"{self.week_number}"


class EmployeeWorkRuleRelation(AbstractModel):
    """
    A through model to define relation between employee and workrules

    AJAY, 21.02.2023
    """

    employee = models.ForeignKey("directory.Employee", on_delete=models.CASCADE)
    work_rule = models.ForeignKey("WorkRules", on_delete=models.CASCADE)
    session_year = models.ForeignKey(SessionYear, on_delete=models.CASCADE, null=True, blank=True)
    effective_date = models.DateField(
        verbose_name=("Effective Date"), default=timezone.now
    )

    class Meta:
        verbose_name = "Assign Work Week"
        verbose_name_plural = "Assign Work Week"
        unique_together = ("employee", "work_rule")

    def __str__(self) -> str:
        return f"{self.employee.name}-{self.work_rule.name}"


class LeaveRules(AbstractModel):
    ACCRUAL_CHOICES = (
        ("MONTHLY", "Monthly"),
        ("QUARTERLY", "Quarterly"),
        ("HALF_YEARLY", "Half Yearly"),
    )

    company = models.ForeignKey(
        CompanyDetails,
        on_delete=models.CASCADE,
        verbose_name="Company",
        help_text="Select Company Primary Key To Post Work Week Rules According To Company Wise",
    )
    name = models.CharField(max_length=100, verbose_name="Leave Type")
    description = models.TextField(
        verbose_name="Leave Description",
        help_text="Enter description",
        default="This is a default description for the Leave Type. You can customise this.",
        blank=True,
    )
    leaves_allowed_in_year = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        verbose_name="Leaves Allowed in a Year",
        null=True,
        blank=True,
    )
    weekends_between_leave = models.BooleanField(
        verbose_name="Weekends Between Leave", default=False
    )
    holidays_between_leave = models.BooleanField(
        verbose_name="Holidays Between Leave", default=False
    )
    creditable_on_accrual_basis = models.BooleanField(
        verbose_name="Creditable On Accrual Basis", default=False
    )
    accrual_frequency = models.CharField(
        max_length=20,
        choices=ACCRUAL_CHOICES,
        verbose_name="Accrual Frequency",
        help_text="leaves credited in employee buccket by monthly, quarterly,halfyearly",
        null=True,
        blank=True,
    )
    accruel_period = models.CharField(
        max_length=10,
        verbose_name="Accrual Period",
        help_text="credit leaves end of the month or month start",
        null=True,
        blank=True,
    )
    allowed_under_probation = models.BooleanField(
        default=False,
        verbose_name="Allowed Under Probation",
    )
    allowed_negative_rules = models.BooleanField(
        default=False,
        verbose_name="Allowed Negative Leaves",
    )
    carry_forward_enabled = models.BooleanField(
        verbose_name="Carry Forward Enabled", default=False
    )
    all_remaining_leaves = models.BooleanField(
        verbose_name="All Remaining Leaves",
        default=False,
        help_text="Flag to carry forward all remaining leaves",
    )
    max_leaves_to_carryforward = models.IntegerField(
        verbose_name="Max Leaves To Carry Forward", default=0
    )
    continuous_leaves_allowed = models.IntegerField(
        verbose_name="Allowed Continuous Leaves", default=0
    )
    max_leaves_allowed_in_month = models.FloatField(
        verbose_name="Max Allowed Leaves Per Month",
        blank=True,
        null=True,
        default=4,
    )
    allow_backdated_leaves = models.BooleanField(
        verbose_name="Backdated Leaves allowed",
        default=False,
    )
    is_leave_encashment_enabled = models.BooleanField(default=False,blank=True,null=True)
    all_remaining_leaves_for_encash = models.BooleanField(default=False,blank=True,null=True)
    max_leaves_to_encash = models.IntegerField(blank=True,null=True,default=0)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    includes_check_in_leave = models.BooleanField(default=False, null=True, blank=True)

    class Meta:
        verbose_name = "Create Leave Rule"
        verbose_name_plural = "Create Leave Rules"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.max_leaves_allowed_in_month:
            self.max_leaves_allowed_in_month = self.leaves_allowed_in_year

        return super().save(*args, **kwargs)


class EmployeeLeaveRuleRelation(AbstractModel):
    """
    A through model to define relation between Employee and Leave Rules

    AJAY, 22.02.2023
    """
    REQUEST_STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    )
    employee = models.ForeignKey("directory.Employee", on_delete=models.CASCADE)
    leave_rule = models.ForeignKey("LeaveRules", on_delete=models.CASCADE)
    effective_date = models.DateField(
        verbose_name=("Effective Date"), default=timezone.now
    )
    session_year = models.ForeignKey(SessionYear, on_delete=models.CASCADE, null=True, blank=True)
    remaining_leaves = models.DecimalField(
        max_digits=7,
        decimal_places=1,
        verbose_name="Balance Leaves",
        default=0,
    )
    earned_leaves = models.DecimalField(
        max_digits=7, decimal_places=2, verbose_name="Earned Leaves", default=0
    )
    used_so_far = models.DecimalField(
        max_digits=7, decimal_places=1, verbose_name="Applied Leaves", default=0
    )
    penalty_deduction = models.DecimalField(
        max_digits=7,
        decimal_places=1,
        verbose_name="Penalty Deducted Leaves",
        default=0,
    )
    used_lop_leaves = models.DecimalField(
        max_digits=7,
        decimal_places=1,
        verbose_name="LOP Leaves",
        default=0,
        help_text="Used Loss Of Pay Leaves",
    )
    extra_data = models.JSONField(default=dict, blank=True, verbose_name="Extra Data")
    compoff_added_details = ArrayField(
        models.TextField(default=''),
        default=list
    )
    """
    compoff_added_details = ArrayField(dates, default=[])
    when manager approved compoff for which date employee approved compoff will be added.
    when employee applied for leave which is least value of date  in this field be checked with start date of leave.
    if leave startdate is with in range of configuration max_days_to_utilize_compoff it will be applyed and last date will be removed. 
    the above part is happy path!!!
    
    for say i have 5 compoffs dates were ['2024-01-01', '2024-01-05', '2024-01-12',  '2024-01-15', '2024-01-21']

    all were approved, we have given 10 days to to apply leave, so today date is 2024-02-02
    
    ? so what i need to do in this condition
    
    ? how to reduce the if day is crossed.
    
    ? did HR's will guide employees.
    
    
    """

    class Meta:
        verbose_name = "Assign Leave Rules"
        verbose_name_plural = "Assign Leave Rules"
        # unique_together = ("employee", "leave_rule", "is_deleted", "session_year")

    def __str__(self) -> str:
        return f"{self.employee.name}-{self.leave_rule.name}"


class LeavesHistory(AbstractModel):
    APPROVED = 10
    PENDING = 20
    CANCELLED = 30
    REJECTED = 40
    REVOKED = 50

    STATUS_CHOICES = (
        (APPROVED, "Approved"),
        (PENDING, "Pending"),
        (CANCELLED, "Cancelled"),
        (REJECTED, "Rejected"),
        (REVOKED, "Revoke"),
    )

    DAY_SESSION_CHOICES = (
        ("FIRST_HALF", "First Half"),
        ("SECOND_HALF", "Second Half"),
    )

    employee = models.ForeignKey("directory.Employee", on_delete=models.CASCADE)
    leave_rule = models.ForeignKey("LeaveRules", on_delete=models.CASCADE)
    start_date = models.DateField(
        verbose_name="Start Date",
    )
    start_day_session = models.CharField(
        max_length=20,
        choices=DAY_SESSION_CHOICES,
        verbose_name="Select Half",
        help_text="It indicates the employee taken full_day or half_day leave",
        null=True,
        blank=True,
    )
    end_date = models.DateField(
        verbose_name="End Date",
    )
    end_day_session = models.CharField(
        max_length=20,
        choices=DAY_SESSION_CHOICES,
        verbose_name="Select Half",
        help_text="It indicates the employee taken full_day or half_day leave",
        null=True,
        blank=True,
    )
    reason = models.CharField(
        max_length=500,
        verbose_name="Write your Reason",
        help_text="Write Your Reason here for taking leave",
    )
    reason_for_rejection = models.CharField(
        max_length=500,
        verbose_name="Write your Reason",
        help_text="Write Your Reason here for taking leave",
        null=True,
        blank=True,
    )
    # attachment = models.FileField(
    #     upload_to="leave attachments/",
    #     help_text="upload file for proof",
    #     null=True,
    #     blank=True,
    # )
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES,
        verbose_name="Leave Status",
        help_text="It indicates the leave status",
    )
    extra_data = models.JSONField(
        default=dict,
        verbose_name="Additional Info",
        help_text="Used to store additional information in the JSON format",
        null=True,
        blank=True,
    )
    no_of_leaves_applied = models.DecimalField(
        verbose_name="No Of Leaves",
        max_digits=7,
        decimal_places=1,
        default=0,
        help_text="Count of applied leaves",
    )
    approved_on = models.DateTimeField(
        verbose_name="Approved On",
        null=True,
        blank=True,
    )
    approved_by = models.ForeignKey(
        "directory.Employee",
        on_delete=models.CASCADE,
        verbose_name="Leave Approved By",
        related_name="approved_by",
        null=True,
        blank=True,
    )
    is_approved_by_tenant_manager = models.BooleanField(default=False)
    multitenant_manager_id = models.CharField(
        max_length=500,
        verbose_name="Multitenant Manager ID",
        help_text="Please Enter multitenant Manager ID",
        null=True,
        blank=True,
    )
    multitenant_manager_name = models.CharField(
        max_length=500,
        verbose_name="Multitenant Manager Name",
        help_text="Please Enter multitenant Manager Name",
        null=True,
        blank=True,
    )
    multitenant_manager_email = models.EmailField(
        max_length=500,
        verbose_name="Multitenant Manager Email",
        help_text="Please Enter multitenant Manager Email",
        null=True,
        blank=True,
    )
    is_penalty = models.BooleanField(default=False, null=True, blank=True)
    attachment = models.FileField(upload_to='leave_docs/', null=True, blank=True)
    is_revoked = models.BooleanField(default=False, null=True, blank=True)
    is_backdated = models.BooleanField(default=False, null=True, blank=True)
    backdated_approval_reason = models.TextField(null=True, blank=True, max_length=1024)
    
    class Meta:
        verbose_name = "Leaves History"
        verbose_name_plural = "Leaves History"

class LeaveRuleSettings(AbstractModel):

    class CalendarTypeChoice(models.TextChoices):
        CALENDARYEAR = 'calendaryear', 'CalendarYear'
        FINANCIALYEAR = 'financialyear', 'FinancialYear'

    company = models.ForeignKey(CompanyDetails,on_delete=models.CASCADE,verbose_name="Company")
    session_year = models.ForeignKey(SessionYear, on_delete=models.CASCADE, null=True, blank=True)
    calendar_type = models.CharField(max_length=50, choices=CalendarTypeChoice.choices,null=True,blank=True)
    start_date = models.DateField(null=True,blank=True)
    end_date = models.DateField(null=True,blank=True)
    is_calendar_updated = models.BooleanField(default=False, null=True, blank=True)
    
    class Meta:
        verbose_name = "Leaves Setup"
        verbose_name_plural = "Leaves Setup"
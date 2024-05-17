import datetime

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from company_profile.models import (
    CompanyGrades,
    Departments,
    Designations,
    SubDepartments,
)
from core.models import AbstractModel
from directory import managers
from HRMSApp.models import Roles, CompanyDetails
from model_utils import FieldTracker


#  Custom User Manager
class WorkLocations(AbstractModel):
    work_location = models.CharField(max_length=100)


class SessionYear(AbstractModel):
    
    session_year = models.CharField(max_length=56, null=True, blank=True)
    start_month = models.IntegerField(default=1, null=True, blank=True)
    end_month = models.IntegerField(default=12, null=True, blank=True)
    
    def __str__(self):
        return f'{self.session_year}'


class EmployeeTypes(AbstractModel):
    FULL_TIME = 10
    PART_TIME = 20
    INTERN = 30
    ON_CONTRACT = 40
    OTHERS = 50

    EMPLOYEE_TYPE_CHOICES = (
        (FULL_TIME, "Full Time"),
        (PART_TIME, "Part Time"),
        (INTERN, "Intern"),
        (ON_CONTRACT, "On Contract"),
        (OTHERS, "Others"),
    )
    employee_type = models.PositiveSmallIntegerField(
        verbose_name="Employement Type",
        choices=EMPLOYEE_TYPE_CHOICES,
        default=OTHERS,
    )

    slug = models.SlugField(blank=True, null=True)

    def __str__(self) -> str:
        return self.get_employee_type_display()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.get_employee_type_display())
        return super().save(*args, **kwargs)

class StatusChoices(models.TextChoices):
    Accepted = 'Accepted', 'Accepted'
    Rejected = 'Rejected', 'Rejected'
    Pending = 'Pending', 'Pending'
    
# Add Employee Model
class Employee(AbstractModel):
    GENDER_CHOICES = (
        ("MALE", "Male"),
        ("FEMALE", "Female"),
        ("TRANSGENDER", "Transgender")
    )

    # PAYROLL_CHOICES = (
    #     ("Active", "Active"),
    #     ("In-Active", "In-Active"),
    #     ("Hold", "Hold")
    # )

    company = models.ForeignKey(
        CompanyDetails, related_name="employees", on_delete=models.CASCADE
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, help_text=_("User"), related_name = "employee_details",
    )

    first_name = models.CharField(
        verbose_name=_("First Name"),
        max_length=255,
        help_text=_("Required, Maximum of 255 Characters."),
    )
    middle_name = models.CharField(
        verbose_name=_("Middle Name"),
        max_length=255,
        blank=True,
        default=" ",
        help_text=_("Optional, Maximum of 255 Characters."),
    )
    last_name = models.CharField(
        verbose_name=_("Last Name"),
        max_length=255,
        blank=True,
        default=" ",
        help_text=_("Required, Maximum of 255 Characters."),
    )
    employee_image = models.FileField(
        upload_to="employee_images/",
        null=True,
        blank=True,
        max_length=512
    )
    official_email = models.EmailField(
        verbose_name=_("Official Email"), max_length=100, blank=True, null=True
    )
    phone = models.CharField(verbose_name=_("Phone"), max_length=20)
    roles = models.ManyToManyField(
        Roles,
        related_name="roles_employees",
        blank=True,
    )

    date_of_join = models.DateField(
        verbose_name=_("Join Date"),
        null=True,
        blank=True,
    )
    date_of_birth = models.DateField(
        verbose_name=_("Date Of Birth"), null=True, blank=True
    )

    gender = models.CharField(
        verbose_name=_("Gender"),
        choices=GENDER_CHOICES,
        max_length=20,
        null=True,
        blank=True,
    )
    blood_group = models.CharField(
        verbose_name=_("Blood Group"), max_length=5, null=True, blank=True
    )
    marital_status = models.CharField(
        verbose_name=_("Marital Status"), max_length=100, null=True, blank=True
    )
    anniversary_date = models.DateField(
        verbose_name=_("Anniversary Date"), null=True, blank=True
    )
    personal_email = models.EmailField(
        verbose_name=_("Personal Email"), max_length=100, null=True, blank=True
    )
    alternate_phone = models.CharField(
        verbose_name=_("Alternative Mobile Number"),
        max_length=20,
        null=True,
        blank=True,
    )
    pre_onboarding = models.BooleanField(verbose_name=_("Is PreJoinee?"), default=False)

    linkedin_profile = models.URLField(
        verbose_name=_("LinkedIN Profile"),
        blank=True,
        null=True,
        default="https://www.linkedin.com",
    )
    facebook_profile = models.URLField(
        verbose_name=_("FaceBook Profile"),
        blank=True,
        null=True,
        default="https://www.facebook.com",
    )
    twitter_profile = models.URLField(
        verbose_name=_("Twitter Profile"),
        blank=True,
        null=True,
        default="https://www.twitter.com",
    )
    objects = managers.EmployeeManager()
    payroll_status = models.BooleanField(default=True,null=True,blank=True)
    # tracker = FieldTracker()
    is_sign_up = models.BooleanField(default=False, null=True, blank=True)
    payroll_entity = models.CharField(null=True, blank=True, max_length=256)
    work_entity = models.CharField(null=True, blank=True, max_length=256)
    is_rehire  = models.BooleanField(default=False, blank=True, null=True)
    bio = models.TextField(null=True, blank=True)
    

    class Meta:
        verbose_name = "Personal Details"
        verbose_name_plural = "Personal Details"
        ordering = ["date_of_join"]

    def __str__(self) -> str:
        return f"{self.first_name}"
    
    @property
    def name(self):
        full_name = self.first_name
        if self.middle_name:
            full_name += " " +self.middle_name
        if self.last_name:
            full_name += " " +self.last_name

        return (
            full_name
        ).strip()


class EmployeeWorkDetails(AbstractModel):
    """
    Model to save employee work details

    """

    employee = models.OneToOneField(
        Employee,
        verbose_name=_("Employee"),
        related_name="work_details",
        on_delete=models.CASCADE,
    )
    employee_number = models.CharField(
        verbose_name=_("Employee Serial Number"),
        max_length=246,
        help_text=_(
            "Required, Unique, maximum of 246 characters. Employee Unique Identifier."
        ),
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        Departments,
        verbose_name=_("Department"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    sub_department = models.ForeignKey(
        SubDepartments,
        verbose_name=_("Sub Department"),
        related_name=_("work_details_sub_dept"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    designation = models.ForeignKey(
        Designations,
        verbose_name=_("Designation"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    job_title = models.CharField(
        verbose_name=_("Job Title"), max_length=100, blank=True, null=True
    )

    # reporting_manager = models.ForeignKey(
    #     "directory.EmployeeReportingManager",
    #     verbose_name="Reporting Manager",
    #     related_name="reporting_manager",
    #     on_delete=models.PROTECT,
    #     null=True,
    #     blank=True,
    # )
    work_location = models.CharField(
        verbose_name=_("Work Location"), max_length=100, blank=True, null=True
    )
    employee_grade = models.ForeignKey(
        CompanyGrades,
        verbose_name=_("Company Grades"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    employee_type = models.ForeignKey(
        EmployeeTypes,
        verbose_name="Employee Type",
        related_name="types",
        limit_choices_to=models.Q(is_deleted=False),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    employee_status = models.CharField(
        default="YetToJoin",
        max_length=100,
        blank=True,
        null=True,
    )
    experience_in_years = models.IntegerField(
        verbose_name="Work Experience In Year(s)", blank=True, null=True
    )
    experience_in_months = models.IntegerField(
        verbose_name="Work Experience In Month(s)", blank=True, null=True
    )
    probation_period = models.IntegerField(
        verbose_name="Probation Period", blank=True, null=True
    )
    probation_period_left = models.IntegerField(default=0, blank=True, null=True)
    # tracker = FieldTracker()

    objects = managers.EmployeeWorkDetailsManager()

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Work Details"
        verbose_name_plural = "Work Details"
        get_latest_by = ["employee__created_at"]
        indexes = [models.Index(fields=['employee', 'employee_number', 'department', 'sub_department', 'designation', 'job_title', 'work_location', 'employee_grade', 'employee_type', 'employee_status', 'experience_in_years', 'experience_in_months', 'probation_period', 'probation_period_left'], name="work_details_table_index")]

    def __str__(self) -> str:
        return f"{self.employee}"


class EmployeeSalaryDetails(AbstractModel):
    FUND_TRANSFER_CHOICES = (
        ("FT", "FT"),
        ("NEFT", "NEFT"),        
    )

    employee = models.OneToOneField(
        Employee, related_name="salary_details", on_delete=models.CASCADE
    )
    ctc = models.DecimalField(
        verbose_name=_("CTC"),
        default=0.00,
        max_digits=12,
        decimal_places=2,
        help_text=_("Cost to the Compnany"),
        null=True,
        blank=True,
    )
    salary = models.DecimalField(
        verbose_name=_("Salary"),
        default=0.00,
        max_digits=12,
        decimal_places=2,
        help_text=_("Monthly Salary"),
        null=True,
        blank=True,
    )

    account_holder_name = models.CharField(
        verbose_name=_("Bank Account Holder Name"),
        max_length=100,
        null=True,
        blank=True,
    )
    account_number = models.CharField(
        verbose_name=_("Bank Account Number"),
        max_length=100,
        null=True,
        blank=True,
    )
    bank_name = models.CharField(
        verbose_name=_("Bank Name"),
        max_length=100,
        null=True,
        blank=True,
    )
    branch_name = models.CharField(
        verbose_name=_("Bank Branch Name"),
        max_length=100,
        null=True,
        blank=True,
    )
    city = models.CharField(
        verbose_name=_("Bank City"),
        max_length=100,
        null=True,
        blank=True,
    )
    ifsc_code = models.CharField(
        verbose_name=_("IFSC"),
        max_length=100,
        null=True,
        blank=True,
    )
    fund_transfer_type = models.CharField(        
        choices=FUND_TRANSFER_CHOICES,
        max_length=20,
        null=True,
        blank=True,
    )

    account_type = models.ForeignKey(
        "company_profile.BankAccountTypes",
        verbose_name=_("Bank Account Type"),
        related_name="bank_account_type",
        limit_choices_to=models.Q(is_deleted=False),
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    
    fixed_salary = models.DecimalField(default=0.00, max_digits=12, decimal_places=2, null=True, blank=True)
    variable_pay = models.DecimalField(default=0.00, max_digits=12, decimal_places=2, null=True, blank=True)
    
    monthly_incentive = models.DecimalField(default=0.00, max_digits=12, decimal_places=2, null=True, blank=True)
    arrears = models.DecimalField(default=0.00, max_digits=12, decimal_places=2, null=True, blank=True)
    special_deductions = models.DecimalField(default=0.00, max_digits=12, decimal_places=2, null=True, blank=True)
    advance_deductions = models.DecimalField(default=0.00, max_digits=12, decimal_places=2, null=True, blank=True)

    previous_income =  models.DecimalField(decimal_places=2, default=0.0, max_digits=12, null=True, blank =True)
    previous_tds = models.DecimalField(decimal_places=2, default=0.0, max_digits=12, null=True, blank = True)
    objects = managers.EmployeeSalaryDetailsManager()

    class Meta:
        verbose_name = _("Salary/Bank Info")
        verbose_name_plural = _("Salary/Bank Info")
        ordering = ("created_at",)
    
    def __str__(self):
        return str(self.employee) + str(self.ctc)    


    # def save(self, *args, **kwargs):
    #     if self.bank_name:
    #         bank_name = str(self.bank_name).strip().lower()
    #         self.fund_transfer_type = "FT" if bank_name.startswith('icici') else "NEFT"    
    #     return super().save(*args, **kwargs)

class EmployeeAddressDetails(AbstractModel):
    employee = models.OneToOneField(
        Employee,
        related_name=_("address_details"),
        on_delete=models.CASCADE,
    )
    current_address_line1 = models.CharField(max_length=500)
    current_address_line2 = models.CharField(max_length=500, blank=True, null=True)
    current_country = models.CharField(max_length=100, blank=True, null=True)
    current_state = models.CharField(max_length=100, blank=True, null=True)
    current_city = models.CharField(max_length=150, blank=True, null=True)
    current_pincode = models.CharField(max_length=20, blank=True, null=True)
    current_house_type = models.CharField(max_length=100, blank=True, null=True)
    current_staying_since = models.DateField(blank=True, null=True)
    living_in_current_city_since = models.DateField(blank=True, null=True)
    permanent_address_line1 = models.CharField(max_length=500)
    permanent_address_line2 = models.CharField(max_length=500, blank=True, null=True)
    permanent_country = models.CharField(max_length=100, blank=True, null=True)
    permanent_state = models.CharField(max_length=100, blank=True, null=True)
    permanent_city = models.CharField(max_length=150, blank=True, null=True)
    permanent_pincode = models.CharField(max_length=20, blank=True, null=True)
    permanent_same_as_current_address = models.BooleanField(default=False)
    other_house_type = models.CharField(max_length=50, null=True, blank=True, default='')
    # tracker = FieldTracker()
    
    class Meta:
        verbose_name = "Address Details"
        verbose_name_plural = "Address Details"
    
    def __str__(self):
        return str(self.employee)

class EmployeeWorkHistoryDetails(AbstractModel):
    MANAGER_TYPE_CHOICES = (
        ("Primary", "Primary"), 
        ("Secondary", "Secondary"))
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    department = models.ForeignKey(Departments, on_delete=models.CASCADE, null=True, blank=True)
    designation = models.ForeignKey(Designations, on_delete=models.CASCADE, null=True, blank=True)
    work_from = models.DateTimeField(null=True, blank=True)
    work_to = models.DateTimeField(null=True, blank=True)
    manager = models.ForeignKey(Employee,on_delete=models.CASCADE,related_name="employee_manager_history", null=True, blank=True)
    is_multitenant_manager = models.BooleanField(default=False)
    multitenant_manager_emp_id = models.CharField(max_length=150, blank=True, null=True)
    multitenant_manager_company_domain = models.CharField(max_length=150, blank=True, null=True)
    manager_type = models.CharField(null=True, blank=True, max_length=32, choices = MANAGER_TYPE_CHOICES, default='Primary')
    objects = managers.EmployeeWorkHistoryManager()
    
    class Meta:
        verbose_name = "Work History Detail"
        verbose_name_plural = "Work History Details"
    
    def __str__(self):
            return str(self.employee)

class EmployeeResignationDetails(AbstractModel):
    lEAVING_REASONS = (
        ("Resigned", "Resigned"),
        ("Absconded", "Absconded"),
        ("Terminated", "Terminated"),
        ("ReJoined", "ReJoined"),
    )
    employee = models.OneToOneField(
        Employee,
        related_name=_("resignation_info"),
        on_delete=models.CASCADE,
    )
    resignation_date = models.DateField(
        null=True,
        blank=True,
    )
    last_working_day = models.DateField(
        null=True,
        blank=True
    )
    resignation_status = models.CharField(
        max_length=100,
        default="-",
    )
    notice_period = models.IntegerField(
        verbose_name=_("Notice Period"),
        null=True,
        blank=True,
    )
    termination_date = models.DateField(
        blank=True,
        null=True,
    )
    exit_interview_date = models.DateField(blank=True, null=True)
    exit_interview_time = models.TimeField(null=True,blank=True)
    reason_of_leaving = models.CharField(
        max_length=16,
        choices=lEAVING_REASONS,
        default='Resigned',
        null=True,
        blank=True,
    )
    class Meta:
        verbose_name = "Resignation Info"
        verbose_name_plural = "Resignation Info"
    
    def __str__(self):
        return str(self.employee)

    # def save(self, *args, **kwargs):
    #     if self.resignation_date:
    #         self.last_working_day = self.resignation_date + datetime.timedelta(days=self.notice_period)
    #     return super().save(*args, **kwargs)

# DroupDown Table for Work
class ManagerType(AbstractModel):
    PRIMARY = 10
    SECONDARY = 20

    MANAGER_TYPE_CHOICES = ((PRIMARY, "Primary"), (SECONDARY, "Secondary"))

    manager_type = models.PositiveSmallIntegerField(
        verbose_name="Manager Types", choices=MANAGER_TYPE_CHOICES
    )

    def __str__(self):
        return self.get_manager_type_display()

    class Meta:
        verbose_name = _("Manager Type")
        verbose_name_plural = _("Manager Types")
        ordering = ["-created_at"]


class EmployeeReportingManager(AbstractModel):
    manager_type = models.ForeignKey(
        ManagerType,
        default=ManagerType.PRIMARY,
        verbose_name=_("Manager Type"),
        related_name="employee_manager_type",
        limit_choices_to=models.Q(is_deleted=False),
        on_delete=models.CASCADE,
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="employee",
    )
    manager = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="employee_manager",
        null=True,
        blank=True
    )
    is_multitenant = models.BooleanField(_("Is Multitenant?"), default=False, null=True, blank=True)
    multitenant_manager_emp_id = models.CharField(max_length=128, null=True, blank=True)
    multitenant_manager_company = models.CharField(max_length=256, null=True, blank=True)
    multitenant_manager_company_domain = models.CharField(max_length=256, null=True, blank=True)
    multitenant_manager_name = models.CharField(max_length=256, null=True, blank=True)
    multitenant_manager_email = models.CharField(max_length=256, null=True, blank=True)
    

    class Meta:
        verbose_name = _("Reporting Manager")
        verbose_name_plural = _("Reporting Managers")

    def __str__(self) -> str:
        return f"{self.employee.name} - {self.manager_type}"


class EmployeeDirectReporting(AbstractModel):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="employeedirect2"
    )
    manager = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="employeedirect3"
    )


class QualificationTypes(AbstractModel):
    GRADUATION = 10
    POST_GRADUATION = 20
    DOCTORATE = 30
    DIPLOMA = 40
    PRE_UNIVERSITY = 50
    OTHER_EDUCATION = 60
    CERTIFICATION = 70

    QUALIFICATION_TYPE_CHOICES = (
        (GRADUATION, "Graduation"),
        (POST_GRADUATION, "Post Graduation"),
        (DOCTORATE, "Doctorate"),
        (DIPLOMA, "Diploma"),
        (PRE_UNIVERSITY, "Pre University"),
        (OTHER_EDUCATION, "Other Education"),
        (CERTIFICATION, "Certification"),
    )

    qualification_type = models.PositiveSmallIntegerField(
        verbose_name="Manager Types", choices=QUALIFICATION_TYPE_CHOICES
    )

    def __str__(self):
        return self.get_qualification_type_display()

    class Meta:
        verbose_name = _("Qualification Type")
        verbose_name_plural = _("Qualification Types")
        ordering = ["-created_at"]


class CourseTypes(AbstractModel):
    FULL_TIME = 10
    PART_TIME = 20
    CORRESPONDENCE = 30
    CERTIFICATE = 40

    COURSE_TYPE_CHOICES = (
        (FULL_TIME, "Full Time"),
        (PART_TIME, "Part_Time"),
        (CORRESPONDENCE, "Correspondence"),
        (CERTIFICATE, "Certificate"),
    )

    course_type = models.PositiveSmallIntegerField(
        verbose_name="Course Types", choices=COURSE_TYPE_CHOICES
    )

    def __str__(self):
        return self.get_course_type_display()

    class Meta:
        verbose_name = _("Course Type")
        verbose_name_plural = _("Course Types")
        ordering = ["-created_at"]


class EmployeeEducationDetails(AbstractModel):
    employee = models.ForeignKey(
        Employee,
        verbose_name=_("Employee Education Details"),
        related_name="employee_education_details",
        on_delete=models.CASCADE,
    )
    qualification = models.ForeignKey(
        "directory.QualificationTypes",
        verbose_name=_("Qualification Types"),
        related_name="education_qualification_types",
        limit_choices_to=models.Q(is_deleted=False),
        on_delete=models.CASCADE,
    )
    course_name = models.CharField(
        verbose_name=_("Education Course Name"),
        max_length=100,
    )
    course_type = models.ForeignKey(
        "directory.CourseTypes",
        verbose_name=_("Course Types"),
        related_name="education_course_types",
        limit_choices_to=models.Q(is_deleted=False),
        on_delete=models.CASCADE,
    )
    stream = models.CharField(
        verbose_name="Course Stream",
        max_length=100,
    )
    course_start_date = models.DateField(
        verbose_name=_("Course Start Date"),
    )
    course_end_date = models.DateField(
        verbose_name=_("Course End Date"),
    )
    college_name = models.CharField(
        verbose_name=_("College Name"),
        max_length=100,
    )
    university_name = models.CharField(
        verbose_name=_("University Name"),
        max_length=100,
    )

    class Meta:
        verbose_name = "Educational Info"
        verbose_name_plural = "Educational Info"
        ordering = ("created_at",)


# Relationship Type DropDown
class RelationshipTypes(AbstractModel):
    FATHER = 10
    MOTHER = 20
    HUSBAND = 30
    WIFE = 40
    SON = 50
    DAUGHTER = 60
    BROTHER = 70
    SISTER = 80
    FRIEND = 90

    RELATIONSHIP_TYPE_CHOICES = (
        (FATHER, "Father"),
        (MOTHER, "Mother"),
        (HUSBAND, "Husband"),
        (WIFE, "Wife"),
        (SON, "Son"),
        (DAUGHTER, "Daughter"),
        (BROTHER, "Brother"),
        (SISTER, "Sister"),
        (FRIEND, "Friend"),
    )

    relationship_type = models.PositiveSmallIntegerField(
        verbose_name="Relationship Types", choices=RELATIONSHIP_TYPE_CHOICES
    )
    
    # tracker = FieldTracker()
    
    class Meta:
        verbose_name = "Relationship Type"
        verbose_name_plural = "Relationship Types"

    def __str__(self):
        return self.get_relationship_type_display()


class EmployeeFamilyDetails(AbstractModel):
    employee = models.ForeignKey(
        Employee,
        verbose_name=_("Employee Family Details"),
        related_name="employee_family_details",
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        verbose_name="Family Member Name",
        max_length=100,
    )
    relationship = models.ForeignKey(
        RelationshipTypes,
        verbose_name=_("Relationship Types"),
        related_name="relationship_types",
        limit_choices_to=models.Q(is_deleted=False),
        on_delete=models.CASCADE,
    )
    date_of_birth = models.DateField(
        verbose_name="Family Member DOB",
        null=True, blank=True
    )
    dependent = models.BooleanField(
        verbose_name="Employee Dependent OR Not",
        default=False,
    )
    # tracker = FieldTracker()

    class Meta:
        verbose_name = "Family Details"
        verbose_name_plural = "Family Details"
        ordering = ("created_at",)

    def __str__(self):
            return str(self.employee)

class EmployeeEmergencyContact(AbstractModel):
    employee = models.ForeignKey(
        Employee,
        verbose_name=_("Employee Emargency Contact"),
        related_name="employee_emargency_contact",
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        verbose_name="Emargency Contact Name",
        max_length=100,
    )
    relationship = models.ForeignKey(
        RelationshipTypes,
        verbose_name=_("Relationship Types"),
        related_name="emargency_relationship_types",
        limit_choices_to=models.Q(is_deleted=False),
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    phone_number = models.CharField(
        verbose_name="Emargency Phone Number",
        max_length=30,
    )
    # tracker = FieldTracker()

    class Meta:
        verbose_name = "Emargency Contact"
        verbose_name_plural = "Emargency Contact"
        ordering = ("created_at",)


# DropDown for document type
class DocumentsTypes(AbstractModel):
    PAN_CARD = 10
    AADHAAR_CARD = 20
    PASSPORT = 30
    DRIVING_LICENCE = 40
    VOTER_ID = 50
    ELECTRICITY_BILL = 60
    PHONE_BILL = 70
    BANK_PASSBOOK = 80
    RENTAL_AGREEMENT = 90
    others = 100

    DOCUMENT_TYPE_CHOICES = (
        (PAN_CARD, "PAN Card"),
        (AADHAAR_CARD, "Aadhaar Card"),
        (PASSPORT, "Passport"),
        (DRIVING_LICENCE, "Driving Licence"),
        (VOTER_ID, "Voter ID"),
        (ELECTRICITY_BILL, "Electricity Bill"),
        (PHONE_BILL, "Phone Bill"),
        (BANK_PASSBOOK, "Bank Passbook"),
        (RENTAL_AGREEMENT, "Rental Agreement"),
        (others, "others"),
    )

    document_type = models.PositiveSmallIntegerField(
        verbose_name="Document Types", choices=DOCUMENT_TYPE_CHOICES
    )

    def __str__(self):
        return self.get_document_type_display()

    class Meta:
        verbose_name = _("Document Type")
        verbose_name_plural = _("Document Types")
        ordering = ["-created_at"]


class EmployeeDocuments(AbstractModel):
    employee = models.ForeignKey(
        Employee,
        verbose_name=_("Employee Documents Ids"),
        related_name="employee_document_ids",
        on_delete=models.CASCADE,
    )
    document_type = models.ForeignKey(
        DocumentsTypes,
        verbose_name="Employee Document Types",
        related_name="employee_document_types",
        limit_choices_to=models.Q(is_deleted=False),
        on_delete=models.CASCADE,
    )
    document_number = models.CharField(
        verbose_name="Employee Document Number",
        max_length=100,
        null=True,
        blank=True,
    )
    photo_id = models.BooleanField(
        default=False,
    )
    date_of_birth = models.BooleanField(
        default=False,
    )
    current_address = models.BooleanField(
        default=False,
    )
    parmanent_address = models.BooleanField(
        default=False,
    )
    is_verified = models.BooleanField(default=False)
    select_file = models.FileField(
        upload_to="employee_documents/",
        null=True,
        blank=True,
        max_length=512
    )
    document_description = models.TextField(blank=True, null=True)
    document_submission_date = models.DateField(null=True, blank=True)
    is_uploaded_by_tenant = models.BooleanField(default=True)
    tenant_domain = models.CharField(
        verbose_name="Tenant Domain",
        max_length=100,
        null=True,
        blank=True,
    )
    tenant_company_id = models.CharField(
        verbose_name="Tenant Company ID",
        max_length=100,
        null=True,
        blank=True,
    )
    tenant_user_email = models.EmailField(
        blank=True,
        null=True, 
    )
    
    # tracker = FieldTracker()

    class Meta:
        verbose_name = _("Employee Document Id")
        verbose_name_plural = _("Employee Document Ids")
        ordering = ("created_at",)

    def __str__(self):
        return str(self.employee)
    
    def save(self, *args, **kwargs):            
        if self.select_file and 'https://bharatpayroll.s3.amazonaws.com/' not in self.select_file.url:
            file_key = f"{self.select_file.field.upload_to}{self.select_file.name}"
            s3_url = "https://bharatpayroll.s3.amazonaws.com/media/public/"+file_key
            self.select_file = s3_url     
        return super().save(*args, **kwargs)


class CertificationCourseTypes(AbstractModel):
    GRADUATION = 10
    POST_GRADUATION = 20
    DOCTORATE = 30
    DIPLOMA = 40
    PRE_UNIVERSITY = 50
    CERTIFICATION = 60
    OTHERS = 70

    CERTIFICATION_TYPE_CHOICES = (
        (GRADUATION, "Graduation"),
        (POST_GRADUATION, "Post Graduation"),
        (DOCTORATE, "Doctorate"),
        (DIPLOMA, "Diploma"),
        (PRE_UNIVERSITY, "Pre University"),
        (CERTIFICATION, "Certification"),
        (OTHERS, "Others"),
    )

    course_type = models.PositiveSmallIntegerField(
        verbose_name="Certification Course Types", choices=CERTIFICATION_TYPE_CHOICES
    )

    def __str__(self):
        return self.get_course_type_display()

    class Meta:
        verbose_name = _("Certification Course Type")
        verbose_name_plural = _("Certification Course Types")
        ordering = ["-created_at"]


class EmployeeCertifications(AbstractModel):
    employee = models.ForeignKey(
        Employee,
        verbose_name=_("Employee Certifications"),
        related_name="employee_certification",
        on_delete=models.CASCADE,
    )
    course_type = models.ForeignKey(
        "directory.CertificationCourseTypes",
        verbose_name="Employee Certification Types",
        related_name="employee_certification_types",
        limit_choices_to=models.Q(is_deleted=False),
        on_delete=models.CASCADE,
    )
    certification_title = models.CharField(
        verbose_name=_("Certification Title"),
        max_length=100,
    )
    is_verified = models.BooleanField(default=True)
    select_file = models.FileField(upload_to="employee_certifications/",max_length=512)

    class Meta:
        verbose_name = "Educational Documents"
        verbose_name_plural = "Educational Documets"


class EmployeeDocumentationWork(AbstractModel):
    employee = models.ForeignKey(
        Employee,
        verbose_name=_("Employee Documentation Work"),
        related_name="employee_documentation_work",
        on_delete=models.CASCADE,
    )
    document_title = models.CharField(
        verbose_name=_("Document Title"),
        max_length=100,
    )
    document_description = models.CharField(
        verbose_name=_("Document Description"),
        max_length=100,
        null=True,
        blank=True
    )
    select_file = models.FileField(upload_to="documentation_work/",max_length=512)
    # tracker = FieldTracker()
    
    class Meta:
        verbose_name = "Work Docs"
        verbose_name_plural = "Work Docs"

    def save(self, *args, **kwargs):        
        if self.select_file and 'https://bharatpayroll.s3.amazonaws.com/' not in self.select_file.url:
            file_key = f"{self.select_file.field.upload_to}{self.select_file.name}"
            s3_url = "https://bharatpayroll.s3.amazonaws.com/media/public/"+file_key
            self.select_file = s3_url       
        return super().save(*args, **kwargs)

    def __str__(self):
        return str(self.employee)
        
class EmployeeExperienceDetails(AbstractModel):
    employee = models.ForeignKey(
        Employee,
        related_name="employee_experience",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    company_name = models.CharField(
        verbose_name=_("Company Name"),
        max_length=100,
        null=True,
        blank=True
    )
    designation = models.CharField(
        verbose_name=_("Previous Designation"),
        max_length=100,
        null=True,
        blank=True
    )
    from_date = models.DateField(
        verbose_name="From Date",
        null=True, blank=False
    )
    to_date  = models.DateField(
        verbose_name="To Date",
        null=True, blank=False
    )
    experience = models.DecimalField(default=0, max_digits=3, decimal_places=1, null=True, blank=True)
    company_url= models.URLField(max_length=80, blank=True, null=True, verbose_name='Company URL')
    class Meta:
        verbose_name = "Experienced Years"
        verbose_name_plural = "Experienced Years"

    def __str__(self):
        return str(self.company_name)    
    
""" 
class HealthInsurence(AbstractModel):
    
    INSURENCE_CHOICES = (
        ("YES","YES"),
        ("NO","NO"),
        ("ESI","ESI"),
        ("NEED_TO_CHECK","NEED_TO_CHECK"),

    )
    employee = models.ForeignKey(
        Employee,
        verbose_name=_("Employee Health Insurence"),
        related_name="employee_Health_Insurence",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    health_insurence = models.CharField(max_length=15, choices=INSURENCE_CHOICES, null=True, blank=True)
    insurence_date = models.DateField(verbose_name="insurence Date", null=True, blank=True)
    insurence_file = models.FileField(upload_to="employee_documents/", null=True, blank=True)
    nominee_name = models.CharField(max_length=20, null=True, blank=True)
    nominee_relationship = models.CharField(max_length=20, null=True, blank=True)
    nominee_date_of_birth = models.DateField(verbose_name="nominee date of birth", null=True, blank=True)

    def __str__(self):
        return str(self.employee)

"""

class CTCHistory(models.Model):
    employee = models.ForeignKey( 
        Employee,
        related_name="employee_ctc_history",
        on_delete=models.CASCADE
    )
    updated_ctc = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    updated_at = models.DateTimeField()
    updated_by = models.ForeignKey( 
        Employee,
        related_name="updated_ctc_employee",
        on_delete=models.CASCADE
    )
    is_deleted = models.BooleanField(default = False)

class EmployeeWorkDocuments(models.Model):
    document = models.ForeignKey(EmployeeDocumentationWork, on_delete=models.CASCADE, related_name='employee_work_doc_files')
    work_doc = models.FileField(upload_to="work_documents/",max_length=512)
    is_deleted = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):    
        if self.work_doc and 'https://bharatpayroll.s3.amazonaws.com/' not in self.work_doc.url:
            file_key = f"{self.work_doc.field.upload_to}{self.work_doc.name}"
            s3_url = "https://bharatpayroll.s3.amazonaws.com/media/public/"+file_key
            self.work_doc = s3_url        
        return super().save(*args, **kwargs)
    
class CompanySMTPSetup(models.Model):
    company= models.OneToOneField(
        CompanyDetails,
        related_name="company_smpt_setup",
        on_delete=models.CASCADE,
    )
    email_host = models.CharField(max_length=100)
    email_port = models.IntegerField()
    email_host_user = models.CharField(max_length=100)
    email_host_password = models.CharField(max_length=100)
    from_email = models.EmailField()
    is_default = models.BooleanField(default=False)
       
    
class LateCheckInOutReminderCheck(models.Model):
    employee = models.ForeignKey( 
        Employee,
        related_name="forget_reminder",
        on_delete=models.CASCADE
        )
    date_of_check_in = models.DateField()
    is_late_check_in_reminder_sent = models.BooleanField(default=False)
    is_late_check_out_reminder_sent = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ("employee", "date_of_check_in")

class EmployeePreBoardingDetails(AbstractModel):
    """
    Model to save employee pre boardin details

    """

    employee = models.OneToOneField(
        Employee,
        verbose_name=_("Employee"),
        related_name="pre_boarding_details",
        on_delete=models.CASCADE,
    )
    #preboarding columns - conditional_offer_letter
    is_conditional_offer_letter_sent = models.BooleanField(default=False)
    conditional_offer_letter_status = models.CharField(max_length=20,choices=StatusChoices.choices, default="Pending")
    conditional_offer_letter = models.FileField(upload_to="conditional_offer_letters/", null=True, blank=True)
    conditional_offer_letter_content = models.TextField(null=True, blank=True)
    conditional_offer_letter_pdf_content = models.TextField(null=True, blank=True)    
    col_digital_sign = models.FileField(upload_to="col_digital_sign/", null=True, blank=True)
    col_date_of_update = models.DateTimeField(null=True, blank=True)
    col_ip_address = models.CharField(max_length=32, null=True, blank=True)
    col_sign = models.CharField(max_length=32, null=True, blank=True)
    #preboarding columns - appointment_letters
    is_appointment_letter_sent = models.BooleanField(default=False)
    appointment_letter_status = models.CharField(max_length=20,choices=StatusChoices.choices, default="Pending")
    appointment_letter = models.FileField(upload_to="appointment_letters/", null=True, blank=True)
    appointment_letter_content = models.TextField(null=True, blank=True)
    appointment_letter_pdf_content = models.TextField(null=True, blank=True)
    al_digital_sign = models.FileField(upload_to="al_digital_sign/", null=True, blank=True)
    al_date_of_update = models.DateTimeField(null=True, blank=True)
    al_ip_address = models.CharField(max_length=32, null=True, blank=True)
    al_sign = models.CharField(max_length=32, null=True, blank=True)
    
    is_bgv_complted = models.CharField(max_length=20,choices=StatusChoices.choices, default="Pending")
    added_from = models.CharField(max_length=32, default="HRMS")
    rejection_comments = models.TextField(null=True, blank=True)
    is_responding = models.BooleanField(default=True)
    is_welcome_mail_sent = models.BooleanField(default=False)
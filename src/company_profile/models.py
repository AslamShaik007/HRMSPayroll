from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from model_utils import FieldTracker
from core.models import AbstractModel
from HRMSApp.models import CompanyDetails, Roles


# Company_Profile:---Address Module:---Sub_Module:---Custom_Address_Title
class CustomAddressDetails(AbstractModel):
    company = models.ForeignKey(CompanyDetails, on_delete=models.PROTECT)
    address_title = models.CharField(max_length=20, help_text=_("Type of Address"))
    address_line1 = models.CharField(max_length=100)
    address_line2 = models.CharField(max_length=100)
    country = models.CharField(max_length=100, null=True)
    state = models.CharField(max_length=100, null=True)
    city = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    
    class Meta:
        verbose_name = "Custom Address"
        verbose_name_plural = "Custom Address"

    def __str__(self):
        return self.address_title


# Department Master Model
class Departments(AbstractModel):
    company = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    # tracker = FieldTracker()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        unique_together = (('is_deleted', 'name', 'company'), )

    def save(self, *args, **kwargs):
        if (
            self.id
            and self.employeeworkdetails_set.filter(is_deleted=False)
            and self.is_deleted
        ):
            raise ValueError("One of the related object is not deleted")
        return super().save(*args, **kwargs)


class SubDepartments(AbstractModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True, null=True)
    department = models.ForeignKey(
        Departments, related_name="sub_departments", on_delete=models.CASCADE
    )
    # tracker = FieldTracker()

    class Meta:
        verbose_name = _("Sub Departments")
        verbose_name_plural = _("Sub Departments")
        unique_together = (('name', 'department', 'is_deleted'), )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.id:
            self.slug = slugify(self.name)
        elif (
            self.id
            and self.work_details_sub_dept.filter(is_deleted=False)
            and not self.department.is_deleted
            and self.is_deleted
        ):
            raise ValueError("One of the related object is not deleted")

        return super().save(*args, **kwargs)


class Designations(AbstractModel):
    company = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE)
    name = models.CharField(
        max_length=100,
    )
    # sub_department = models.ForeignKey(
    #     SubDepartments, related_name="sub_dep_desig", on_delete=models.CASCADE, null=True, blank=True
    # )
    # department = models.ForeignKey(
    #     Departments, related_name="dep_desig", on_delete=models.CASCADE,  null=True, blank=True
    # )
    # tracker = FieldTracker()

    class Meta:
        verbose_name = "Designation"
        verbose_name_plural = "Designations"
        unique_together = (('company', 'name', 'is_deleted'), )

    def save(self, *args, **kwargs):
        if (
            self.id
            and self.employeeworkdetails_set.filter(is_deleted=False)
            and self.is_deleted
        ):
            raise serializers.ValidationError(
                {"data": {"error": "One of the related object is not deleted"}}
            )

        return super().save(*args, **kwargs)


class CompanyGrades(AbstractModel):
    company = models.ForeignKey(CompanyDetails, on_delete=models.PROTECT)
    grade = models.CharField(max_length=100)

    class Meta:
        verbose_name = _("Grade")
        verbose_name_plural = _("Grades")
        unique_together = (('company', 'grade', 'is_deleted'),)


# Announcement Model
class Announcements(AbstractModel):
    VISIBILITY = (
        ("VISIBLE_TO_ALL", "Visible To All"),
        ("LIMITED_VISIBILITY", "Limited Visibility"),
    )
    announcement_choices = (
        ("ANNOUNCEMENT", "Announcement"),
        ("TIKKER", "Tikker"),
    )
    announcement_title = models.CharField(verbose_name=_("Announcement Title"),max_length=500,null=True,blank=True)
    company = models.ForeignKey(CompanyDetails, on_delete=models.PROTECT)
    departments = models.ManyToManyField(Departments, related_name="announcements_departments", default=[])
    visibility = models.CharField(max_length=20,choices=VISIBILITY,null=True,blank=True)
    annoucement_image = models.FileField(upload_to='company_annoucement_files/',blank=True,null=True,max_length=512)
    annoucement_description = models.CharField(verbose_name=_("Announcement description"),max_length=500,null=True,blank=True)
    post_date = models.DateField(blank=True,null=True)
    expired_date = models.DateField(blank=True,null=True)
    announcement_type = models.CharField(max_length=48,choices=announcement_choices, default='ANNOUNCEMENT')
    class Meta:
        verbose_name = _("Announcement")
        verbose_name_plural = _("Announcements")

    def save(self, *args, **kwargs):              
        if self.annoucement_image and 'https://bharatpayroll.s3.amazonaws.com/' not in self.annoucement_image.url:
            file_key = f"{self.annoucement_image.field.upload_to}{self.annoucement_image.name}"
            s3_url = "https://bharatpayroll.s3.amazonaws.com/media/public/"+file_key
            self.annoucement_image = s3_url        
        return super().save(*args, **kwargs)


class Policies(AbstractModel):
    company = models.ForeignKey(CompanyDetails, on_delete=models.PROTECT)
    policy_title = models.CharField(max_length=100)
    policy_description = models.CharField(max_length=100)
    file_path = models.FileField(upload_to="company_policy_files/",max_length=512)

    class Meta:
        verbose_name = _("policies")
        verbose_name_plural = _("policies")
    
    def save(self, *args, **kwargs):        
        if self.file_path and 'https://bharatpayroll.s3.amazonaws.com/' not in self.file_path.url:
            file_key = f"{self.file_path.field.upload_to}{self.file_path.name}"
            s3_url = "https://bharatpayroll.s3.amazonaws.com/media/public/"+file_key
            self.file_path = s3_url       
        return super().save(*args, **kwargs)

# Company STATUTORY Models
class EntityTypes(AbstractModel):
    PRIVATE_LIMITED_COMPANY = 10
    PUBLIC_LIMITED_COMPANY = 20
    LIMITED_LIABILITY_PARTNERSHIP = 30
    PARTNERSHIP = 40
    SOLE_PROPRIETORSHIP = 50
    NONPROFIT_ORGANISATION = 60
    SOCIETY = 70
    TRUST = 80
    OTHERS = 90

    ENTITY_TYPE_CHOICES = (
        (PRIVATE_LIMITED_COMPANY, "Private Limited Company"),
        (PUBLIC_LIMITED_COMPANY, "Public Limited Company"),
        (LIMITED_LIABILITY_PARTNERSHIP, "Limited Liability Partnership"),
        (PARTNERSHIP, "Partnership"),
        (SOLE_PROPRIETORSHIP, "Sole Proprietorship"),
        (NONPROFIT_ORGANISATION, "Nonprofit Organisation"),
        (SOCIETY, "Society"),
        (TRUST, "Trust"),
        (OTHERS, "Others"),
    )
    entity_type = models.PositiveSmallIntegerField(
        verbose_name="Entity Types", choices=ENTITY_TYPE_CHOICES
    )

    def __str__(self):
        return self.get_entity_type_display()

    class Meta:
        verbose_name = _("Entity Type")
        verbose_name_plural = _("Entity Types")
        ordering = ["-created_at"]


# Statutory Related All Models
class StatutoryDetails(AbstractModel):
    company = models.ForeignKey(CompanyDetails, on_delete=models.PROTECT)
    entity_type = models.ForeignKey(
        EntityTypes,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    tan_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        default=None,
    )
    date_of_incorp = models.DateField(
        max_length=100,
        null=True,
        blank=True,
    )
    pan_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        default=None,
    )
    pan_image_path = models.FileField(
        upload_to="company_pan_images/",
        null=True,
        blank=True,
        default=None,
    )
    cin_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        default=None,
    )
    cin_image_path = models.FileField(
        upload_to="corporate_identity_number_images/",
        null=True,
        blank=True,
        default=None,
    )
    gst_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        default=None,
    )
    gst_image_path = models.FileField(
        upload_to="company_gst_images/",
        null=True,
        blank=True,
        default=None,
    )
    other_entity_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default='',
    )
    tds_circle_code = models.CharField(max_length=50, blank=True, null=True)    

    class Meta:
        verbose_name = _("Over View")
        verbose_name_plural = _("Over View")

    def __str__(self):
        return str(self.id)

    


class CompanyDirectorDetails(AbstractModel):
    company = models.ForeignKey(CompanyDetails, on_delete=models.PROTECT)
    director_name = models.CharField(max_length=100)
    director_mail_id = models.CharField(max_length=100)
    din_number = models.CharField(max_length=100)
    director_phone = models.CharField(max_length=100)

    class Meta:
        verbose_name = _("Directors")
        verbose_name_plural = _("Directors")

    def __str__(self):
        return str(self.pk)


class AuditorTypes(AbstractModel):
    INTERNAL = 10
    STATUTORY = 20

    AUDITOR_TYPE_CHOICES = ((INTERNAL, "Internal"), (STATUTORY, "Statutory"))
    auditor_type = models.PositiveSmallIntegerField(
        verbose_name="Auditor Types", choices=AUDITOR_TYPE_CHOICES
    )

    def __str__(self):
        return self.get_auditor_type_display()

    class Meta:
        verbose_name = _("Auditor Type")
        verbose_name_plural = _("Auditor Types")
        ordering = ["-created_at"]


class AuditorDetails(AbstractModel):
    company = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE)
    auditor_name = models.CharField(max_length=100)
    auditor_email = models.CharField(max_length=100)
    auditor_type = models.ForeignKey(AuditorTypes, on_delete=models.CASCADE)
    auditor_phone = models.CharField(max_length=100)

    class Meta:
        verbose_name = _("Auditors")
        verbose_name_plural = _("Auditors")

    def __str__(self):
        return str(self.auditor_name)


class SecretaryDetails(AbstractModel):
    company = models.ForeignKey(CompanyDetails, on_delete=models.PROTECT)
    secretary_name = models.CharField(max_length=100)
    secretary_email = models.CharField(max_length=100)
    secretary_phone = models.CharField(max_length=100)

    class Meta:
        verbose_name = _("Company Secretary")
        verbose_name_plural = _("Company Secretary")

    def __str__(self):
        return str(self.secretary_name)


# Company BANK Info
class BankAccountTypes(AbstractModel):
    CURRENT_ACCOUNT = 10
    SAVINGS_ACCOUNT = 20
    SALARY_ACCOUNT = 30
    FD_ACCOUNT = 40
    RD_ACCOUNT = 50
    NRI_ACCOUNT = 60
    NRO_ACCOUNT = 61
    NRE_ACCOUNT = 62
    FCNR_ACCOUNT = 70

    ACCOUNT_TYPE_CHOICES = (
        (CURRENT_ACCOUNT, "Current Account"),
        (SAVINGS_ACCOUNT, "Savings Account"),
        (SALARY_ACCOUNT, "Salary Account"),
        (FD_ACCOUNT, "Fixed Deposit Account"),
        (RD_ACCOUNT, "Recurring Deposit Account"),
        (NRI_ACCOUNT, "Non-Resident Indian Account"),
        (NRO_ACCOUNT, "Non-Resident Ordinary Account"),
        (NRE_ACCOUNT, "Non-Resident External Account"),
        (FCNR_ACCOUNT, "Foreign Currency Non-Resident Account"),
    )

    account_type = models.PositiveSmallIntegerField(
        verbose_name="Account Types", choices=ACCOUNT_TYPE_CHOICES
    )

    def __str__(self):
        return self.get_account_type_display()

    class Meta:
        verbose_name = _("Bank Account Type")
        verbose_name_plural = _("Bank Account Types")
        ordering = ["-created_at"]


class BankDetails(AbstractModel):
    company = models.ForeignKey(CompanyDetails, on_delete=models.PROTECT)
    account_title = models.CharField(max_length=200)
    bank_name = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    branch_name = models.CharField(max_length=100)
    ifsc_code = models.CharField(max_length=50)
    account_type = models.ForeignKey(BankAccountTypes, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=50, unique=True)
    bic = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Required, Max of 100 Characters"),
        verbose_name=_("BIC/SWIFT"),
    )
    is_default = models.BooleanField(
        verbose_name=_("Is Default"),
        default=True,
        help_text=_("Mark it if its the default Bank Account."),
    )

    class Meta:
        verbose_name = _("Bank Account Info")
        verbose_name_plural = _("Bank Account Info")

    def __str__(self):
        return self.bank_name


class LoggingRecord(models.Model):
    user_name = models.CharField(max_length=200, null=True, blank=True)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    end_point = models.TextField(blank=True, null=True)
    ip_address = models.CharField(max_length=256, null=True, blank=True)
    payload = models.JSONField(null=True, blank=True, default=dict)
    old_data = models.JSONField(null=True, blank=True, default=dict)
    method = models.CharField(max_length=200,null=True, blank=True)
    error_details = models.TextField(blank=True, null=True)
    is_success_entry = models.BooleanField(default=True)
    company_name = models.CharField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)
    model_name = models.CharField(max_length=200,null=True,blank=True)
    
    class Meta:
        verbose_name = "Audit Report"
        verbose_name_plural = "Audit Report"

class CompanyPolicyTypes(AbstractModel):
    policy_name = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        verbose_name = "Company Policy Types"
        verbose_name_plural = "Company Policy Types"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.policy_name}"
class CompanyPolicyDocuments(AbstractModel):
    class VisibilityChoices(models.TextChoices):
        VISIBLE_TO_ALL = 'VISIBLE_TO_ALL', 'Visible To All'
        LIMITED_VISIBILITY = 'LIMITED_VISIBILITY', 'Limited Visibility'
    class StatusChoices(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'InActive'
        ARCHIVE = 'ARCHIVE', 'Archive'
    
    company = models.ForeignKey(
        CompanyDetails, related_name="company_policy", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=40, blank=True, null=True)
    description = models.TextField(max_length=1000, null=True, blank=True) 
    policy_type = models.ForeignKey(CompanyPolicyTypes,on_delete=models.CASCADE, null=True, blank=True)
    visibility = models.CharField(max_length=20,choices=VisibilityChoices.choices, default="VISIBLE_TO_ALL")
    roles = models.ManyToManyField(Roles, related_name="company_policy_roles", default=[])
    status = models.CharField(max_length=20,choices=StatusChoices.choices, default="InActive")
    policy_file = models.FileField(upload_to="policy_documents/", null=True, blank=True)
    # valid_from = models.DateField(null=True, blank=True) 
    # valid_to = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Company Policy Documents"
        verbose_name_plural = "Company Policy Documents"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.title}"
    


import os

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, Permission, PermissionsMixin
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker

from core.models import AbstractModel
from core.utils import strptime, validate_file_attachment

from .managers import AttachmentManager, CountryManager, RoleManager, UserManager
from django.contrib.postgres.fields import ArrayField


# noqa  from django_chunk_upload_handlers.clam_av import validate_virus_check_result


# Role Management Table
class Roles(AbstractModel):
    """
    Creating a model for the Role.

    AJAY, 26.12.2022
    """

    DEFAULT_ADMIN_ROLES = [
        "CEO",
        "ADMIN",
        "EMPLOYEE",
        "HR",
        "MANAGER"
    ]
    name = models.CharField(verbose_name="Role Name", max_length=200)
    slug = models.SlugField(max_length=50, unique=True)
    code = models.CharField(
        verbose_name=_("Code"),
        max_length=50,
        unique=True,
        help_text=_("Required, Unique, maximum of 50 characters. A category code."),
    )
    is_active = models.BooleanField(
        verbose_name=_("Active"),
        help_text=_("True if the Role is active"),
        default=True,
    )
    permissions = models.ManyToManyField(Permission, blank=True)
    description = models.TextField(verbose_name=_("Description"), blank=True, null=True)
    is_multitenant_role = models.BooleanField(default=False, null=True, blank=True)
    objects = RoleManager()

    class Meta:
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.code is None:
            self.code = "_".join(self.name.split(" ")).upper()

        self.slug = slugify(self.code)

        return super().save(*args, **kwargs)


# Moduels
class Modules(AbstractModel):
    module_name = models.CharField(max_length=200)

    def __str__(self):
        return self.module_name

    class Meta:
        verbose_name = _("Modules")
        verbose_name_plural = _("Modules")


# Models fro Country
class Country(AbstractModel):
    """
    Has a list of all countries

    AJAY, 26.12.2022
    """

    name = models.CharField(
        verbose_name=_("Country Name"),
        max_length=200,
        help_text=_("Required, Max of 200 Characters, Name in English language"),
    )
    local_name = models.CharField(
        verbose_name=_("Local Name"),
        max_length=200,
        blank=True,
        help_text=_("Required, Max of 200 Characters, Name in local language"),
    )
    symbol = models.CharField(
        verbose_name=_("Symbol"),
        max_length=3,
        blank=True,
        # unique=True,
        help_text=_("Required, Max of 3 Characters, Country Symbol"),
    )
    calling_code = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Calling Code"),
        help_text=_("Phone Calling Code, Integer"),
    )

    objects = CountryManager()

    class Meta:
        ordering = ["name"]
        verbose_name = _("Country")
        verbose_name_plural = _("Countries")

    def __str__(self):
        return self.name


# Model For States
class States(AbstractModel):
    state_name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.state_name)

    class Meta:
        verbose_name = _("State")
        verbose_name_plural = _("States")


# Model For Features by Uday
# class Features(AbstractModel):
#     FEATURES = (
#         ('payroll', _('Payroll')),
#         ('hrms', _('HRMS')),
#     )
#     feature_name = models.CharField(default=False,max_length=100,choices=FEATURES)

#     def __str__(self):
#         return str(self.feature_name)


# Compnay _Detailes model to capture the company detailes
class CompanyDetails(AbstractModel):

    INDUSTRY_CHOICES = (
        ('Cybersecurity','Cybersecurity'),
        ('Software','Software'),
        ('Hardware and equipment', 'Hardware and equipment'),
        ('Artificial intelligence','Artificial intelligence'),
        ('Education and training','Education and training'),
        ('Data services', 'Data services'),
        ('Business services', 'Business services'),
        ('Public infrastructure', 'Public infrastructure'),
        ('Telecommunications', 'Telecommunications'),
        ('IT consulting', 'IT consulting'),
        ('Finance', 'Finance'),
        ('Simulation','Simulation'),
        ('Robotics','Robotics'),
        ('Creative services','Creative services'),
        ('Research and development','Research and development'),
        ('Energy','Energy'),
        ('Medical','Medical'),
        ('Sales and marketing','Sales and marketing'),
        ('Gaming','Gaming'),
        ('Consumer products and services','Consumer products and services'),
        ('others','others')
    )

    SHOW = 1
    HIDE = 2
    WATERMARKSTATUS=(
        (SHOW, "Show"),
        (HIDE, "Hide"),
    )
    
    company_id = models.CharField(max_length=200, unique=True, null=True, blank=True)
    company_name = models.CharField(max_length=200, unique=True, null=True, blank=True)
    company_image = models.FileField(
        upload_to="company_images/",
        null=True,
        blank=True,
    )
    brand_name = models.CharField(max_length=200, null=True, blank=True)
    web_site = models.CharField(max_length=200, null=True, blank=True)
    domain_name = models.CharField(max_length=200, null=True, blank=True)
    linked_in_page = models.CharField(max_length=200, null=True, blank=True)
    facebook_page = models.CharField(max_length=200, null=True, blank=True)
    twitter_page = models.CharField(max_length=200, null=True, blank=True)
    registered_adress_line1 = models.CharField(max_length=200, null=True, blank=True)
    registered_adress_line2 = models.CharField(max_length=200, null=True, blank=True)
    registered_country = models.CharField(max_length=100, null=True, blank=True)
    registered_state = models.CharField(max_length=100, null=True, blank=True)
    registered_city = models.CharField(max_length=200, null=True, blank=True)
    registered_pincode = models.CharField(max_length=200, null=True, blank=True)
    corporate_adress_line1 = models.CharField(max_length=200, null=True, blank=True)
    corporate_adress_line2 = models.CharField(max_length=200, null=True, blank=True)
    corporate_country = models.CharField(max_length=100, null=True, blank=True)
    corporate_state = models.CharField(max_length=100, null=True, blank=True)
    corporate_city = models.CharField(max_length=200, null=True, blank=True)
    corporate_pincode = models.CharField(max_length=200, null=True, blank=True)
    industry_type = models.CharField(choices=INDUSTRY_CHOICES, max_length=80, null=True, blank=True)
    payslip_watermark = models.FileField(upload_to="company_images/",null=True,blank=True,)
    watermark_status = models.IntegerField(choices=WATERMARKSTATUS, default=2, help_text=_("1 will treated as Show. 2 will treate as Hide."))
    is_brand_name_updated = models.BooleanField(default=False, null=True, blank=True)

    payslip_signature = models.FileField(upload_to="company_images/",null=True,blank=True)
    signature_status = models.IntegerField(choices=WATERMARKSTATUS, default=2, help_text=_("1 will treated as Show. 2 will treate as Hide."))
    decimals = models.BooleanField(default=True)
    round_offs = models.BooleanField(default=True)

    payslip_hr_email = models.CharField(max_length=200, null=True, blank=True)
    payslip_hr_phone = models.CharField(max_length=200, null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    is_multitenant = models.BooleanField(default=False)
    multitenant_key = models.CharField(max_length=256, null=True, blank=True)
    company_uid = models.CharField(max_length=200, unique=True, null=True, blank=True)
    child_company_uids = ArrayField(models.CharField(max_length=50), default=list)


    # tracker = FieldTracker()

    class Meta:
        ordering = ["created_at"]
        get_latest_by = "created_at"
        verbose_name = _("Organization")
        verbose_name_plural = _("Organization")

    def __str__(self):
        return str(self.company_name)

    def save(self, *args, **kwargs):        
        if self.company_image and 'https://bharatpayroll.s3.amazonaws.com/' not in self.company_image.url:
            file_key = f"{self.company_image.field.upload_to}{self.company_image.name}"
            s3_url = "https://bharatpayroll.s3.amazonaws.com/media/public/"+file_key
            self.company_image = s3_url  
            
        if self.payslip_watermark and 'https://bharatpayroll.s3.amazonaws.com/' not in self.payslip_watermark.url:
            file_key = f"{self.payslip_watermark.field.upload_to}{self.payslip_watermark.name}"
            s3_url = "https://bharatpayroll.s3.amazonaws.com/media/public/"+file_key
            self.payslip_watermark = s3_url  

        if self.payslip_signature and 'https://bharatpayroll.s3.amazonaws.com/' not in self.payslip_signature.url:
            file_key = f"{self.payslip_signature.field.upload_to}{self.payslip_signature.name}"
            s3_url = "https://bharatpayroll.s3.amazonaws.com/media/public/"+file_key
            self.payslip_signature = s3_url  
                
        return super().save(*args, **kwargs)
class CompanyCustomizedConfigurations(AbstractModel):
    """
    Created-By: Padmaraju P
    Description: Giving Customizations to All Over Company
    """
    company = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE, related_name = "company_config")
    can_payroll_auto_deactivate = models.BooleanField(default=False, null=True, blank=True)
    can_payroll_auto_deactivate_description = models.TextField(null=True, blank=True)
    compoff_apply_days_excemption = models.IntegerField(default=0, null=True, blank=True)
    compoff_apply_days_excemption_description = models.TextField(null=True, blank=True)
    max_days_to_utilize_compoff = models.IntegerField(default=60, null=True, blank=True)
    max_days_to_utilize_compoff_description = models.TextField(null=True, blank=True)
    
    
    def __str__(self):
        return f'{self.company.company_name} Configurations'

class User(
    AbstractBaseUser,
    PermissionsMixin,
    AbstractModel,
):
    username_validator = UnicodeUsernameValidator()

    email = models.EmailField(
        verbose_name="Email",
        max_length=255,
        unique=True,
        help_text=_("Required, Please enter your Email Address."),
        error_messages={
            "unique": _("This email already exists."),
        },
    )
    username = models.CharField(
        verbose_name=_("Username"),
        max_length=255,
        null=True,
        help_text=_(
            "Required. 256 characters or fewer. " "Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    phone = models.CharField(
        verbose_name=_("Phone"), max_length=20, unique=True, blank=True, null=True
    )
    is_active = models.BooleanField(
        verbose_name=_("Active"),
        default=False,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    is_staff = models.BooleanField(
        verbose_name=_("Staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    first_name = models.CharField(
        verbose_name=_("First name"), max_length=128, blank=True
    )
    middle_name = models.CharField(
        verbose_name=_("Middle name"), max_length=128, blank=True
    )
    last_name = models.CharField(
        verbose_name=_("Last name"), max_length=128, blank=True
    )
    date_joined = models.DateTimeField(
        verbose_name=_("Date joined"), default=timezone.now
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    # REQUIRED_FIELDS = ["email"]
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        return self.email

    class Meta:
        get_latest_by = "created_at"


#  Custom User Model
class Registration(AbstractModel):
    r"""
    Registration Model

    * phoneNumberRegex = RegexValidator(regex = r"^\+?1?\d{8,15}$") # noqa
    * phoneNumber = models.CharField(validators = [phoneNumberRegex], max_length = 16, unique = True)

    """

    class Meta:
        verbose_name = _("Registration")
        verbose_name_plural = _("Registrations")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, help_text=_("User"), related_name="rel_user"
    )

    email = models.EmailField(
        verbose_name="Email",
        max_length=50,
        unique=True,
        help_text=_("Required, Please enter your Email Address."),
        error_messages={
            "unique": _("This email already exists."),
        },
    )

    name = models.CharField(
        verbose_name="Registration Name",
        max_length=50,
        help_text=_("Name while registration"),
        error_messages={
            "unique": _("Name is already exists."),
        },
    )

    terms_and_conditions = models.BooleanField(
        verbose_name="Terms And Conditions",
        help_text=_("Compnany Terms and Conditions"),
        default=False,
    )
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    company = models.ForeignKey(
        CompanyDetails, on_delete=models.PROTECT, blank=True, null=True, related_name="company"
    )
    company_size = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name = "Company Registration"
        verbose_name_plural = "Company Registrations"

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return self.is_active

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True


# Assigned Modules Model
class AssignedModules(AbstractModel):
    registered_user = models.ForeignKey(Registration, on_delete=models.PROTECT)
    module = models.ForeignKey(Modules, on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("Assgined Module")
        verbose_name_plural = _("Assgined Modules")


class PhoneOTP(AbstractModel):
    username = models.CharField(max_length=254, blank=True, default=False)
    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,14}$",
        message="Phone number must be entered in the form of +919999999999.",
    )
    email = models.CharField(max_length=254, blank=True, null=True)
    phone = models.CharField(validators=[phone_regex], max_length=17)
    otp = models.CharField(max_length=9, blank=True, null=True)
    count = models.IntegerField(default=0, help_text="Number of sent otps")
    validated = models.BooleanField(
        default=False,
        help_text="if it is true, that means user have validate otp correctly in seconds",
    )

    def __str__(self):
        return f"{self.phone} is sent to {self.otp}"

    class Meta:
        verbose_name = _("PhoneOTP")
        verbose_name_plural = _("PhoneOTP")


class FutureModule(AbstractModel):
    SUCCESS = 10
    FAIL = 20
    QUEUE = 30

    STATUSES = (
        (SUCCESS, "Success"),
        (FAIL, "Error"),
        (QUEUE, "Queued"),
    )

    employee_model = models.Q(app_label="directory", model="Employee")
    department_model = models.Q(app_label="company", model="Department")

    limited_models = employee_model | department_model

    serializer = models.CharField(
        verbose_name=_("Serailizer class"),
        max_length=255,
        help_text=_("serializer class used to save or update the information."),
    )
    content_type = models.ForeignKey(
        ContentType,
        limit_choices_to=limited_models,
        on_delete=models.SET_NULL,
        verbose_name=_("Content Type"),
        null=True,
    )
    payload = models.JSONField(
        verbose_name=_("payload"),
        default=dict,
        help_text=_("Data saved to DB in future"),
    )
    effective_date = models.DateField(verbose_name=_("Effective Date"))
    status = models.PositiveSmallIntegerField(
        verbose_name=_("Status"), choices=STATUSES, default=QUEUE
    )
    logs = models.TextField(verbose_name=_("Log messages"), blank=True, null=True)
    
    class Meta:
        verbose_name = "Future Module"
        verbose_name_plural = "Future Modules"

    def save(self, *args, **kwargs):
        if isinstance(self.effective_date, str):
            self.effective_date = strptime(
                self.effective_date,
            )

        return super().save(*args, **kwargs)


class Attachment(AbstractModel):
    """
    A File model can be attached to any kind of object

    """

    investment_declaration_model = models.Q(
        app_label="investment_declaration", model="DeclarationForms"
    )

    limited_models = investment_declaration_model

    # content_type = models.ForeignKey(
    #     ContentType,
    #     limit_choices_to=limited_models,
    #     on_delete=models.CASCADE,
    #     verbose_name=_("Content Type"),
    # )
    object_id = models.IntegerField(verbose_name=_("Object ID"))
    # content_object = GenericForeignKey("content_type", "object_id")

    title = models.CharField(
        verbose_name=_("Title"),
        max_length=255,
        help_text=_("Required, Max of 255 Characters."),
    )
    document = models.FileField(
        verbose_name=_("Public Attachment"),
        upload_to="uploads/%Y/%m/%d/",
        max_length=255,
        blank=True,
        null=True,
        validators=[validate_file_attachment],
    )

    objects = AttachmentManager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")

    def __str__(self):
        return self.title

    @property
    def file(self):
        """
        Return the document or private document

        """
        return self.document

    @property
    def file_name(self):
        file = self.document
        if file:
            try:
                return self.document.name.split("/")[-1]
            except Exception:
                return self.document.name

    @property
    def relative_file_name(self):
        return os.path.basename(self.document.name)

    def get_size(self):
        """
        Retrieve the Size if it's available
        """
        file = self.document
        if file:
            try:
                return self.file.size
            except Exception:
                return 0
        return 0


@receiver(post_delete, sender=Attachment)
def auto_delete_attachment_document_on_delete(sender, instance, **kwargs):
    """
    Delete attachment document when Attachment is deleted.
    Cannot delete instance.document as this is public document and shared across all objects.

    """
    instance.document.delete(save=False)


class Grade(models.Model):
    
    name = models.CharField(max_length=256)
    company = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Add Grade Lable"
        verbose_name_plural = "Add Grade Lables"

    def __str__(self):
        return f'{self.company.company_name} - {self.name}'
    
    
class MultiTenantCompanies(models.Model):
    mul_key = models.CharField(max_length=256)
    cmp_id = models.CharField(max_length=256)
    subdomain = models.CharField(max_length=256)
    is_multitenant = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)
    companyname = models.CharField(max_length=256)
    
    class Meta:
        managed = False
        db_table = "companies"
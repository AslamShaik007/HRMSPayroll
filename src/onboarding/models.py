from django.db import models

from directory.models import Employee
from core.models import AbstractModel
from company_profile.models import CompanyDetails

# Create your Choices here.
class StatusChoices(models.TextChoices):
    Active = 'Active', 'Active'
    InActive = 'InActive', 'InActive'
        
class TaskType(models.TextChoices):
    PREONBOARDING = 'Pre_On_Boarding', 'Pre On Boarding'
    POSTONBOARDING = 'Post_On_Boarding', 'Post On Boarding'
    
# Create your models here.
class Template(models.Model):
    name = models.CharField(max_length=256)
    status = models.CharField(max_length=20,choices=StatusChoices.choices, default="InActive")
    is_deleted = models.BooleanField(default=False)

class OnBoardingModule(AbstractModel):                            # main module
    company  = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE)
    tenent_id = models.CharField(max_length=256, blank=True, null=True)
    template = models.ForeignKey(Template,related_name="onboardingmodule_template", on_delete=models.CASCADE)
    
class EmployeeOnboardStatus(models.Model):
    employee = models.ForeignKey(Employee, related_name="completed_onboard", on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    onboarding_module  = models.ForeignKey(OnBoardingModule, on_delete=models.CASCADE)
    is_deleted=models.BooleanField(default=False)

class OnBoardingSubModule(AbstractModel):                        # Sub modules
    name = models.CharField(max_length=256)
    module = models.ForeignKey(OnBoardingModule, on_delete=models.CASCADE, related_name="on_boarding_sub_modules")
    task_type = models.CharField(max_length=256, choices=TaskType.choices)
    status = models.CharField(max_length=20,choices=StatusChoices.choices, default="InActive")

class OnBoardingTask(AbstractModel):                               # tasks 
    name = models.CharField(max_length=256, blank=True, null=True)
    description = models.TextField(null=True, blank=True)
    sub_module = models.ForeignKey(OnBoardingSubModule, on_delete=models.CASCADE, related_name="on_boarding_task")
    # accessed_by = models.ManyToManyField(Employee, related_name="task_accessed_by", default=[]) # on Hold
    
class OnBoardingCheckList(AbstractModel):                        # check fields
    title = models.CharField(max_length=256, blank=True, null=True)
    task = models.ForeignKey(OnBoardingTask, on_delete=models.CASCADE,related_name="on_boarding_check_lists")
    check_name = models.TextField(blank=True, null=True)

class EmployeeCheckList(AbstractModel):  # to mark weather check fields are completed or not 
    task_check = models.ForeignKey(OnBoardingCheckList, on_delete=models.CASCADE, related_name='employee_check_list')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)

class OnBoardingFiles(models.Model):
    task_files = models.ForeignKey(OnBoardingTask, on_delete=models.CASCADE,related_name="on_boarding_task_files")
    file_name = models.CharField(max_length=256, blank=True, null=True)
    onboarding_file = models.FileField(upload_to="onboarding_documents/", null=True, blank=True)
    is_deleted = models.BooleanField(default=False)


""" 
Discussions::
####################################################################

Module Name
OnBoardID
Company ID
TenantID
Previlages/Role
Template Name
TemplateID
EmpID
IsOnBoardingCompletedStatus

Sub Module Name
SubModID
PreJoin / PostJoin
Status
IsDelete

Item Name
ItemID
Description
Checklist
Owner
Accessed By
ProgressBar
Documents
IsDelete
    
"""
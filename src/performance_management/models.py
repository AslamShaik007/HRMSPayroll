from django.db import models
from core.models import AbstractModel
from HRMSApp.models import CompanyDetails
# Create your models here.

#Monthly KRA Set Names
class AppraisalSetName(AbstractModel):
    company = models.ForeignKey(
        "HRMSApp.CompanyDetails",
        on_delete=models.CASCADE,
        related_name="company_setname",
        verbose_name="Company",
        help_text="Enter Primary Key of CompanyDetails Model"
    )
    author = models.ForeignKey(
        "directory.Employee",
        on_delete=models.CASCADE,
        related_name="author_employee",
        verbose_name="Author",
        help_text="Enter Primary Key Of Employee Model"
    )
    name = models.CharField(
        max_length=100,
        verbose_name="Employee Appraisal Set Name",
        help_text="Enter Set Names For Add Quationnaires"
    )
    set_number = models.IntegerField(
        verbose_name="Set Number",
        help_text="Set Number Will Be Increases by Default",
        null=True,
        blank=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Status",
        help_text="Status Will Be Taken As Active Or Inactive, But Default It Will Be Active"
    )
    
    class Meta:
        verbose_name = "ADD Questionnaire"
        verbose_name_plural = "ADD Questionnaires"

    def __str__(self):
        return str(self.name)


class AppraisalSetQuestions(AbstractModel):
    set_name = models.ForeignKey(
        AppraisalSetName,
        on_delete=models.CASCADE,
        related_name="setname_questions",
        verbose_name="Set Names",
        help_text="Enter The Primary Key Of Set_Names Model"
    )
    is_active  = models.BooleanField(
        default=True,
        verbose_name="Status",
        help_text="Status Will Be Taken As Active Or Inactive, But Default It Will Be Active"
    )
    creation_date = models.DateTimeField(
        auto_now=True,
        verbose_name="Creation Date",
        help_text="Current DateTime Will Be Add by Default"
    )
    questions = models.CharField(
        max_length=500,
        verbose_name="Questions",
        help_text="Enter Multiple Questions In a Array[]"
    )
    
    class Meta:
        verbose_name = "Questionnaire"
        verbose_name_plural = "Questionnaires"

    def __str__(self) -> str:
        return self.questions




class AppraisalSendForm(AbstractModel):
    employee = models.ForeignKey(
        "directory.Employee",
        on_delete=models.CASCADE,
        related_name="sendform_employee",
        verbose_name="Employee",
        help_text="Enter Primary Key Of Employee Model"
    )
    set_id = models.ForeignKey(
        AppraisalSetName,
        on_delete=models.CASCADE,
        related_name="setnumber_id",
        verbose_name="Set Number",
        help_text="Enter Primary Key Of Appraisal Set Name Model"
    )
    creation_date = models.DateTimeField(
        auto_now=True,
        verbose_name="Creation Date",
        help_text="Date Will Be Add Default Current Date And Time",
        null=True, blank=True
    )
    candidate_status = models.CharField(
        max_length=100,
        default="NOT SUBMITTED",
        verbose_name="Candidate Status",
        help_text="It Will Be a Not Submitted,Till He Didn't Submitte the KRA Form,After Submitteing KRA It Will Be Change To Submitted"
    )
    Emp_suggestion = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Employee Suggestion",
        help_text="Employee Will Add There Suggestions Here If Any"
    )
    manager_acknowledgement = models.CharField(
        max_length=500,
        default="PENDING",
        verbose_name="Manager Acknowledgement",
        help_text="Till Manager Give Score To An Employee Its Pending,After Giving Score Its Will Be Submitted"
    )
    score = models.FloatField(
        default=0,
        verbose_name="Score",
        help_text="Enter Score For An Employee"
    )
    monthly_score_status = models.CharField(
        max_length=100,
        default="PENDING",
        verbose_name="Monthly Score Status",
        help_text="If Score Is Add To An Employee It Will Be Change To On-Track,Default It Will Be Pending"
    )
    email_status = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Email Status",
        help_text="Enter Sent, If Email As Send To His Official Email"
    )
    is_revoked = models.BooleanField(blank=True, null=True, default=False)
    comment = models.TextField(
        blank=True,
        verbose_name="Comment",
        help_text="Comment Will Be Add To An Employee By Manager"
    )
    reason = models.TextField(
        blank=True,
        verbose_name="Reason",
        help_text="Reason Will be Add To An Employee According To Given Score"
    )
    form_deadline_date = models.DateField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Send Form"
        verbose_name_plural = "Send Forms"

    def __str__(self) -> str:
        return self.set_id.name



class NotificationDates(AbstractModel):
    company = models.ForeignKey(
        CompanyDetails,
        on_delete=models.CASCADE,
        related_name="notification_date",
        verbose_name="Notification",
        help_text="Notification Will Use To Reminder Mail Of Monthly KRA",
        null=True,
        blank=True
    )
    notification_start_date = models.DateField( null=True,
        blank=True)
    notification_end_date = models.DateField( null=True,
        blank=True)
    reporting_manager_start_date = models.DateField( null=True,
        blank=True)
    reporting_manager_end_date = models.DateField( null=True,
        blank=True)
    employees_kra_deadline_date = models.DateField( null=True,
        blank=True)
    
    class Meta:
        verbose_name = "Notification Date"
        verbose_name_plural = "Notification Dates"

    def __str__(self):
        return str(self.id)


class AppraisalFormSubmit(AbstractModel):
    employee = models.ForeignKey(
        "directory.Employee",
        on_delete=models.CASCADE,
        related_name="employee_appraisalform",
        verbose_name="Employee",
        help_text="Enter a Primary Key Of the Employee Model"
    )
    set_name = models.ForeignKey(
        AppraisalSetName,
        on_delete=models.CASCADE,
        related_name="setname_appraisal",
        verbose_name="Set Name",
        help_text="Enter a Primary Key Of AppraisalSetName Model"
    )
    question = models.ForeignKey(
        AppraisalSetQuestions,
        on_delete=models.CASCADE,
        related_name="question_appraisal",
        verbose_name="Question_id",
        help_text="Enter a Primary Key Of Appraisalsetquestions Model"
    )
    answer = models.TextField(
        # max_length=800,
        null=True,
        blank=True,
        verbose_name="Answer",
        help_text="Enter The Answer For The Given Question"
    )
    sentform_date = models.DateTimeField(
        auto_now=True,
        verbose_name="Sent Form Date",
        help_text="It Will Take Current Date And Time By Default"
    )
    candidate_status = models.CharField(
        max_length=100,
        verbose_name="Candidate Status",
        help_text="Employee Can Be Enter Like Save Or Submit"
    )

    class Meta:
        verbose_name = "Appraisal Form Submit"
        verbose_name_plural = "Appraisal Form Submit"

    # def __str__(self) -> str:
    #     return self.answer
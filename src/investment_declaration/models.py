from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import AbstractModel
from model_utils import FieldTracker

class FormChoices(AbstractModel):
    formtype = models.CharField(
        max_length=100,
        verbose_name="Form Choices",
        help_text="Form Choices",
    )

    def __str__(self):
        return f"{self.formtype}"

    class Meta:
        verbose_name = _("Form Choice")
        verbose_name_plural = _("Form Choices")


class SubFormChoices(AbstractModel):
    parentform = models.ForeignKey(
        "FormChoices",
        on_delete=models.CASCADE,
        verbose_name="Parent Form",
        help_text="Parent Form from form choices",
        related_name="form_choices",
    )
    formtype = models.CharField(
        max_length=100,
        verbose_name="Form Choices",
        help_text="Form Choices",
    )

    def __str__(self):
        return f"{self.id} - {self.formtype}"

    class Meta:
        verbose_name = _("SUb Form Choice")
        verbose_name_plural = _("Sub Form Choices")


class InvestmentDeclaration(AbstractModel):
    SAVED = 10
    SUBMIT = 20
    RE_SUBMIT = 30
    CANCEL = 40
    REVOKED = 50
    APPROVE = 60
    APPROVE_REVOKED = 70
    DECLINE = 80    
    FINAL_APPROVED = 90

    STATUS_CHOICES = (
        (SAVED, "Saved"),
        (SUBMIT, "Submitted"),
        (RE_SUBMIT, "Re Submitted"),
        (CANCEL, "Cancel"),
        (REVOKED, "Revoked"),
        (APPROVE, "Approved"),
        (APPROVE_REVOKED, "Approve_revoked"),
        (DECLINE, "Declined"),
        (FINAL_APPROVED, "Final_Approved"),        
    )

    OLD_TAX_REGIME = 10
    NEW_TAX_REGIME = 20

    REGIME_CHOICES = (
        (OLD_TAX_REGIME, "Old Tax Regime"),
        (NEW_TAX_REGIME, "New Tax Regime"),
    )

    RESUBMITTED_CHOICES = (
        (APPROVE, "Approved"),
        (REVOKED, "Revoked"),
        (RE_SUBMIT, "Re Submitted"),
        (FINAL_APPROVED, "Final_Approved"),
        (DECLINE, "Declined"),
        (SAVED, "Saved"),
        
    )

    employee = models.ForeignKey(
        "directory.Employee",
        on_delete=models.CASCADE,
        verbose_name="Employee",
        help_text="Employe Primary Key Of Employee",
    )
    regime_type = models.PositiveSmallIntegerField(
        choices=REGIME_CHOICES,
        verbose_name="Regime Type",
        help_text="It indicates the employee choose which regime he belongs to.",
        null=True,
        blank=True
    )
    declaration_amount = models.DecimalField(
        verbose_name=_("Total Declaration Amount"),
        default=0.00,
        max_digits=12,
        decimal_places=2,
        help_text=_("Employee Total Declaration Amount"),
    )
    income_from_previous_employer = models.DecimalField(
        verbose_name=_("Income From Previous Employer"),
        default=0.00,
        max_digits=12,
        decimal_places=2,
        help_text=_("Income From Previous Employer"),
        null=True,
        blank=True,
    )
    tds_from_previous_employer = models.DecimalField(
        verbose_name=_("TDS From Previous Employer"),
        default=0.00,
        max_digits=12,
        decimal_places=2,
        help_text=_("TDS From Previous Employer"),
        null=True,
        blank=True,
    )
    approved_amount = models.DecimalField(
        verbose_name=_("Total Approved Amount"),
        default=0.00,
        max_digits=12,
        decimal_places=2,
        help_text=_("Employee Total Approved Amount"),
    )
    final_declared_amount = models.DecimalField(
        verbose_name=_("Total Final Declared Amount"),
        default=0.00,
        max_digits=12,
        decimal_places=2,
        help_text=_("Employee Total Final Declared Amount"),
    )
    final_approved_amount = models.DecimalField(
        verbose_name=_("Total Final Approved Amount"),
        default=0.00,
        max_digits=12,
        decimal_places=2,
        help_text=_("Employee Total Final Approved Amount"),
    )
    savings_after_ctc = models.DecimalField(
        verbose_name=_("Savings After CTC"),
        default=0.00,
        max_digits=12,
        decimal_places=2,
        help_text=_("Employee Savings After CTC"),
    )
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES,
        verbose_name="Form Status",
        help_text="Approval or Submit status representations",
        null=True,
        blank=True,
    )
    admin_resubmit_status = models.PositiveSmallIntegerField(choices=RESUBMITTED_CHOICES, null=True, blank=True) 
    start_year = models.IntegerField(verbose_name="Declaration Start Year", blank=True)
    end_year = models.IntegerField(verbose_name="Declaration End Year", blank=True)
    approval_date = models.DateField(
        verbose_name="Approved Date",
        null=True,
        blank=True,
    )
    submitted_date = models.DateField(
        verbose_name="Submitted Date",
        null=True,
        blank=True,
    )
    
    freeze_declared_status = models.BooleanField(default=True)
    freeze_final_declared_status = models.BooleanField(default=True)
    access_to_select_regime = models.BooleanField(default=False)

    last_submission_date = models.DateField(
        verbose_name="Last Submission Date",
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.employee}"

    class Meta:
        verbose_name = "Saving Declaration Form"
        verbose_name_plural = "Saving Declaration Form"
        unique_together = ("employee", "start_year", "end_year")


class DeclarationForms(AbstractModel):
    """
    Model to save declaration forms information

    """
    parentform_type = models.ForeignKey(
        FormChoices,
        on_delete=models.CASCADE,
        verbose_name="Parent Form Type",
        null=True,
        blank=True,
    )
    subform_type = models.ForeignKey(
        SubFormChoices,
        on_delete=models.CASCADE,
        verbose_name="Sub Form Type",
        null=True,
        blank=True,
    )

    declaration = models.ForeignKey(
        "InvestmentDeclaration",
        on_delete=models.CASCADE,
        verbose_name="Investment Declaration",
        help_text="Relation to the declarations",
        related_name="declaration_forms"
    )
    declared_amount = models.DecimalField(
        verbose_name=_("Declared Amount"),
        default=0.00,
        max_digits=12,
        decimal_places=2,
        help_text=_("Employee Savings Declared Amount"),
    )
    approved_amount = models.DecimalField(
        verbose_name=_("Approved Amount"),
        default=0.00,
        max_digits=12,
        decimal_places=2,
        help_text=_("Employee Approved Amount"),
    )
    final_declared_amount = models.DecimalField(
        verbose_name=_("Employee Final Declared Amount"),
        default=0.00,
        max_digits=12,
        decimal_places=2,
        help_text=_("Employee Final Declared Amount"),
        null=True,
        blank=True
    )
    final_approved_amount = models.DecimalField(
        verbose_name=_("Employee Final Approved Amount"),
        default=0.00,
        max_digits=12,
        decimal_places=2,
        help_text=_("Employee Final Approved Amount"),
    )
    no_of_attachments = models.IntegerField(
        verbose_name="Form Attachments Count",
        default=0,
        blank=True,
        null=True,
    )
    comments_from_employee = models.CharField(
        verbose_name="Comments",
        max_length=500,
        null=True,
        blank=True,
    )
    comments_from_employer = models.CharField(
        verbose_name="Comments",
        max_length=500,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Declaration Form")
        verbose_name_plural = _("Declaration Forms")
        ordering = ("created_at",)
        unique_together = ("declaration", "id")

    def __str__(self):
        return (
            f" ({self.declaration.start_year} - {self.declaration.end_year})"
            f" - {self.declaration.employee.name}"
        )


class Attachments(AbstractModel):
    investment_declaration = models.ForeignKey(
        InvestmentDeclaration, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        )
    declaration_form = models.ForeignKey(
        DeclarationForms,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    attachment = models.FileField(
        upload_to="Investment_Attachments",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Attachments")
        verbose_name_plural = _("Attachmnets")
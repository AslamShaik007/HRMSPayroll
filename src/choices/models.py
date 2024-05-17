from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.mixins import OrderableModelMixin
from core.models import AbstractModel
from HRMSApp.models import CompanyDetails

from .managers import ChoicesManager


class ChoiceType(AbstractModel):
    """
    Dropdown list field name.

    AJAY, 26.01.2023
    """

    employee_model = models.Q(app_label="directory", model="employee")
    company_model = models.Q(app_label="HRMSApp", model="companydetails")
    clock_model = models.Q(app_label="attendance", model="EmployeeCheckInOutDetails")
    investment_declaration_model = models.Q(
        app_label="investment_declaration", model="InvestmentDeclaration"
    )
    limited_models = (
        employee_model | company_model | clock_model | investment_declaration_model
    )

    slug = models.CharField(max_length=150, help_text=_("Auto Generated Text"))
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, verbose_name=_("description"))
    # content_type = models.ForeignKey(
    #     ContentType,
    #     limit_choices_to=limited_models,
    #     on_delete=models.SET_NULL,
    #     verbose_name=_("Content Type"),
    #     null=True,
    # )
    company = models.ForeignKey(
        CompanyDetails,
        on_delete=models.CASCADE,
        verbose_name="Company",
        help_text="Related Company Choices",
    )

    def __str__(self):
        return self.name


class Choices(AbstractModel, OrderableModelMixin):
    """
    Dropdown list choices

    AJAY, 04.05.2023
    """

    choice_type = models.ForeignKey(
        ChoiceType, related_name="choices", on_delete=models.CASCADE
    )
    key = models.CharField(_("Key"), max_length=255, blank=True, default="")
    value = models.CharField(_("Value"), max_length=255, blank=True, default="")
    is_active = models.BooleanField(
        verbose_name=_("Active"),
        default=True,
    )
    parent = models.ForeignKey(
        "self",
        verbose_name=_("Parent Category"),
        blank=True,
        null=True,
        related_name="parent_set",
        on_delete=models.CASCADE,
    )

    ordering = models.IntegerField(verbose_name=_("Ordering"), default=0)

    objects = ChoicesManager()

    class Meta:
        ordering = ["ordering"]
        verbose_name = _("Choices")
        verbose_name_plural = _("Choices")

    def __str__(self):
        return f"[ {self.choice_type} ] {self.value}"

    def get_ascendants(self, include_self=True):
        """
        Return all parents to root.

        AJAY, 31.01.2023
        """
        model = self.__class__
        ascendants = model.objects.none()

        if self.parent:
            ascendants |= self.parent.get_ascendants()

        if include_self:
            ascendants |= model.objects.filter(pk=self.pk)

        return ascendants.order_by("created_at")

    def levels(self):
        """
        For display in admin.

        AJAY, 31.01.2023
        """
        return " > ".join(list(self.get_ascendants().values_list("value", flat=True)))

    def get_descendants(self, include_self=True):
        """
        Get all descendants. Recursively.

        AJAY, 31.01.2023
        """
        model = self.__class__
        if include_self:
            descendants = model.objects.filter(pk=self.pk)
        else:
            descendants = model.objects.none()
        if self.parent_set.exists():
            for choice in self.parent_set.all():
                descendants |= choice.get_descendants()
        return descendants

    def get_flat_descendants(self, include_self=True):
        """
        Get all descendants. Only PK.

        AJAY, 31.01.2023
        """
        return self.get_descendants(include_self).values_list("pk", flat=True)

    def get_siblings(self):
        """
        Combine descendants and ascendants.

        AJAY, 31.01.2023
        """
        qs = self.get_descendants() | self.get_ascendants(include_self=False)
        return qs.order_by("created_at")

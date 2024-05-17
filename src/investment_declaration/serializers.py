import logging
# from decimal import Decimal as D

# from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework import serializers

# from rest_framework.status import HTTP_400_BAD_REQUEST

# from core.serializers import QuerysetFilterSerializer
from investment_declaration.models import (
    DeclarationForms,
    InvestmentDeclaration,
    FormChoices,
    SubFormChoices,
    Attachments,
)
from payroll.utils import ctc_to_gross_per_year

logger = logging.getLogger(__name__)


class SubFormChoicesSerializer(serializers.ModelSerializer):
    # form_choices = FormChoicesSerializer(read_only=True)

    class Meta:
        model = SubFormChoices
        fields = ("id", "formtype")


class FormChoicesSerializer(serializers.ModelSerializer):
    form_choices = SubFormChoicesSerializer(many=True)
    # form_choices = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = FormChoices
        depth = 1
        fields = (
            "id",
            "formtype",
            "form_choices",
        )


class AttachmentsSerializer(serializers.ModelSerializer):
    """
    Serializer for saving the attachments
    """
    
    class Meta:
        model = Attachments
        fields = (
            "id",
            "declaration_form",
            "attachment",
        )


class InvestmentDeclarationSerializer(serializers.ModelSerializer):
    """
    Investment Declaration serializer
    """

    class Meta:
        model = InvestmentDeclaration
        fields = (
            "id",
            "employee",
            "regime_type",
            "declaration_amount",
            "income_from_previous_employer",
            "tds_from_previous_employer",
            "approved_amount",
            "final_declared_amount",
            "final_approved_amount",
            "savings_after_ctc",
            "status",
            "start_year",
            "end_year",
            "approval_date",
            )


class DeclarationFormsSerializer(serializers.ModelSerializer):
    """
    Declaration Forms serializer
    """
    # attachments = AttachmentsSerializer(many=True, read_only=True)
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = DeclarationForms
        fields = (
            "id",
            "parentform_type",
            "subform_type",
            "declaration",
            "declared_amount",
            "approved_amount",
            "final_declared_amount",
            "final_approved_amount",
            "comments_from_employee",
            "comments_from_employer",
            "attachments",
        )
    
    def get_attachments(self, obj):
        context=[]
        if attachments := Attachments.objects.filter(declaration_form=obj.id):
            for att in attachments:
                context.append({'id': att.id, 'name': att.attachment.name})
            return {
                "filespath": context,
            }
        return {"filespath":"-"}


class InvestmentDeclarationDetailSerializer(serializers.ModelSerializer):
    """
    SURESH, 10.05.2023
    """

    employee_data = serializers.SerializerMethodField()
    status = serializers.ChoiceField(choices=InvestmentDeclaration.STATUS_CHOICES)
    admin_resubmit_status = serializers.ChoiceField(choices=InvestmentDeclaration.RESUBMITTED_CHOICES)
    status_display = serializers.ChoiceField(
        choices=InvestmentDeclaration.STATUS_CHOICES, source="get_status_display"
    )
    admin_rstatus_display = serializers.ChoiceField(
        choices=InvestmentDeclaration.RESUBMITTED_CHOICES, source="get_admin_resubmit_status_display"
    )
    regime_type_display = serializers.ChoiceField(
        choices=InvestmentDeclaration.REGIME_CHOICES, source="get_regime_type_display"
    )
    declaration_forms = DeclarationFormsSerializer(many=True, required=False)
    forms_count = serializers.SerializerMethodField()
    attachments_count = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    submitted_forms = serializers.SerializerMethodField()
    files_count = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentDeclaration
        fields = (
            "id",
            "employee",
            "employee_data",
            "regime_type",
            "regime_type_display",
            "declaration_amount",
            "approved_amount",
            "final_declared_amount",
            "income_from_previous_employer",
            "tds_from_previous_employer",
            "final_approved_amount",
            "savings_after_ctc",
            "status",
            "status_display",
            "admin_resubmit_status",
            "admin_rstatus_display",
            "start_year",
            "end_year",
            "attachments",
            "files_count",
            "approval_date",
            "updated_at",
            "forms_count",
            "submitted_forms",
            "attachments_count",
            "declaration_forms",
        )

    def get_employee_data(self, obj):
        try:
            employee = obj.employee            
            department = employee.work_details.department            
            ctc = employee.salary_details.ctc
            gross_per_year = ctc_to_gross_per_year(ctc,0)

            return {
                "id": employee.id,
                "name": employee.name,
                "employee_number": employee.work_details.employee_number,
                "department": department.name if department else " ",
                "organization": employee.company.company_name,
                "ctc":ctc,
                "gross_per_year":gross_per_year
            }
        except Exception as e:            
            logger.warn(
                f"Employee {obj} with id: {obj.id} don't have work details information."
            )
            return {
                "id": obj.id,
                "name": obj.employee.name,
                "employee_number": " ",
                "department": " ",
                "organization": obj.employee.company.company_name,
            }
    
    def get_attachments(self,obj):
        context=[]
        if attachments := Attachments.objects.filter(investment_declaration=obj.id):
            for att in attachments:
                context.append({'id': att.id, 'name': att.attachment.name})
            return {
                "filespath": context,
            }
        return {"filespath":"-"}
    
    def get_forms_count(self, obj):
        if forms := DeclarationForms.objects.filter(declaration=obj.id):
            return forms.count()
        else:
            return "-"
    
    def get_submitted_forms(self, obj):
        # context = []
        if submitted_forms := DeclarationForms.objects.filter(declaration = obj.id):
            return submitted_forms.order_by('parentform_type').distinct('parentform_type').values("id", "parentform_type")
        else:
            return "-"
        #     for form in submitted_forms:
        #         context.append({'id': form.id, 'parentform_type' : form.parentform_type_id, 'subform_type' : form.subform_type_id})
        #     return {
        #         "form_types": context,
        #     } 
        # else:
        #     return "-"

    def get_attachments_count(self, obj):
        if attachments_count := Attachments.objects.filter(declaration_form__declaration=obj.id):
            return attachments_count.count()
        else:
            return "-"
        
    def get_files_count(self, obj):
        if files_count := Attachments.objects.filter(investment_declaration=obj.id):
            return files_count.count()
        else:
            return "-"
    


class InvestmentDeclarationStatusChangeSerializer(serializers.ModelSerializer):
    """
    UDAY, 06.06.2023
    """

    class Meta:
        model = InvestmentDeclaration
        fields = (
            "id",
            "status",
        )


class InvestmentDeclarationEnteriesUpdateSerializer(serializers.ModelSerializer):
    """
    UDAY, 06.06.2023
    """

    class Meta:
        model = InvestmentDeclaration
        fields = "__all__"



# class DeclarationFormsSerializer(serializers.ModelSerializer):
#     """
#     Serializer for Declaration form
#     """

#     id = serializers.IntegerField(required=False)

#     class Meta:
#         model = DeclarationForms
#         list_serializer_class = QuerysetFilterSerializer
#         fields = (
#             "id",
#             "form_type",
#             "declaration",
#             "declared_amount",
#             "comments",
#             "is_deleted",
#         )
#         validators = []  # * To handle unique_together validation
#         extra_kwargs = {
#             "declaration": {"required": False},
#             "form_type": {"source": "declaration_type"},
#         }


# class InvestmentDeclarationSerializer(
#     FlexFieldsSerializerMixin, serializers.ModelSerializer
# ):
#     """
#     SURESH, 09.05.2023
#     """

#     employee_data = serializers.SerializerMethodField()
#     status = serializers.ChoiceField(choices=InvestmentDeclaration.STATUS_CHOICES)
#     status_display = serializers.ChoiceField(
#         choices=InvestmentDeclaration.STATUS_CHOICES,
#         source="get_status_display",
#         required=False,
#     )
#     regime_type_display = serializers.ChoiceField(
#         choices=InvestmentDeclaration.REGIME_CHOICES,
#         source="get_regime_type_display",
#         required=False,
#     )
#     declaration_forms = DeclarationFormsSerializer(many=True, required=False)

#     class Meta:
#         model = InvestmentDeclaration
#         fields = (
#             "id",
#             "employee",
#             "employee_data",
#             "regime_type",
#             "regime_type_display",
#             "declaration_amount",
#             "income_from_previous_employer",
#             "approved_amount",
#             "final_declared_amount",
#             "final_approved_amount",
#             "savings_after_ctc",
#             "no_of_attachments",
#             "comments",
#             "status",
#             "status_display",
#             "start_year",
#             "end_year",
#             "declaration_forms",
#             "updated_at",
#         )
#         extra_kwargs = {"comments": {"required": False}}

#     def validate(self, attrs):
#         if attrs["end_year"] - attrs["start_year"] != 1:
#             raise serializers.ValidationError("Enter declaraton for One (1) Year only")

#         return super().validate(attrs)

#     def create(self, validated_data):
#         forms = validated_data.pop("declaration_forms", [])
#         no_of_forms = 0
#         form_objs = []
#         tot_declared_amount = D(0.00)

#         declaration = InvestmentDeclaration(**validated_data)

#         for counter, form in enumerate(forms, 1):
#             no_of_forms = counter
#             tot_declared_amount += D(form.get("declared_amount", 0))
#             form_objs.append(
#                 DeclarationForms(
#                     declaration_type=form["declaration_type"],
#                     declared_amount=form.get("declared_amount", 0),
#                     comments=form.get("comments", ""),
#                     declaration=declaration,
#                 )
#             )

#         declaration.no_of_forms = no_of_forms
#         declaration.declaration_amount = tot_declared_amount
#         declaration.save()

#         if form_objs:
#             DeclarationForms.objects.bulk_create(form_objs)

#         return declaration

#     def update(self, instance, validated_data):
#         forms = validated_data.pop("declaration_forms", [])
#         print(validated_data)
#         print(forms)
#         try:
#             for form in forms:
#                 print(form["declaration"])
#                 form["declaration"] = instance
#                 DeclarationForms.objects.update_or_create(
#                     id=form.pop("id", None), defaults=form
#                 )

#         except Exception as e:
#             result = {"status": HTTP_400_BAD_REQUEST, "data": e}
#             raise serializers.ValidationError(result) from e

#         return super().update(instance, validated_data)

#     def get_employee_data(self, obj):
#         employee = obj.employee
#         department = employee.work_details.department
#         return {
#             "id": employee.id,
#             "name": employee.name,
#             "emp_id": employee.work_details.employee_number,
#             "department": department.name if department else " ",
#             "organization": employee.company.company_name,
#         }

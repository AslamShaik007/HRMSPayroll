import logging

from django.db import transaction

from rest_framework import serializers

from company_profile.models import (
    Announcements,
    AuditorDetails,
    AuditorTypes,
    BankAccountTypes,
    BankDetails,
    CompanyDetails,
    CompanyDirectorDetails,
    CompanyGrades,
    CustomAddressDetails,
    Departments,
    Designations,
    EntityTypes,
    Policies,
    SecretaryDetails,
    StatutoryDetails,
    SubDepartments,
)
from core.serializers import QuerysetFilterSerializer
from directory.models import Employee
from django.db import models as db_models

logger = logging.getLogger(__name__)


class CompanySerializer(serializers.ModelSerializer):
    """
    Comapny Details Serializer

    SURESH, 04.01.2023
    """

    class Meta:
        model = CompanyDetails
        fields = (
            "id",
            "company_name",
            "brand_name",
            "company_image",
            "web_site",
            "domain_name",
            "industry_type",
            "linked_in_page",
            "facebook_page",
            "twitter_page",
            "registered_adress_line1",
            "registered_adress_line2",
            "registered_country",
            "registered_state",
            "registered_city",
            "registered_pincode",
            "corporate_adress_line1",
            "corporate_adress_line2",
            "corporate_country",
            "corporate_state",
            "corporate_city",
            "corporate_pincode",
            "is_deleted",
            "payslip_watermark",
            "watermark_status",
            "is_brand_name_updated",
            "payslip_signature",
            "signature_status",
            "decimals",
            "round_offs",
            "payslip_hr_email",
            "payslip_hr_phone"
        )


class CompanyDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyDetails
        fields = (
            "id",
            "company_name",
            "brand_name",
            "company_image",
            "web_site",
            "domain_name",
            "industry_type",
            "linked_in_page",
            "facebook_page",
            "twitter_page",
            "registered_adress_line1",
            "registered_adress_line2",
            "registered_country",
            "registered_state",
            "registered_city",
            "registered_pincode",
            "corporate_adress_line1",
            "corporate_adress_line2",
            "corporate_country",
            "corporate_state",
            "corporate_city",
            "corporate_pincode",
            "is_deleted",
            "payslip_watermark",
            "watermark_status",
            "is_brand_name_updated",
            "payslip_signature",
            "signature_status",
            "decimals",
            "round_offs",
            "payslip_hr_email",
            "payslip_hr_phone"
        )


class CompanySubDepartmentSerializer(serializers.ModelSerializer):
    """
    Sub Department Serializer

    AJAY, 03.01.2023
    """

    no_of_employees = serializers.SerializerMethodField()
    class Meta:
        model = SubDepartments
        list_serializer_class = QuerysetFilterSerializer
        fields = (
            "id",
            "is_deleted",
            "name",
            "no_of_employees",
        )
        extra_kwargs = {
            "department": {"read_only": True},
            "name": {"validators": []},
            "id": {"required": False, "read_only": False},
        }
    def get_no_of_employees(self, obj):
        return Employee.objects.filter(
            company=obj.department.company, work_details__sub_department=obj
        ).count()


class CompanyDepartmentSerializer(serializers.ModelSerializer):
    sub_departments = CompanySubDepartmentSerializer(many=True, required=False)
    no_of_employees = serializers.SerializerMethodField()

    class Meta:
        model = Departments
        fields = (
            "id",
            "is_deleted",
            "name",
            "company",
            "no_of_employees",
            "sub_departments",
        )

    def get_no_of_employees(self, obj):
        return Employee.objects.filter(
            company=obj.company, work_details__department=obj
        ).count()

    def create_sub_depatment(self, validated_data, instance):
        for data in validated_data:
            data["department"] = instance
            if data.get('is_deleted') == True:
                data["name"] = "check"
                sd = SubDepartments.objects.get(id=data.pop("id", None))
                if sd.work_details_sub_dept.count() == 0:
                    SubDepartments.objects.get(id=sd.id).delete()
                else:
                    raise serializers.ValidationError(
                        {
                            "data": {
                                "error": "SubDepartment Contains Employees"
                            }
                        }
                    )
            else:
                SubDepartments.objects.update_or_create(
                    id=data.pop("id", None), defaults=data
                )

    # @transaction.atomic
    def create(self, validated_data):
        """
        Overwrite create method to cater for nested object save

        AJAY, 03.01.2023
        """
        try:
            sid = transaction.set_autocommit(autocommit=False)
            sub_departments = validated_data.pop("sub_departments", [])
            department = Departments.objects.create(**validated_data)
            self.create_sub_depatment(sub_departments, department)
            transaction.commit()
            return department
        except Exception as e:
            transaction.rollback(sid)
            raise serializers.ValidationError(
                {
                    "data": {
                        "error": "Duplicate Sub Departments Not Allowed, Try Unique Sub Departments"
                    }
                }
            )

    # @transaction.atomic
    def update(self, instance, validated_data):
        """
        Overwrite update method

        AJAY, 03.01.2023
        """
        sid = transaction.set_autocommit(autocommit=False)
        try:
            self.create_sub_depatment(
                validated_data.pop("sub_departments", []), instance
            )
            
            # for sub_department in sub_departments:
            #     sub_department["department"] = instance
            #     SubDepartments.objects.update_or_create(
            #         id=sub_department.pop("id", None), defaults=sub_department
            #     )
            data = super().update(instance, validated_data)
            transaction.commit()
            return data
        except ValueError as e:
            transaction.rollback(sid)
            raise serializers.ValidationError({"data": {"error": e}})
        except Exception as e:
            transaction.rollback(sid)
            error_msg = str(e)
            if "unique constraint" in str(e):
                error_msg = "Sub Department with name already exists"
            if "SubDepartment Contains Employees" in str(e):
                error_msg = "SubDepartment Contains Employees"
            raise serializers.ValidationError(
                {
                    "data": {
                        "error": error_msg
                    }
                }
            )

        # except Exception as e:
        #     logger.error(traceback.print_exc())
        #     raise serializers.ValidationError(
        #         {"status": status.HTTP_400_BAD_REQUEST, "data": e}
        #     ) from e


class CompanyDepartmentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departments
        fields = [
            "id",
            "is_deleted",
            "name",
        ]


class CompanySubDepartmentDetailSerializer(serializers.ModelSerializer):
    """
    Sub Department Detail Serializer

    AJAY, 03.01.2023
    """

    class Meta:
        model = SubDepartments
        fields = [
            "id",
            "is_deleted",
            "name",
        ]


class CustomAddressSerializer(serializers.ModelSerializer):
    """
    Custom Address serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = CustomAddressDetails
        fields = (
            "id",
            "company",
            "address_title",
            "address_line1",
            "address_line2",
            "country",
            "state",
            "city",
            "pincode",
            "is_deleted",
        )


class CustomAddressDetailSerializer(serializers.ModelSerializer):
    """
    Custom Address Detail serializer

    AJAY, 28.12.2022
    """

    class Meta:
        model = CustomAddressDetails
        fields = (
            "id",
            "company",
            "address_title",
            "address_line1",
            "address_line2",
            "country",
            "state",
            "city",
            "pincode",
            "is_deleted",
        )


class CompanyDesignationSerializer(serializers.ModelSerializer):
    """
    Company Designation serializer

    SURESH, 28.12.2022
    """

    no_of_employees = serializers.SerializerMethodField()

    class Meta:
        model = Designations
        fields = (
            "id",
            "company",
            "no_of_employees",
            "name",
            "is_deleted",
        )

    def get_no_of_employees(self, obj):
        return Employee.objects.filter(
            company=obj.company, work_details__designation=obj
        ).count()


class CompanyDesignationDetailSerializer(serializers.ModelSerializer):
    """
    Company Designation serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = Designations
        fields = ("id", "company", "name", "is_deleted")


class CompanyGradesSerializer(serializers.ModelSerializer):
    """
    Company Grades serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = CompanyGrades
        fields = ("id", "company", "grade", "is_deleted")


class CompanyGradesDetailSerializer(serializers.ModelSerializer):
    """
    Company Grades serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = CompanyGrades
        fields = ("id", "company", "grade", "is_deleted")


class CompanyAnnouncementSerializer(serializers.ModelSerializer):
    """
    Company Announcement serializer

    SURESH, 28.12.2022
    """
    status = serializers.CharField(required=False, read_only=True) 
    department = serializers.ListField(required=False)
    def validate(self, data):
        id = self.context.get('obj_id','')
        exclude = db_models.Q()
        if id: exclude = db_models.Q(id=id)
        announcement_type  = data.get('announcement_type','ANNOUNCEMENT')
        announcement_title = Announcements.objects.filter(
                                    announcement_title__iexact=data.get('announcement_title'),
                                    company=data.get('company'),
                                    post_date=data.get('post_date'),
                                    is_deleted=False,
                                    announcement_type=announcement_type
                                ).exclude(exclude)
        if announcement_title.exists():
            raise serializers.ValidationError(
                {
                    "error": f"{announcement_type.lower()} with this name already exists"
                }
            )
        post_date = data.get('post_date')
        expired_date = data.get('expired_date')
        if post_date and expired_date and post_date > expired_date:
            raise serializers.ValidationError(
                {
                    "error": f"{announcement_type.lower()} post date should be less then or equal to expired date"
                }
            )
        return data
    class Meta:
        model = Announcements
        fields = ("id", "announcement_title", "company", "annoucement_image", "post_date", "expired_date", "is_deleted","status",
                "department","visibility","annoucement_description","announcement_type")
class CompanyAnnouncementDetailSerializer(serializers.ModelSerializer):
    """
    Company Announcement serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = Announcements
        fields = ("id", "company", "annoucement", "is_deleted")


class CompanyPoliciesSerializer(serializers.ModelSerializer):
    """
    Company Policies serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = Policies
        fields = (
            "id",
            "company",
            "policy_title",
            "policy_description",
            "file_path",
            "is_deleted",
        )


class CompanyPoliciesDetailSerializer(serializers.ModelSerializer):
    """
    Company Policies serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = Policies
        fields = (
            "id",
            "company",
            "policy_title",
            "policy_description",
            "file_path",
            "is_deleted",
        )


class ComapanyEntitySerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EntityTypes
        fields = ("id", "entity_type", "value")

    def get_value(self, instance):
        return instance.get_entity_type_display()


# class Meta:
#     model = EntityTypes
#     fields = ("id", "entity_type")


class ComapanyEntityDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityTypes
        fields = ("id", "entity_type")


class CompanyStatutorySerializer(serializers.ModelSerializer):
    """
    Company Statutory serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = StatutoryDetails
        fields = (
            "id",
            "company",
            "entity_type",
            "tan_number",
            "date_of_incorp",
            "pan_number",
            "pan_image_path",
            "cin_number",
            "cin_image_path",
            "gst_number",
            "gst_image_path",
            "is_deleted",
            "other_entity_type",
            "tds_circle_code"
        )


class CompanyStatutoryDetailSerializer(serializers.ModelSerializer):
    """
    Company Statutory serializer

    SURESH, 28.12.2022
    """

    entity_type = ComapanyEntitySerializer(read_only=True)

    class Meta:
        model = StatutoryDetails
        fields = (
            "id",
            "company",
            "entity_type",
            "tan_number",
            "date_of_incorp",
            "pan_number",
            "pan_image_path",
            "cin_number",
            "cin_image_path",
            "gst_number",
            "gst_image_path",
            "is_deleted",
            "other_entity_type",
            "tds_circle_code"
        )


class CompanyDirectorSerializer(serializers.ModelSerializer):
    """
    Company Director serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = CompanyDirectorDetails
        fields = (
            "id",
            "company",
            "director_name",
            "director_mail_id",
            "din_number",
            "director_phone",
            "is_deleted",
        )


class CompanyDirectorDetailSerializer(serializers.ModelSerializer):
    """
    Company Director serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = CompanyDirectorDetails
        fields = (
            "id",
            "company",
            "director_name",
            "director_mail_id",
            "din_number",
            "director_phone",
            "is_deleted",
        )


class CompanyAuditortypeSerializer(serializers.ModelSerializer):
    """
    Company Auditor type serializer

    SURESH, 06.1.2023
    """

    value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AuditorTypes
        fields = ("id", "auditor_type", "value")

    def get_value(self, instance):
        return instance.get_auditor_type_display()

    # class Meta:
    #     model = AuditorTypes
    #     fields = ("id", "auditor_type")


class CompanyAuditortypeDetailSerializer(serializers.ModelSerializer):
    """
    Company Auditor type serializer

    SURESH, 06.1.2023
    """

    class Meta:
        model = AuditorTypes
        fields = ("id", "auditor_type")


class CompanyAuditorSerializer(serializers.ModelSerializer):
    """
    Company Auditor serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = AuditorDetails
        fields = (
            "id",
            "company",
            "auditor_name",
            "auditor_email",
            "auditor_type",
            "auditor_phone",
            "is_deleted",
        )


class CompanyAuditorDetailSerializer(serializers.ModelSerializer):
    """
    Company Auditor serializer

    SURESH, 28.12.2022
    """

    auditor_type = CompanyAuditortypeSerializer(read_only=True)

    class Meta:
        model = AuditorDetails
        fields = (
            "id",
            "company",
            "auditor_name",
            "auditor_email",
            "auditor_type",
            "auditor_phone",
            "is_deleted",
        )


class CompanySecretarySerializer(serializers.ModelSerializer):
    """
    Company Secretary serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = SecretaryDetails
        fields = (
            "id",
            "company",
            "secretary_name",
            "secretary_email",
            "secretary_phone",
            "is_deleted",
        )


class CompanySecretaryDetailSerializer(serializers.ModelSerializer):
    """
    Company Secretary serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = SecretaryDetails
        fields = (
            "id",
            "company",
            "secretary_name",
            "secretary_email",
            "secretary_phone",
            "is_deleted",
        )


class BankAccountTypesSerializer(serializers.ModelSerializer):
    """
    Company Auditor type serializer

    SURESH, 06.1.2023
    """

    value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = BankAccountTypes
        fields = ("id", "account_type", "value")

    def get_value(self, instance):
        return instance.get_account_type_display()

    # class Meta:
    #     model = BankAccountTypes
    #     fields = ("id", "account_type")


class BankAccountTypesDetailSerializer(serializers.ModelSerializer):
    """
    Company Auditor type serializer

    SURESH, 06.1.2023
    """

    class Meta:
        model = BankAccountTypes
        fields = ("id", "account_type")


class CompanyBankSerializer(serializers.ModelSerializer):
    """
    Company Secretary serializer

    SURESH, 28.12.2022
    """

    class Meta:
        model = BankDetails
        fields = (
            "id",
            "company",
            "account_title",
            "bank_name",
            "city",
            "branch_name",
            "ifsc_code",
            "account_type",
            "account_number",
            "bic",
            "is_default",
            "is_deleted",
        )
    
    def create(self, validated_data):
        if BankDetails.objects.filter(account_title=validated_data.get("account_title"), company=validated_data.get("company"), is_deleted=False):
            raise serializers.ValidationError(
                {
                    "error": "Bank Details With Account Title already exists"
                }
            )
        if BankDetails.objects.filter(account_number=validated_data.get("account_number"), company=validated_data.get("company"), is_deleted=False):
            raise serializers.ValidationError(
                    {
                        "error": "Bank Details With Account Number already exists"
                    }
                )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if BankDetails.objects.filter(account_title=validated_data.get("account_title"), company=validated_data.get("company"), is_deleted=False).exclude(
            id=instance.id
        ):
            raise serializers.ValidationError(
                {
                    "error": "Bank Details With Account Title already exists"
                }
            )
        if BankDetails.objects.filter(account_number=validated_data.get("account_number"), company=validated_data.get("company"), is_deleted=False).exclude(
            id=instance.id
        ):
            raise serializers.ValidationError(
                    {
                        "error": "Bank Details With Account Number already exists"
                    }
                )
        return super().update(instance, validated_data)


class CompanyBankDetailSerializer(serializers.ModelSerializer):
    """
    Company Secretary serializer

    SURESH, 28.12.2022
    """

    account_type = BankAccountTypesSerializer(read_only=True)

    class Meta:
        model = BankDetails
        fields = (
            "id",
            "company",
            "account_title",
            "bank_name",
            "city",
            "branch_name",
            "ifsc_code",
            "account_type",
            "account_number",
            "bic",
            "is_default",
            "is_deleted",
        )

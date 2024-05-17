import logging
import datetime
import traceback
from django.core.exceptions import ObjectDoesNotExist
from HRMSApp.utils import Util
from django.db import transaction
from django.utils.text import slugify
from django.db import connections
import pandas as pd
from rest_framework import serializers, status
from django.db import models as db_models
from attendance.models import AssignedAttendanceRules
from company_profile.models import (
    CompanyGrades,
    Departments,
    Designations,
    SubDepartments,
    CompanyPolicyDocuments
)
from company_profile.serializers import companies
from company_profile.serializers.companies import BankAccountTypesDetailSerializer
from core.models import Utils as model_utils
from core.utils import (get_user, timezone_now, sending_mails_to_employee, get_month_weeks, get_terminations_date, 
                        email_render_to_string, update_employee_ats)
from core.whatsapp import WhatsappMessage
from directory.models import (
    CertificationCourseTypes,
    CourseTypes,
    CompanyDetails,
    DocumentsTypes,
    Employee,
    EmployeeAddressDetails,
    EmployeeCertifications,
    EmployeeDocumentationWork,
    EmployeeDocuments,
    EmployeeEducationDetails,
    EmployeeEmergencyContact,
    EmployeeFamilyDetails,
    EmployeeReportingManager,
    EmployeeResignationDetails,
    EmployeeSalaryDetails,
    EmployeeTypes,
    EmployeeWorkDetails,
    ManagerType,
    QualificationTypes,
    RelationshipTypes,
    EmployeeWorkHistoryDetails,
    EmployeeExperienceDetails,
    SessionYear,
    CTCHistory,
    EmployeePreBoardingDetails
)
from HRMSApp.models import User, Roles, Registration
from leave.models import EmployeeLeaveRuleRelation, EmployeeWorkRuleRelation, LeaveRules
from scripts.employee_deactivation import EmployeeDeactivation
from rest_framework import response
from django.db.models import Q, expressions,JSONField, Value
import re
from leave.serializers import EmployeeLeaveRuleRelationSerializer
from pss_calendar.models import Holidays
from investment_declaration.models import InvestmentDeclaration
from payroll.utils import get_financial_year_start_and_end
from payroll.models import EmployeeComplianceNumbers
logger = logging.getLogger('django')
from rest_framework.response import Response
from alerts.utils import check_alert_notification
from onboarding.models import EmployeeOnboardStatus, OnBoardingModule
from HRMSProject.multitenant_setup import MultitenantSetup

from .email_contents import (manager_hr_email_notifications, manager_hr_whatsapp_notifications, 
                             employee_email_about_manager, employee_whatsapp_about_manager,
                             employee_email_welcome, employee_whatsapp_welcome)

# DropDown Serializers
class EmployeeTypeSerializer(serializers.ModelSerializer):
    """
    Summary for EmployeeTypeSerializer

    Args:
        serializers (ModelSerialzer): EmployeeTypeSerializer

    Raises:
        serializers.ValidationError: If in-valid data found

    AJAY, 10.01.2023
    """

    value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EmployeeTypes
        fields = ("id", "employee_type", "value")

    def get_value(self, instance):
        return instance.get_employee_type_display()


class EmployeeTypeDetailSerializer(serializers.ModelSerializer):
    """
    Summary for EmployeeTypeSerializer

    Args:
        serializers (ModelSerialzer): EmployeeTypeSerializer

    Raises:
        serializers.ValidationError: If in-valid data found

    AJAY, 10.01.2023
    """

    value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EmployeeTypes
        fields = ("id", "employee_type", "value")

    def get_value(self, instance):
        return instance.get_employee_type_display()


class ManagerTypeSerializer(serializers.ModelSerializer):
    """
    Summary for ManagerTypeSerializer

    Args:
        serializers (ModelSerialzer): ManagerTypeSerializer

    Raises:
        serializers.ValidationError: If in-valid data found

    SURESH, 13.01.2023
    """

    value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ManagerType
        fields = ("id", "manager_type", "value")

    def get_value(self, instance):
        return instance.get_manager_type_display()


class ManagerTypeDetailSerializer(serializers.ModelSerializer):
    """
    Summary for ManagerTypeSerializer

    Args:
        serializers (ModelSerialzer): ManagerTypeSerializer

    Raises:
        serializers.ValidationError: If in-valid data found

    SURESH, 13.01.2023
    """

    class Meta:
        model = ManagerType
        fields = ("id", "manager_type")


class QualificationTypeSerializer(serializers.ModelSerializer):
    """
    Summary for qualification_typeSerializer

    Args:
        serializers (ModelSerialzer): QualificationTypeSerializer

    Raises:
        serializers.ValidationError: If in-valid data found

    SURESH, 13.01.2023
    """

    value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = QualificationTypes
        fields = ("id", "qualification_type", "value")

    def get_value(self, instance):
        return instance.get_qualification_type_display()


class QualificationTypeDetailSerializer(serializers.ModelSerializer):
    """
    Summary for qualification_typeSerializer

    Args:
        serializers (ModelSerialzer): QualificationTypeSerializer

    Raises:
        serializers.ValidationError: If in-valid data found

    SURESH, 13.01.2023
    """

    class Meta:
        model = QualificationTypes
        fields = ("id", "qualification_type")


class CourseTypeSerializer(serializers.ModelSerializer):
    """
    Summary for CourseTypeSerializer

    Args:
        serializers (ModelSerialzer): CourseTypeSerializer

    Raises:
        serializers.ValidationError: If in-valid data found

    SURESH, 13.01.2023
    """

    value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CourseTypes
        fields = ("id", "course_type", "value")

    def get_value(self, instance):
        return instance.get_course_type_display()


class CourseTypeDetailSerializer(serializers.ModelSerializer):
    """
    Summary for CourseTypeSerializer

    Args:
        serializers (ModelSerialzer): CourseTypeSerializer

    Raises:
        serializers.ValidationError: If in-valid data found

    SURESH, 13.01.2023
    """

    class Meta:
        model = CourseTypes
        fields = ("id", "course_type")


class DocumentsTypeSerializer(serializers.ModelSerializer):
    """
    Summary for DocumentsTypeSerializer

    Args:
        serializers (ModelSerialzer): DocumentsTypeSerializer

    Raises:
        serializers.ValidationError: If in-valid data found

    SURESH, 13.01.2023
    """

    value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DocumentsTypes
        fields = ("id", "document_type", "value")

    def get_value(self, instance):
        return instance.get_document_type_display()


class DocumentsTypeDetailSerializer(serializers.ModelSerializer):
    """
    Summary for DocumentsTypeSerializer

    Args:
        serializers (ModelSerialzer): DocumentsTypeSerializer

    Raises:
        serializers.ValidationError: If in-valid data found

    SURESH, 13.01.2023
    """

    class Meta:
        model = DocumentsTypes
        fields = ("id", "document_type")


class RelationshipTypeSerializer(serializers.ModelSerializer):
    """
    Summary for RelationshipTypeSerializer

    Args:
        serializers (ModelSerialzer): RelationshipTypeSerializer

    Raises:
        serializers.ValidationError: If in-valid data found

    SURESH, 16.01.2023
    """

    value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RelationshipTypes
        fields = ("id", "relationship_type", "value")

    def get_value(self, instance):
        return instance.get_relationship_type_display()


class RelationshipTypeDetailSerializer(serializers.ModelSerializer):
    """
    Summary for RelationshipTypeSerializer

    Args:
        serializers (ModelSerialzer): RelationshipTypeSerializer

    Raises:
        serializers.ValidationError: If in-valid data found

    SURESH, 16.01.2023
    """

    class Meta:
        model = CertificationCourseTypes
        fields = ("id", "course_type")


class CertificationCourseTypeSerializer(serializers.ModelSerializer):
    """
    Summary for Certification Course Type Serializer

    Args:
        serializers (ModelSerialzer): CertificationCourseTypes Serializer

    Raises:
        serializers.ValidationError: If in-valid data found

    SURESH, 17.01.2023
    """

    value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CertificationCourseTypes
        fields = ("id", "course_type", "value")

    def get_value(self, instance):
        return instance.get_course_type_display()


class CertificationCourseTypeDetailSerializer(serializers.ModelSerializer):
    """
    Summary for Certification Course Type Serializer

    Args:
        serializers (ModelSerialzer): CertificationCourseTypes Serializer

    Raises:
        serializers.ValidationError: If in-valid data found

    SURESH, 17.01.2023
    """

    class Meta:
        model = CertificationCourseTypes
        fields = ("id", "relationship_type")


class EmployeeWorkDetailsSerializer(serializers.ModelSerializer):
    """
    Employee Work Details Serializer
    """

    employee_type = serializers.PrimaryKeyRelatedField(
        queryset=EmployeeTypes.objects.all(), required=False
    )
    department = serializers.PrimaryKeyRelatedField(
        queryset=Departments.objects.all(), required=False
    )
    sub_department = serializers.PrimaryKeyRelatedField(
        queryset=SubDepartments.objects.all(), required=False
    )
    designation = serializers.PrimaryKeyRelatedField(
        queryset=Designations.objects.all(), required=False
    )
    employee_grade = serializers.PrimaryKeyRelatedField(
        queryset=CompanyGrades.objects.all(), required=False
    )

    class Meta:
        model = EmployeeWorkDetails
        fields = "__all__"
        extra_kwargs = {
            "employee": {"read_only": True},
            # "reporting_manager": {"read_only": True},
        }


class EmployeeWorkDetailsRetrieveSerializer(serializers.ModelSerializer):
    """
    Employee Work Details Serializer

    AJAY, 10.01.2023
    """

    employee_type = EmployeeTypeDetailSerializer(read_only=True)
    department = companies.CompanyDepartmentDetailSerializer(read_only=True)
    sub_department = companies.CompanySubDepartmentDetailSerializer(read_only=True)
    designation = companies.CompanyDesignationDetailSerializer(read_only=True)
    employee_grade = companies.CompanyGradesDetailSerializer(read_only=True)
    # reporting_manager = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EmployeeWorkDetails
        fields = [
            "id",
            "is_deleted",
            "employee_number",
            "department",
            "sub_department",
            "designation",
            "job_title",
            # "reporting_manager",
            "work_location",
            "employee_grade",
            "employee_type",
            "employee_grade",
            "employee_status",
            "experience_in_years",
            "experience_in_months",
            "probation_period",
        ]
        extra_kwargs = {
            "employee": {"read_only": True},
        }

    # def get_reporting_manager(self, obj):
    #     a = EmployeeReportingManager.objects.filter(
    #         employee=self.employee, manager_type=ManagerType.PRIMARY, is_deleted=False
    #     ).latest()

    #     return {"id": a.employee_manager.id, "name": a.employee_manager.name}


class EmployeeSalaryDetailsSerializer(serializers.ModelSerializer):
    """
    Employee Salary Details Serializer

    """
    # account_type = BankAccountTypesDetailSerializer(read_only=True)

    class Meta:
        model = EmployeeSalaryDetails
        fields = [
            "id",
            "is_deleted",
            "ctc",
            "salary",
            "account_holder_name",
            "account_number",
            "bank_name",
            "branch_name",
            "city",
            "ifsc_code",
            "account_type",
            "fixed_salary",
            "variable_pay",
            "previous_income",
            "previous_tds",
        ]


class EmployeeSalaryDetailsRetrieveSerializer(serializers.ModelSerializer):
    """
    Employee Salary Details Serializer

    AJAY, 10.01.2023
    """

    class Meta:
        model = EmployeeSalaryDetails
        fields = [
            "id",
            "is_deleted",
            "ctc",
            "salary",
            "account_holder_name",
            "account_number",
            "bank_name",
            "branch_name",
            "city",
            "ifsc_code",
            "account_type",
            "fixed_salary",
            "variable_pay"
        ]
        extra_kwargs = {
            "employee": {"read_only": True},
        }


class EmployeeAddressSerializer(serializers.ModelSerializer):
    """
    Employee Address Serializer

    SURESH, 11.01.2023,
    AJAY, 21.02.2023
    """

    class Meta:
        model = EmployeeAddressDetails
        fields = [
            "id",
            "is_deleted",
            "current_address_line1",
            "current_address_line2",
            "current_country",
            "current_state",
            "current_city",
            "current_pincode",
            "current_house_type",
            "current_staying_since",
            "living_in_current_city_since",
            "permanent_address_line1",
            "permanent_address_line2",
            "permanent_country",
            "permanent_state",
            "permanent_city",
            "permanent_pincode",
            "permanent_same_as_current_address",
        ]
        extra_kwargs = {
            "id": {"read_only": False},
        }


class EmployeeAddressDetailSerializer(serializers.ModelSerializer):
    """
    Employee Address Serializer

    SURESH, 11.01.2023
    """

    class Meta:
        model = EmployeeAddressDetails
        fields = "__all__"


class EmployeeResignationSerializer(serializers.ModelSerializer):
    """
    Employee Resignation Serializer

    SURESH, 19.01.2023
    """

    class Meta:
        model = EmployeeResignationDetails
        fields = "__all__"
        extra_kwargs = {
            "employee": {"read_only": True},
        }


class EmployeeResignationDetailSerializer(serializers.ModelSerializer):
    """
    Employee Resignation Serializer

    SURESH, 19.01.2023
    """

    class Meta:
        model = EmployeeResignationDetails
        fields = "__all__"

class EmployeeSerialzer(serializers.ModelSerializer):
    """
    Serializer for the Employee Details Model

    AJAY, 07.01.2023
    """

    work_details = EmployeeWorkDetailsSerializer(write_only=True, required=False)
    salary_details = EmployeeSalaryDetailsSerializer(write_only=True, required=False)
    address_details = EmployeeAddressDetailSerializer(required=False)
    resignation_info = EmployeeResignationDetailSerializer(required=False)
    # READ ONLY
    # address = serializers.SerializerMethodField(read_only=True)
    work_info = serializers.SerializerMethodField(read_only=True)
    salary_info = serializers.SerializerMethodField(read_only=True)
    signed_in = serializers.SerializerMethodField(read_only=True)
    # date_of_birth = serializers.DateField(format="%d-%m-%Y")
    investment_info = serializers.DictField(required=False,allow_null=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "company",
            "first_name",
            "middle_name",
            "last_name",
            "employee_image",
            "official_email",
            "phone",
            "date_of_join",
            "date_of_birth",
            "gender",
            "blood_group",
            "marital_status",
            "anniversary_date",
            "personal_email",
            "alternate_phone",
            "pre_onboarding",
            "linkedin_profile",
            "facebook_profile",
            "twitter_profile",
            "is_rehire",
            "work_details",
            "salary_details",
            "work_info",
            "salary_info",
            "address_details",
            "signed_in",
            "resignation_info",
            "payroll_status",
            "payroll_entity", "work_entity",
            "investment_info",
            "bio",
        ]
        extra_kwargs = {
            "date_of_birth": {"required": False},
            "work_info": {"required": False},
            "payroll_entity": {"required": False},
            "work_entity": {"required": False},
        }

    def get_address(self, obj):
        try:
            return EmployeeAddressDetailSerializer(instance=obj.address_details).data
        except EmployeeAddressDetails.DoesNotExist:
            return None

    def get_work_info(self, obj):
        try:
            return EmployeeWorkDetailsRetrieveSerializer(obj.work_details).data
        except EmployeeWorkDetails.DoesNotExist:
            return None

    def get_salary_info(self, obj):
        try:
            return EmployeeSalaryDetailsRetrieveSerializer(obj.salary_details).data
        except EmployeeSalaryDetails.DoesNotExist:
            return None

    def get_signed_in(self, obj):
        return obj.user.is_authenticated

    def validate(self, attrs):
        if self.partial:
            return super().validate(attrs)
        official_email = attrs.get('official_email','')
        personal_email = attrs.get('personal_email','')
        email = official_email if official_email else personal_email
        if get_user(email=email, phone=attrs["phone"]):
            raise serializers.ValidationError("Employee with this Email/Phone Number already exists")

        return super().validate(attrs)
    
    def check_contact_info(self,phone,email,company_id,id):
        # work_details__employee_status='Active'
        mail_filter = Q()
        if email:
            mail_filter |= Q(official_email__isnull=False,official_email=email)
            mail_filter |= Q(personal_email__isnull=False,personal_email=email)   
        emp_obj = Employee.objects.filter(
                Q(company_id__isnull=False,company_id=company_id,is_deleted=False) &
                (Q(phone=phone) | mail_filter)
            ).exclude(id=id)
        if emp_obj.exists():
            raise serializers.ValidationError({"personal_email":"Employee with this Email/Phone Number already exists"})
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        domain = self.context.get('domain','')
        if instance.employee_image:
            representation['employee_image'] = f"{domain}qxbox{instance.employee_image.url}"
        return representation
        
    @transaction.atomic()
    def create(self, validated_data):
        """
        Customize default create method

        * create Employee
        * create User
        * create Employee Work Details
        * create Employee Salary Details
        * create employee address
        * create employee resignation info

        AJAY, 10.01.2023
        """
        # sid = transaction.set_autocommit(autocommit=False)
        try:
            logged_in_user = self.context.get('logged_in_user','')
            work_details = validated_data.pop("work_details", [])
            salary_details = validated_data.pop("salary_details", [])
            # emergency_details = self.initial_data.pop("emergency_details", [])
            document_details = validated_data.pop("document_details", {})
            # reporting_manager = self.initial_data.pop("reporting_manager", [])
            investment_info = validated_data.pop("investment_info", [])
            emp_grade = document_details.pop("employee_grade", [])
            # attendance_rule = self.initial_data.pop("attendance_rule", [])
            domain = self.context.get('domain','')
            extra_data = self.context.get('extra_data',{})
            pf_details = extra_data.get("pf_details", {})
            aadhaar_card_photo = extra_data.get("aadhaar_card_photo", [])
            aadhaar_card_id = extra_data.get("aadhaar_card_id", '')
            pan_card_photo = extra_data.get("pan_card_photo", [])
            pan_card_id = extra_data.get("pan_card_id", '')
            emergency_details = extra_data.get("emergency_details", [])
            reporting_manager = extra_data.get("reporting_manager", [])
            multitenant_manager_emp_id = extra_data.get("multitenant_manager_emp_id", None)
            multitenant_manager_company_domain = extra_data.get("multitenant_manager_company_domain", None)
            multitenant_manager_company_name = extra_data.get("multitenant_manager_company_name", None)
            is_multitenant = extra_data.get("is_multitenant")
            current_company = extra_data.get("current_company")
            attendance_rule = extra_data.get("attendance_rule", [])
            insurence_doc = extra_data.get("insurence_doc", [])
            request_obj = self.context.get("request_obj",None)
            
            tenant_manager_data =  extra_data.get("manager_data_info",None)
            
            
            # roles = validated_data.get('roles', [])
            if  ('personal_email' and 'phone') in validated_data:
                self.check_contact_info(validated_data.get('phone'), validated_data.get('personal_email'), validated_data.get('company').id, None)
            if 'payroll_status' not in validated_data:
                validated_data['payroll_status'] = False
            company = validated_data.get("company")
            company_size = company.company.first().company_size
            if not company_size == '500+' and int(company_size.split('-')[1]) < company.employees.filter(work_details__employee_status__in=['Active', 'YetToJoin']).count():
                raise serializers.ValidationError(
                    {
                        "error": "Number of Employees Cant be more than the company size"
                    }
                )
            official_email = validated_data.get('official_email','')
            personal_email = validated_data.get('personal_email','')
            email = official_email if official_email else personal_email
            user = User.objects.create_user(
                email=email, phone=validated_data["phone"], username=f'{validated_data.get("first_name")} {validated_data.get("last_name")}'
            )
            if validated_data.get("middle_name"):
                user.username = f'{validated_data.get("first_name")} {validated_data.get("middle_name")} {validated_data.get("last_name")}'
                user.save()    
            if validated_data.get("official_email",'') == validated_data.get("personal_email",'') :
                raise serializers.ValidationError(
                    {
                        "error": "Employee Official Email and Personal Email should not be same"
                    }
                )
            validated_data["user"] = user
            employee = Employee.objects.create(**validated_data)
            employee_role = Roles.objects.filter(name__icontains='employee')
            logger.debug(f"User is created: {user}")
            if employee_role.exists():
                employee.roles.add(employee_role.first().id)
                employee.save()

            if not work_details:
                wd_instance,is_created = EmployeeWorkDetails.objects.get_or_create(
                    employee=employee
                )
                wd_instance.probation_period = 180
                wd_instance.probation_period_left = 180
                wd_instance.save()
            if work_details:
                wd_instance,is_created = EmployeeWorkDetails.objects.get_or_create(
                    employee=employee, **work_details
                )
                if 'probation_period' not in work_details:
                    wd_instance.probation_period = 180
                logger.debug(f"Employee Work Details are created: {wd_instance}")
                wd_instance.probation_period_left = 0
                if probation_period := work_details.get("probation_period", 180):
                    data_of_join = validated_data.get("date_of_join",timezone_now().date())
                    employee_regular = data_of_join + datetime.timedelta(days=probation_period)
                    pb_left = max((employee_regular - timezone_now().date()).days,0)
                    wd_instance.probation_period_left = pb_left
                wd_instance.save()
            
            if investment_info:
                doj=validated_data.get("date_of_join", timezone_now())
                start_year, end_year = get_financial_year_start_and_end(doj)
                investment_obj, created = InvestmentDeclaration.objects.update_or_create(
                    employee = employee,
                    income_from_previous_employer = investment_info["income_from_previous_employer"],
                    tds_from_previous_employer = investment_info["tds_from_previous_employer"],
                    regime_type = investment_info["regime_type"],
                    final_approved_amount = investment_info["final_approved_amount"],
                    start_year = start_year,
                    end_year = end_year
                )
                
            if emp_grade:
                if EmployeeWorkDetails.objects.filter(employee=employee).exists():
                    obj_wd = EmployeeWorkDetails.objects.get(employee=employee)
                    obj_wd.employee_grade = emp_grade
                    obj_wd.save()
                else:
                    EmployeeWorkDetails.objects.get_or_create(employee=employee, employee_grade = emp_grade)
            primary = ManagerType.objects.filter(manager_type=ManagerType.PRIMARY).first()
            if reporting_manager or multitenant_manager_emp_id:
                if is_multitenant:
                    instance = EmployeeReportingManager.objects.create(
                        employee=employee, 
                        # manager_id=reporting_manager, 
                        manager_type=primary,
                        is_multitenant = is_multitenant,
                        multitenant_manager_emp_id = multitenant_manager_emp_id,
                        multitenant_manager_company = multitenant_manager_company_name,
                        multitenant_manager_company_domain = multitenant_manager_company_domain
                    )
                    EmployeeWorkHistoryDetails.objects.create(
                        employee=employee, 
                        multitenant_manager_emp_id = multitenant_manager_emp_id,
                        multitenant_manager_company_domain = multitenant_manager_company_domain,
                        is_multitenant_manager = is_multitenant,
                        # manager_id=reporting_manager, 
                        work_from=timezone_now()
                    )
                    # getting manager details
                    # try:
                    # MultitenantSetup().go_to_old_connection(request_obj)
                    # MultitenantSetup().get_domain_connection(request_obj,multitenant_manager_company_domain)
                    # tenant_manager_data = Employee.objects.filter(
                    #     work_details__employee_number = multitenant_manager_emp_id
                    # ).values(
                    #     "work_details__employee_number", "user__username", "official_email",
                    #     "user__phone", 
                    # )
                    # print("manager data", tenant_manager_data)
                    if tenant_manager_data:
                        manager_information_data = tenant_manager_data[0]
                        manager_employee_number = manager_information_data["work_details__employee_number"]
                        manager_username = manager_information_data["user__username"]
                        manager_official_email = manager_information_data["official_email"]
                        manager_phone = manager_information_data["user__phone"]
                    else:
                        manager_employee_number = ""
                        manager_username = ""
                        manager_official_email = ""
                        manager_phone = ""
                    # connections['default'].close()
                    # MultitenantSetup().get_domain_connection(request_obj, current_company)
                    # except Exception:
                    #     MultitenantSetup().get_domain_connection(current_company)
                else:
                    instance = EmployeeReportingManager.objects.create(
                        employee=employee, 
                        manager_id=reporting_manager, 
                        manager_type=primary,
                        is_multitenant = is_multitenant,
                    )
                    EmployeeWorkHistoryDetails.objects.create(
                        employee=employee, 
                        manager_id = reporting_manager,
                        work_from=timezone_now()
                    )
                    manager_information_data = list(Employee.objects.filter(
                            id = reporting_manager
                    ).values(
                            "work_details__employee_number", "user__username", "official_email",
                            "user__phone", 
                    )
                    )
                    if manager_information_data:
                        manager_information_data = manager_information_data[0]
                        manager_employee_number = manager_information_data["work_details__employee_number"]
                        manager_username = manager_information_data["user__username"]
                        manager_official_email = manager_information_data["official_email"]
                        manager_phone = manager_information_data["user__phone"]
                    else:
                        manager_employee_number = ""
                        manager_username = ""
                        manager_official_email = ""
                        manager_phone = ""
                try:
                    emp_designation = instance.employee.work_details.designation.name if instance.employee.work_details.designation else ''
                    # emp_id =instance.employee.work_details.employee_number if instance.employee.work_details.employee_number else '-'
                    man_emp_id = manager_information_data["work_details__employee_number"]
                    
                    body=f"""
    Hello {manager_username.title()} [{man_emp_id}],

    We would like to inform you that a new employee, {instance.employee.user.username.title()} has been successfully added to your team in the HRMS system, 
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()}
    
    {instance.employee.user.username.title()} will be contributing to {emp_designation} We Trust they will be a valuable addition to your team.
    
    Thank you for your attention, and we appreciate your support in welcoming our new team member.
    
    Thanks & Regards,
    {instance.employee.company.company_name.title()}.
    """
                    data = {
                            'subject': f'New Employee Assignment',
                            'body':body,
                            'to_email': manager_official_email
                        }
                    if check_alert_notification("Employee Management","Add Employee", email=True):
                        Util.send_email(data)
                except Exception as e:
                    pass
                # manager Whatsapp notifications
                try:
                    manager_data = {
                            'phone_number':  manager_phone,
                            'subject': 'New Employee Assignment',
                            "body_text1":f"{instance.employee.user.username.title()} has been successfully added to your team",
                            'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                            'url': f"{domain}directory",
                            "company_name":instance.employee.company.company_name.title()
                            }
                    if check_alert_notification("Employee Management","Add Employee", whatsapp=True):
                        WhatsappMessage.whatsapp_message(manager_data)
                except Exception as e:
                    logger.warning("Error while sending Whatsapp notificaton emp %s in add employee: %s" % (
                        instance.employee.user.username,
                        e
                    ) ) 
                #employee email
                try:
                    body=f"""                                                                                                                                                                   
    Hello {instance.employee.user.username.title()},

    We would like to inform you that a new reporting manager {manager_username.title()}, has been assigned to you in our HRMS system
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},
    
    {manager_username.title()},will be overseeing your role and responsibilities moving forward. If you have any questions or need assistance during this transition, 
    
    please feel free to reach out to {manager_username.title()} directly.

    We appreciate your cooperation and wish you continued success in your role under the guidance of your new reporting manager.

    Thanks & Regards,
    {instance.employee.company.company_name.title()}.
    """
                    data={
                            'subject': f'New Reporting Manager Assignment',
                            'body':body,
                            'to_email': instance.employee.official_email
                        }
                    if check_alert_notification("Employee Management","Add Employee", email=True):
                        Util.send_email(data)
                except Exception as e:
                    pass
                
                try:
                    body=f"""
    Hello {instance.employee.user.username.title()},

    We are pleased to inform you that you have been successfully added to {instance.employee.company.company_name.title()}.
    
    If you have any questions or need assistance during this transition, please feel free to reach out to {manager_username.title()} directly.
    
    Thank you for your attention, and we appreciate your support in welcoming our new team member.

    Thanks & Regards,
    {instance.employee.company.company_name.title()}.
    """
                    data={
                            'subject': f'Welcome To {instance.employee.company.company_name.title()}',
                            'body':body,
                            'to_email': instance.employee.official_email
                        }
                    if check_alert_notification("Employee Management","Add Employee", email=True):
                        Util.send_email(data)
                except Exception as e:
                    pass
                
                #employee Whatsapp notifications about welcome
                try:
                    whatsapp_data = {
                                    'phone_number': instance.employee.user.phone,
                                    'subject': f'Welcome To {instance.employee.company.company_name.title()}',
                                    "body_text1":f"We are pleased to inform you that you have been successfully added to {instance.employee.company.company_name.title()}",
                                    'body_text2': " ",
                                    'url': f"{domain}userprofile",
                                    "company_name":instance.employee.company.company_name.title()
                                    }
                    if check_alert_notification("Employee Management","Add Employee", whatsapp=True):
                        WhatsappMessage.whatsapp_message(whatsapp_data)
                except Exception as e:
                    logger.warning("Error while sending Whatsapp notificaton Emp %s in add employee: %s" % (
                        instance.employee.user.username,
                        e
                    ) ) 
                
                #employee Whatsapp notifications about reporting manager
                try:
                    employee_data = {
                            'phone_number': instance.employee.user.phone,
                            'subject': 'New Reporting Manager Assignment',
                            "body_text1": f"We would like to inform you that a new reporting manager {manager_username.title()} has been assigned to you",
                            'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                            'url': f"{domain}userprofile",
                            "company_name":instance.employee.company.company_name.title()
                            }
                    if check_alert_notification("Employee Management","Add Employee", whatsapp=True):
                        WhatsappMessage.whatsapp_message(employee_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to {instance.employee.user.username} in add employee: {e}") 
                logger.debug(f"Employee reporting manager created: {instance}")
            else:
                user_id = Registration.objects.first().user_id
                emp = Employee.objects.filter(user_id=user_id).first().id
                instance = EmployeeReportingManager.objects.create(
                    employee=employee, manager_id=emp, manager_type=primary
                )
                manager_username = instance.manager.user.username
                EmployeeWorkHistoryDetails.objects.create(employee=employee, manager_id=emp, work_from=timezone_now())
                logger.debug(f"Employee reporting manager created: {instance}")
            
            if salary_details:
                if salary_details.get('ifsc_code','').strip() == "":
                    fund_transfer_type = None
                elif salary_details['ifsc_code'].strip().lower().startswith('icic'):
                    fund_transfer_type = "I"
                else:
                    fund_transfer_type = "N"
                instance = EmployeeSalaryDetails.objects.create(
                    employee=employee, fund_transfer_type=fund_transfer_type,**salary_details
                )
            
                logger.debug(f"Employee Salary Info is created: {instance}")
            # Creating employee pf instance 
            if pf_details:
                pf_obj,created = EmployeeComplianceNumbers.objects.get_or_create(employee=employee)
                pf_obj.pf_num = pf_details.get('pf_num','')
                pf_obj.uan_num = pf_details.get('uan_num','')
                pf_obj.esi_num = pf_details.get('esi_num','')
                pf_obj.nominee_name = pf_details.get('nominee_name','')
                pf_obj.nominee_rel = pf_details.get('nominee_rel','')
                pf_obj.nominee_dob = pf_details.get('nominee_dob',None)
                pf_obj.health_insurence = pf_details.get('health_insurence',None)
                pf_obj.insurence_date = pf_details.get('insurence_date',None)
                if insurence_doc:
                    pf_obj.insurence_file=insurence_doc
                pf_obj.save()
            else:
                obj,is_created = EmployeeComplianceNumbers.objects.get_or_create(employee=employee)

            if emergency_details:
                instance = EmployeeEmergencyContact.objects.create(
                    employee=employee, **emergency_details
                )
                logger.debug(f"Employee emergency contact created: {instance}")

            if aadhaar_card_photo or aadhaar_card_id:
                document_type = DocumentsTypes.objects.filter(document_type=DocumentsTypes.AADHAAR_CARD).first()
                doc_instance, is_created = EmployeeDocuments.objects.get_or_create(employee=employee, document_type=document_type)
                doc_instance.select_file=aadhaar_card_photo
                doc_instance.document_number=aadhaar_card_id
                doc_instance.document_submission_date=timezone_now().date()
                doc_instance.save()
                logger.debug(f"Employee Aadhaar Document details created: {doc_instance}")

            if pan_card_photo or pan_card_id:
                document_type = DocumentsTypes.objects.filter(document_type=DocumentsTypes.PAN_CARD).first()
                instance, is_created = EmployeeDocuments.objects.get_or_create(employee=employee, document_type=document_type)
                instance.select_file=pan_card_photo
                instance.document_number=pan_card_id
                instance.document_submission_date=timezone_now().date()
                instance.document_number=pan_card_id
                instance.save()
                logger.debug(f"Employee Pan Document details created: {instance}")

            if document_details:
                instance = EmployeeDocuments.objects.create(
                    employee=employee, **emergency_details
                )
                logger.debug(f"Employee emergency contact created: {instance}")
            company = employee.company
            # getting a new employee_number
            
            db_name = connections.databases['default']['NAME'].upper()
            cmp = ''
            num=0
            if 'PSS' in db_name:
                cmp = 'PSS'
                num = 1309
            elif 'VITELGLOBAL' in db_name:
                cmp = 'VG'  
                num = 2028 
            elif 'VARUNDIGITAL' in db_name:
                cmp = 'VDM'  
                num = 3000 
            elif 'VGTS' in db_name:
                cmp = 'VGT'  
                num = 4091 
            emp_number = ''
            if cmp:
                while EmployeeWorkDetails.objects.filter(employee_number__icontains=f"{cmp}-{num}").exists():
                    num+=1
                    emp_number = f"{cmp}-{num}"
                         
            if emp_number and official_email:
                if not EmployeeWorkDetails.objects.filter(employee=employee).exists():
                    EmployeeWorkDetails.objects.create(
                        employee=employee,
                        # employee_number=f"{slugify(company.brand_name).upper()}-{int(EmployeeWorkDetails.objects.filter(employee__company=company).order_by('-id').first().employee_number.split('-')[1]) + 1}"
                        employee_number = emp_number
                    )
                else:
                    wd = EmployeeWorkDetails.objects.get(employee=employee)
                    # wd.employee_number = f"{slugify(company.brand_name).upper()}-{int(EmployeeWorkDetails.objects.filter(employee__company=company).order_by('-id').first().employee_number.split('-')[1]) + 1}"
                    wd.employee_number = emp_number
                    wd.save()
            else:
                new_num = int(EmployeeWorkDetails.objects.filter(employee_number__icontains=company.brand_name, employee__company=company).order_by('employee_number').first().employee_number.split('-')[1]) + 1
                new_emp_code = f"{slugify(company.brand_name).upper()}-{new_num}"
                while EmployeeWorkDetails.objects.filter(employee_number__icontains=new_emp_code).exists():
                    new_num+=1
                    new_emp_code = f"{slugify(company.brand_name).upper()}-{new_num}"
                new_emp_code = new_emp_code if official_email else ''
                if not EmployeeWorkDetails.objects.filter(employee=employee).exists():
                    EmployeeWorkDetails.objects.create(
                    employee=employee,
                    # employee_number=f"{slugify(company.brand_name).upper()}-{int(EmployeeWorkDetails.objects.filter(employee__company=company).order_by('-id').first().employee_number.split('-')[1]) + 1}"
                    employee_number = new_emp_code
                    )
                else:
                    wd = EmployeeWorkDetails.objects.get(employee=employee)
                    # wd.employee_number = f"{slugify(company.brand_name).upper()}-{int(EmployeeWorkDetails.objects.filter(employee__company=company).order_by('-id').first().employee_number.split('-')[1]) + 1}"
                    wd.employee_number = new_emp_code
                    wd.save()
            try:
                leave_rules = LeaveRules.objects.filter(company_id=company.id, is_deleted=False, allowed_under_probation=True, valid_from__lte=timezone_now().date(), valid_to__gte=timezone_now().date()).values_list('id',flat=True)
                if leave_rules.exists():
                    leave_ser = EmployeeLeaveRuleRelationSerializer(data = {'employee': [employee.id], 'rules': leave_rules, 'effective_date': timezone_now().date()})
                    if leave_ser.is_valid(raise_exception=False):
                        leave_ser.save()
            except Exception as e:
                print(e, 15555)
            if work_details and work_details.get('department',''):
                EmployeeWorkHistoryDetails.objects.create(employee=employee,department=work_details.get('department'),work_from=timezone_now())
            if attendance_rule:
                att_data = {"attendance_rule_id":attendance_rule}
                current_session_year, is_created = SessionYear.objects.get_or_create(session_year=timezone_now().year)
                att_data['session_year'] = current_session_year
                att_data['employee'] = employee
                att_data['effective_date'] = timezone_now().date()
                obj, created = AssignedAttendanceRules.objects.get_or_create(**att_data)
                
                hr_email = list(Employee.objects.filter(is_deleted=False,work_details__employee_status='Active',roles__name='HR',
                        company_id=employee.company.id).values_list('official_email',flat=True))
                    
                manager_ins = employee.employee.filter(is_deleted=False, manager_type__manager_type=ManagerType.PRIMARY).first()
                # email to Manager
                try:
                    man_em_id = manager_ins.manager.work_details.employee_number
                    body=f"""
    Hello {manager_ins.manager.user.username.title()} [{man_em_id}],

    I hope this email finds you well. I wanted to inform you about some changes in the working hours/shift timings of {employee.user.username.title()} to ensure smooth operations.
    
    Attendacne Rule Name : {obj.attendance_rule.name},
    Attendacne Rule Description : {obj.attendance_rule.description},
    Shift In Time : {obj.attendance_rule.shift_in_time.strftime("%I:%M %p")},
    Shift Out Time : {obj.attendance_rule.shift_out_time.strftime("%I:%M %p")},
    Is Anomaly Tracing Enabled : {obj.attendance_rule.enable_anomaly_tracing},
    Time Zone : {obj.attendance_rule.selected_time_zone},
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},
        
    Please ensure that your team members are aware of these changes and that they can adjust their schedules accordingly.
    
    If you have any questions or need further assistance, please feel free to reach out the HR department.

    Thanks & Regards,
    {employee.company.company_name.title()}.
                """
                    data={
                            'subject': f"Changes in {employee.user.username}'s Working Hours/Shift Timings",
                            'body':body,
                            'to_email': manager_ins.manager.official_email,
                            'cc':hr_email
                        }
                    if check_alert_notification("Employee Management","Add Employee", email=True):
                        Util.send_email(data)
                except Exception as e:
                    pass
                
                #manager Whatsapp notifications about Working Hours/Shift Timings
                try:
                    whatsapp_data = {
                                    'phone_number': manager_ins.manager.user.phone,
                                    'subject': "Changes in Working Hours/Shift Timings",
                                    "body_text1":f"{employee.user.username.title()}'s working hours/shift timings has been changed",
                                    'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                    'url': f"{domain}attendanceRules",
                                    "company_name":instance.employee.company.company_name.title()
                                    }
                    if check_alert_notification("Employee Management","Add Employee", whatsapp=True):
                        WhatsappMessage.whatsapp_message(whatsapp_data)
                except Exception as e:
                    pass
                    # logger.warning(f"Error while sending Whatsapp notificaton to {manager_ins.manager.user.username} in notifications about Working Hours/Shift Timings: {e}") 
                
                # email to Employee
                try:
                    body=f"""
    Hello {employee.user.username.title()},

    I hope this email finds you well. We wanted to inform you about some changes in your working hours’/shift timings to ensure that you can plan your schedule accordingly.
    
    Attendacne Rule Name : {obj.attendance_rule.name},
    Attendacne Rule Description : {obj.attendance_rule.description},
    Shift In Time : {obj.attendance_rule.shift_in_time.strftime("%I:%M %p")},
    Shift Out Time : {obj.attendance_rule.shift_out_time.strftime("%I:%M %p")},
    Is Anomaly Tracing Enabled : {obj.attendance_rule.enable_anomaly_tracing},
    Time Zone : {obj.attendance_rule.selected_time_zone},
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},
    
    Please refer the link for more information {domain}userAttendancelogs

    If you have any concern or changes, please don't hesitate to reach out to your manager or the HR department for clarification.
    
    Thanks & Regards,
    {employee.company.company_name.title()}.
                """
                    data={
                            'subject': 'Changes to Your Working Hours/Shift Timings',
                            'body':body,
                            'to_email': employee.official_email,
                            'cc':hr_email
                        }
                    if check_alert_notification("Employee Management","Add Employee", email=True):
                        Util.send_email(data)
                except Exception as e:
                    pass  
                
                #Employee Whatsapp notifications about Working Hours/Shift Timings
                try:
                    whatsapp_data = {
                                    'phone_number': employee.user.phone,
                                    'subject': "Changes in Working Hours/Shift Timings",
                                    "body_text1":"We wanted to inform you about some changes in your working hours’/shift timings to ensure that you can plan your schedule accordingly",
                                    'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                    'url': f"{domain}userAttendancelogs",
                                    "company_name":instance.employee.company.company_name.title()
                                    }
                    if check_alert_notification("Attendance","Add Employee", whatsapp=True):
                        WhatsappMessage.whatsapp_message(whatsapp_data)
                except Exception as e:
                    pass
                    # logger.warning(f"Error while sending Whatsapp notificaton to {manager_ins.manager.user.username} in notifications about Working Hours/Shift Timings: {e}") 
            # transaction.commit()
        except Exception as e:
            # transaction.rollback(sid)
            raise e
        return employee

    # @transaction.atomic()
    def update(self, instance, validated_data):
        # sid = transaction.set_autocommit(autocommit=False)
        try:
            logged_in_user = self.context.get('logged_in_user','')
            domain = self.context.get('domain','')
            user_id = self.context.get('user_id','')
            investment_info = validated_data.pop("investment_info", [])
            if ('personal_email' and 'phone') in validated_data:
                self.check_contact_info(validated_data.get('phone'),validated_data.get('personal_email'),instance.company.id,instance.id)
            if 'official_email' in validated_data:
                self.check_contact_info(validated_data.get('phone'),validated_data.get('official_email'),instance.company.id,instance.id)
            if 'phone' in validated_data and validated_data.get('phone',''):
                instance.user.phone = validated_data.get('phone')
                instance.user.save()
            if 'official_email' in validated_data and validated_data.get('official_email',''):
                instance.user.email = validated_data.get('official_email')
                instance.user.save()
            work_details = validated_data.pop("work_details", {})
            salary_details = validated_data.pop("salary_details", {})
            address_details = validated_data.pop("address_details", {})
            resignation_info = validated_data.pop("resignation_info", {})
        
            if work_details and 'employee_status' in work_details and instance.user.is_superuser and work_details.get('employee_status') != 'Active':
                raise serializers.ValidationError(
                                {
                                    "data": {
                                        "error": "You are not allowed to modify the Employee Status of a SuperAdmin"
                                    }
                                }
                            )
                
            
            if address_details:
                current_staying_since = address_details.get('current_staying_since',timezone_now().date())
                living_in_current_city_since = address_details.get('living_in_current_city_since',timezone_now().date())
                if current_staying_since < living_in_current_city_since :
                    raise serializers.ValidationError(
                                {
                                    "data": {
                                        "error": "Staying Since should not be lower than the Living in Current City Since"
                                    }
                                }
                            )
            today = timezone_now().date()
            probation_period = work_details.get('probation_period','')
            date_of_join = validated_data.get('date_of_join','')
            if date_of_join and EmployeeExperienceDetails.objects.filter(employee_id=instance.id, to_date__gte=date_of_join, is_deleted=False).exists():
                raise serializers.ValidationError(
                                {
                                    "data": {
                                        "error": "Date of Joining should be more than the Work Experience TO DATE"
                                    }
                                }
                            ) 
            work_details["probation_period_left"] = 0
            if probation_period:
                if not date_of_join:
                    date_of_join = instance.date_of_join 
                employe_regular = date_of_join + datetime.timedelta(days=probation_period)
                if probation_period != 0 and today <= employe_regular:
                    EmployeeLeaveRuleRelation.objects.filter(employee_id=instance.id, leave_rule__allowed_under_probation=False
                                                    ).update(effective_date=employe_regular)
                pb_left = max((employe_regular - today).days, 0)
                work_details["probation_period_left"] = pb_left
            # WORK DETAILS
            wd_id = None
            if ('first_name' or 'last_name') in validated_data :
                user_obj = instance.user                    
                if validated_data.get("middle_name").strip():
                    user_obj.username = f'{validated_data.get("first_name", instance.first_name)} {validated_data.get("middle_name", instance.middle_name)} {validated_data.get("last_name", instance.last_name)}'
                else:
                    user_obj.username = f'{validated_data.get("first_name", instance.first_name)} {validated_data.get("last_name", instance.last_name)}'
                user_obj.save()
                    
            try:
                wd_id = instance.work_details.id
            except ObjectDoesNotExist:
                ...
            if validated_data.get('employee_image'):
                if 'image' not in validated_data['employee_image'].content_type:
                    raise serializers.ValidationError(
                        {
                            'data': 'File Must be image format'
                        }
                    )
                
            today = timezone_now().date()
            if work_details and work_details.get('employee_status') and work_details.get('employee_status') == 'Active':
                k = EmployeeResignationDetails.objects.filter(employee=instance,is_deleted=False)
                if k.exists() and k.first().termination_date and k.first().termination_date<=today:
                    k.update(termination_date = None)
                    if not k.first().resignation_date:
                        k.update(resignation_status = '')
                if k.exists() and k.first().resignation_date:
                    final_resign_day = k.first().resignation_date + datetime.timedelta(days=k.first().notice_period) 
                    if final_resign_day <= today :
                        k.update(resignation_date = None, notice_period = None)
                        if not k.first().termination_date:
                            k.update(resignation_status = '')
                    
            work_details["employee"] = instance
            # EmployeeWorkDetails.objects.update_or_create(id=wd_id, defaults=work_details)
            if wd_id:
                EmployeeWorkDetails.objects.filter(id=wd_id).update(**work_details)
                if 'department' in work_details and 'sub_department' not in work_details:
                    EmployeeWorkDetails.objects.filter(id=wd_id).update(sub_department=None)
            else:
                EmployeeWorkDetails.objects.create(employee=instance,**work_details)
                
            if validated_data.get('official_email') and validated_data.get('personal_email'):
                if validated_data.get('official_email') == validated_data.get('personal_email'):
                    raise serializers.ValidationError(
                                {
                                    "data": {
                                        "error": "Employee Official Email and Personal Email should not be same"
                                    }
                                }
                            )
            reporting_manager_qs = EmployeeReportingManager.objects.filter(manager_id=instance.id,is_deleted=False,manager_type__manager_type=ManagerType.PRIMARY)
            if work_details.get('employee_status') == "Inactive" and reporting_manager_qs.exists():
                try:
                    # Get Primary Manger
                    manager_type = ManagerType.objects.get(manager_type=ManagerType.PRIMARY)
                    #Get First Admin for company
                    first_admin = Employee.objects.get(id=1)
                    # Reporting manager Employee List
                    emp_list = list(reporting_manager_qs.values_list('employee_id',flat=True))
                    EmployeeReportingManager.objects.filter(employee_id__in=emp_list,manager_type__manager_type=ManagerType.PRIMARY, is_deleted=False).delete()
                    # EmployeeReportingManager.objects.filter(employee_id_in=emp_list,manager_typemanager_type_in=[ManagerType.PRIMARY,ManagerType.SECONDARY], is_deleted=False).delete()
                    for emp in emp_list:
                        secondary_mangr_obj = EmployeeReportingManager.objects.filter(employee_id=emp,manager_type__manager_type=ManagerType.SECONDARY,is_deleted=False).first()
                        if secondary_mangr_obj:
                            secondary_mangr_obj.manager_type=manager_type
                            secondary_mangr_obj.save()             
                        else:
                            EmployeeReportingManager.objects.create(employee_id = emp,manager=first_admin,manager_type=manager_type)  
                except Exception as e:
                    pass

            # SALARY
            sd_id = None
            try:
                sd_id = instance.salary_details.id
            except ObjectDoesNotExist:
                ...
            if salary_details:
                if salary_details['ifsc_code'].strip() == "":
                    fund_transfer_type = None
                elif salary_details['ifsc_code'].strip().lower().startswith('icic'):
                    fund_transfer_type = "I"
                else:
                    fund_transfer_type = "N"         
                # obj, is_created = EmployeeSalaryDetails.objects.update_or_create(
                #     id=sd_id, defaults=salary_details
                # )
                if 'fixed_salary' in salary_details and not salary_details.get('fixed_salary'):
                    salary_details['fixed_salary'] = 0.00
                    salary_details['variable_pay'] = 0.00
                if sd_id:
                    existing_salary = EmployeeSalaryDetails.objects.filter(id=sd_id).first().ctc
                    new_ctc = salary_details.get('ctc')
                    if not existing_salary == new_ctc:
                        existing_salary = 0 if existing_salary == None else existing_salary
                        CTCHistory.objects.create(employee_id=instance.id,updated_ctc=existing_salary, updated_at=timezone_now(), updated_by_id=user_id)
                    EmployeeSalaryDetails.objects.filter(id=sd_id).update(**salary_details)
                    obj = EmployeeSalaryDetails.objects.filter(id=sd_id).first()
                    obj.fund_transfer_type = fund_transfer_type
                    obj.save() 
                else:
                    obj = EmployeeSalaryDetails.objects.create(employee=instance,**salary_details)    
                    obj.fund_transfer_type = fund_transfer_type
                    obj.save()   


            # ADDRESS
            ad_id = None
            try:
                ad_id = instance.address_details.id
            except ObjectDoesNotExist:
                ...

            address_details["employee"] = instance
            # EmployeeAddressDetails.objects.update_or_create(
            #     id=ad_id, defaults=address_details
            # )
            if ad_id:
                EmployeeAddressDetails.objects.filter(id=ad_id).update(**address_details)
            else:
                EmployeeAddressDetails.objects.create(**address_details)
            # Resingnation Info
            ri_id = None
            try:
                if resignation_info.get('resignation_date') or resignation_info.get('termination_date'):
                    obj, is_created = EmployeeResignationDetails.objects.get_or_create(
                        employee=instance
                    )
                    if resignation_info.get('resignation_date') and resignation_info.get('exit_interview_date'):
                        last_day = resignation_info.get('resignation_date') + datetime.timedelta(days=resignation_info.get('notice_period',0))
                        if resignation_info.get('exit_interview_date') > last_day:
                            raise serializers.ValidationError(
                                {
                                    "data": {
                                        "error": f"Exit Interview Date must be lesser than or equal to {last_day}"
                                    }
                                }
                            )
                        obj.exit_interview_date = resignation_info.get('exit_interview_date')
                        obj.exit_interview_time = resignation_info.get('exit_interview_time')
                        
                        
                    if resignation_info.get('resignation_date'):
                        obj.resignation_date = resignation_info.get('resignation_date')
                        obj.notice_period = resignation_info.get('notice_period', 0)
                        final_day = resignation_info.get('resignation_date') + datetime.timedelta(days=resignation_info.get('notice_period',0))
                        p = True
                        while p:
                            if Holidays.objects.filter(company_id=instance.company.id,holiday_date=final_day).exists():
                                final_day = final_day - datetime.timedelta(days=1)
                            else:
                                p = False 
                        query = Employee.objects.filter(id=instance.id,
                        employeeworkrulerelation__work_rule__work_rule_choices__week_number=get_month_weeks(
                            final_day)[final_day.day]).annotate(
                                work_week_details =
                                    expressions.Func(
                                        Value('monday'), "employeeworkrulerelation__work_rule__work_rule_choices__monday",
                                        Value('tuesday'), "employeeworkrulerelation__work_rule__work_rule_choices__tuesday",
                                        Value('wednesday'), "employeeworkrulerelation__work_rule__work_rule_choices__wednesday",
                                        Value('thursday'), "employeeworkrulerelation__work_rule__work_rule_choices__thursday",
                                        Value('friday'), "employeeworkrulerelation__work_rule__work_rule_choices__friday",
                                        Value('saturday'), "employeeworkrulerelation__work_rule__work_rule_choices__saturday",
                                        Value('sunday'), "employeeworkrulerelation__work_rule__work_rule_choices__sunday",
                                    function="jsonb_build_object",
                                        output_field=JSONField()
                                    )).values('work_week_details')
                        if not query.exists():
                                raise serializers.ValidationError(
                                    {
                                        "data": {
                                            "error": "Please assign work week"
                                        }
                                    }
                                )
                                
                        wd = query.first()['work_week_details']
                        final_termination_date = get_terminations_date(wd,final_day)    
                        obj.last_working_day = final_termination_date
                    if resignation_info.get('termination_date'):
                        final_day = resignation_info.get('termination_date')
                        p = True
                        while p:
                            if Holidays.objects.filter(company_id=instance.company.id,holiday_date=final_day).exists():
                                final_day = final_day - datetime.timedelta(days=1)
                            else:
                                p = False 
                        query = Employee.objects.filter(id=instance.id,
                                employeeworkrulerelation__work_rule__work_rule_choices__week_number=get_month_weeks(
                                    final_day)[final_day.day]).annotate(
                                        work_week_details =
                                            expressions.Func(
                                                Value('monday'), "employeeworkrulerelation__work_rule__work_rule_choices__monday",
                                                Value('tuesday'), "employeeworkrulerelation__work_rule__work_rule_choices__tuesday",
                                                Value('wednesday'), "employeeworkrulerelation__work_rule__work_rule_choices__wednesday",
                                                Value('thursday'), "employeeworkrulerelation__work_rule__work_rule_choices__thursday",
                                                Value('friday'), "employeeworkrulerelation__work_rule__work_rule_choices__friday",
                                                Value('saturday'), "employeeworkrulerelation__work_rule__work_rule_choices__saturday",
                                                Value('sunday'), "employeeworkrulerelation__work_rule__work_rule_choices__sunday",
                                            function="jsonb_build_object",
                                                output_field=JSONField()
                                            )).values('work_week_details')
                        if not query.exists():
                                raise serializers.ValidationError(
                                    {
                                        "data": {
                                            "error": "Please assign work week"
                                        }
                                    }
                                )
                        wd = query.first()['work_week_details']
                        final_termination_date = get_terminations_date(wd,final_day)    
                        obj.last_working_day = final_termination_date
                        obj.termination_date = resignation_info.get('termination_date')
                    obj.resignation_status = resignation_info.get('resignation_status')
                    obj.reason_of_leaving = resignation_info.get('reason_of_leaving','Resigned')
                    obj.exit_interview_date = resignation_info.get('exit_interview_date',None)
                    obj.exit_interview_time = resignation_info.get('exit_interview_time',None)
                    obj.resignation_date = resignation_info.get('resignation_date',None)
                    obj.notice_period = resignation_info.get('notice_period',0)
                    obj.save()
                    if check_alert_notification("My Profile",'Exit Interview', email=True):
                        sending_mails_to_employee(instance)
                    if obj.reason_of_leaving in ['Absconded','Terminated']:
                        if obj.termination_date == timezone_now().date() or obj.last_working_day == timezone_now().date():
                            EmployeeDeactivation().termination_change(emp_id=instance.id)
                    elif obj.reason_of_leaving == 'Resigned' and (obj.last_working_day + datetime.timedelta(days=1)) == timezone_now().date():
                        EmployeeDeactivation().termination_change(emp_id=instance.id)
                if resignation_info.get('reason_of_leaving','') == 'ReJoined':
                    obj, is_created = EmployeeResignationDetails.objects.get_or_create(
                        employee=instance
                    )
                    obj.resignation_status = resignation_info.get('resignation_status','')
                    obj.reason_of_leaving = resignation_info.get('reason_of_leaving','ReJoined')
                    obj.exit_interview_date = resignation_info.get('exit_interview_date',None)
                    obj.exit_interview_time = resignation_info.get('exit_interview_time',None)
                    obj.resignation_date = resignation_info.get('resignation_date',None)
                    obj.termination_date = resignation_info.get('termination_date',None)
                    obj.last_working_day = resignation_info.get('last_working_day',None)
                    obj.notice_period = resignation_info.get('notice_period',0) 
                    obj.save()
                    p = EmployeeWorkDetails.objects.filter(employee=instance).update(employee_status='Active')
            except ObjectDoesNotExist:
                ...


            # TODO: @suresh implement for  user data

            # transaction.savepoint_commit(sid=sid)
            if work_details and work_details.get('department',''):
                if not EmployeeWorkHistoryDetails.objects.filter(employee=instance,department=work_details.get('department'),work_to__isnull=True).exists():
                    EmployeeWorkHistoryDetails.objects.create(employee=instance,department=work_details.get('department'),work_from=timezone_now())
                EmployeeWorkHistoryDetails.objects.filter(employee=instance,department_id__isnull=False, work_to__isnull=True
                                                                                        ).exclude(department=work_details.get('department')).update(work_to=timezone_now())
            if work_details.get('employee_status') == "Inactive":
                EmployeeWorkHistoryDetails.objects.filter(employee=instance).update(work_to=timezone_now())     

            # if investment_info: #must not update or create in investment obj need to store in salary details
            #     doj=validated_data.get("date_of_join", timezone_now())
            #     start_year, end_year = get_financial_year_start_and_end(doj)
            #     defaults = {'income_from_previous_employer' : investment_info["income_from_previous_employer"],
            #     'tds_from_previous_employer' : investment_info["tds_from_previous_employer"],
            #     'regime_type' : investment_info["regime_type"],
            #     'final_approved_amount' : investment_info["final_approved_amount"]}
            #     investment_obj, created = InvestmentDeclaration.objects.update_or_create(
            #         employee = instance,
            #         start_year = start_year,
            #         end_year = end_year, defaults=defaults
            #     )
            hrms_status = instance.work_details.employee_status
            payroll_status = instance.payroll_status            
            ip_payroll_status = validated_data.get('payroll_status','')
            ip_hrms_status = work_details.get('employee_status','')
            hrms_is_changed = False
            prl_is_changed = False
            payroll_status_mapping = {True: 'Active', False: 'Inactive', None:'Hold'}
            if ip_payroll_status != '' and (ip_payroll_status != payroll_status):
                ip_payroll_status = payroll_status_mapping[ip_payroll_status]
                payroll_status = payroll_status_mapping[payroll_status]
                prl_is_changed = True
            if ip_hrms_status and (ip_hrms_status != hrms_status):
                hrms_is_changed = True
            if prl_is_changed:
                rep_man = EmployeeReportingManager.objects.filter(employee=instance,is_deleted=False,
                                                                    manager_type__manager_type=ManagerType.PRIMARY,
                                                                    manager__work_details__employee_status='Active').first()
                ex_filter = Q()
                if rep_man:
                    ex_filter = Q(id__in=[rep_man.manager.id])
                admin_hr_emails = Employee.objects.filter(roles__name__in = ['ADMIN','HR'],work_details__employee_status='Active', 
                                                            company_id=instance.company_id).exclude(ex_filter).values('official_email','user__username',
                                                                                                                      'work_details__employee_number', 'company__company_name','user__phone')
                subject = f'Employee Payroll Status Update: {instance.user.username} - {ip_payroll_status}'
 
                if rep_man:
                    try:
                        man_emp_number = rep_man.manager.work_details.employee_number
                        body = email_render_to_string(
                                template_name="mails/directory_mails/payroll_hrms_status_updated_template.html", 
                                context={"manager_name":rep_man.manager.name.title(), "manager_emp_code":man_emp_number, "emp_name":instance.user.username.title(),
                                        "old_status":payroll_status, "new_status":ip_payroll_status, "date":timezone_now().strftime("%d-%m-%Y"),
                                        "time":timezone_now().strftime("%I:%M %p"), "updated_by":logged_in_user.title(), "domain":domain,
                                        "company_name":rep_man.employee.company.company_name.title()
                                        
                                            }
                            )
                
                        data={
                            'subject':subject,
                            'body':body,
                            'to_email':rep_man.manager.official_email
                        }
                        if check_alert_notification("Employee Management",'HRMS/Payroll Status Update', email=True):
                            Util.send_email(data, is_content_html=True)
                    except Exception as e:
                        pass
                    
                    #manager Whatsapp notifications about payroll status update
                    try:
                        whatsapp_data = {
                                        'phone_number': rep_man.manager.user.phone,
                                        'subject': 'Employee Payroll Status Update',
                                        "body_text1":f"the status of {instance.user.username.title()} has been updated from {payroll_status} to {ip_payroll_status}",
                                        'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                        'url': f"{domain}directory",
                                        "company_name":rep_man.manager.company.company_name.title()
                                        }
                        if check_alert_notification("Employee Management",'HRMS/Payroll Status Update', whatsapp=True):
                            WhatsappMessage.whatsapp_message(whatsapp_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton Emp {instance.user.username} in notifications about payroll status update: {e}") 
                if admin_hr_emails:
                    for ins in admin_hr_emails:
                        try:
                            body = email_render_to_string(
                                    template_name="mails/directory_mails/payroll_hrms_status_updated_template.html", 
                                    context={"manager_name":ins['user__username'].title(), "manager_emp_code":ins['work_details__employee_number'], "emp_name":instance.user.username.title(),
                                            "old_status":payroll_status, "new_status":ip_payroll_status, "date":timezone_now().strftime("%d-%m-%Y"),
                                            "time":timezone_now().strftime("%I:%M %p"), "updated_by":logged_in_user.title(), "domain":domain,
                                            "company_name":ins['company__company_name'].title()
                                        }
                                )
                        
                            data={
                                'subject':subject,
                                'body':body,
                                'to_email':ins['official_email']
                            }
                            if check_alert_notification("Employee Management",'HRMS/Payroll Status Update', email=True):
                                Util.send_email(data, is_content_html=True)
                        except Exception as e:
                            pass
                            
                        #HR Whatsapp notifications about payroll status update
                        try:
                            whatsapp_data = {
                                            'phone_number': ins['user__phone'],
                                            'subject': 'Employee Payroll Status Update',
                                            "body_text1":f"the status of {instance.user.username.title()} has been updated from {payroll_status} to {ip_payroll_status}",
                                            'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                            'url': f"{domain}directory",
                                            "company_name":ins['company__company_name'].title()
                                            }
                            if check_alert_notification("Employee Management",'HRMS/Payroll Status Update', whatsapp=True):
                                WhatsappMessage.whatsapp_message(whatsapp_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to {ins['user__username']} in notifications about payroll status update: {e}")     
                            
            if hrms_is_changed:
                current_date = timezone_now().date().strftime("%d-%m-%Y %I:%m %p")
                rep_man = EmployeeReportingManager.objects.filter(employee=instance,is_deleted=False,
                                                                    manager_type__manager_type=ManagerType.PRIMARY,
                                                                    manager__work_details__employee_status='Active').first()
                ex_filter = Q()
                if rep_man:
                    ex_filter = Q(id__in=[rep_man.manager.id])
                admin_hr_emails = Employee.objects.filter(roles__name__in = ['ADMIN','HR'],work_details__employee_status='Active', 
                                                            company_id=instance.company_id).exclude(ex_filter).values('official_email','user__username',
                                                                                                                      'work_details__employee_number', 'company__company_name','user__phone')
                subject = f'Employee HRMS Status Update: {instance.user.username} - {ip_hrms_status}'

                if rep_man:
                    try:
                        man_emp_id = rep_man.manager.work_details.employee_number
                        body = email_render_to_string(
                                    template_name="mails/directory_mails/payroll_hrms_status_updated_template.html", 
                                    context={"manager_name":rep_man.manager.name.title(), "manager_emp_code":man_emp_id, "emp_name":instance.user.username.title(),
                                            "old_status":hrms_status, "new_status":ip_hrms_status, "date":timezone_now().strftime("%d-%m-%Y"),
                                            "time":timezone_now().strftime("%I:%M %p"), "updated_by":logged_in_user.title(), "domain":domain,
                                            "company_name":rep_man.employee.company.company_name.title()
                                            
                                                }
                                    )
                    
                        data={
                            'subject':subject,
                            'body':body,
                            'to_email':rep_man.manager.official_email
                        }
                        if check_alert_notification("Employee Management",'HRMS/Payroll Status Update', email=True):
                            Util.send_email(data, is_content_html=True)
                    except Exception as e:
                        pass
                    
                    #manager Whatsapp notifications about HRMS status update
                    try:
                        whatsapp_data = {
                                        'phone_number': rep_man.manager.user.phone,
                                        'subject': 'Employee HRMS Status Update',
                                        "body_text1":f"the status of {instance.user.username.title()} has been updated from {hrms_status} to {ip_hrms_status}",
                                        'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                        'url': f"{domain}directory",
                                        "company_name":rep_man.manager.company.company_name.title()
                                        }
                        if check_alert_notification("Employee Management",'HRMS/Payroll Status Update', whatsapp=True):
                            WhatsappMessage.whatsapp_message(whatsapp_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton Emp {instance.user.username} in notifications about HRMS status update: {e}")     
                    
                if admin_hr_emails:
                    for ins in admin_hr_emails:
                        try:
                            body = email_render_to_string(
                                        template_name="mails/directory_mails/payroll_hrms_status_updated_template.html", 
                                        context={"manager_name":ins['user__username'].title(), "manager_emp_code":ins['work_details__employee_number'], "emp_name":instance.user.username.title(),
                                                "old_status":hrms_status, "new_status":ip_hrms_status, "date":timezone_now().strftime("%d-%m-%Y"),
                                                "time":timezone_now().strftime("%I:%M %p"), "updated_by":logged_in_user.title(), "domain":domain,
                                                "company_name":ins['company__company_name'].title()
                                            }
                                    )
                        
                            data={
                                'subject':subject,
                                'body':body,
                                'to_email':ins['official_email']
                            }
                            if check_alert_notification("Employee Management",'HRMS/Payroll Status Update', email=True):
                                Util.send_email(data, is_content_html=True)
                        except Exception as e:
                            pass
                        
                        #manager Whatsapp notifications about HRMS status update
                        try:
                            whatsapp_data = {
                                            'phone_number': ins['user__phone'],
                                            'subject': 'Employee HRMS Status Update',
                                            "body_text1":f"the status of {instance.user.username.title()} has been updated from {hrms_status} to {ip_hrms_status}",
                                            'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                            'url': f"{domain}directory",
                                            "company_name":ins['company__company_name'].title()
                                            }
                            if check_alert_notification("Employee Management",'HRMS/Payroll Status Update', whatsapp=True):
                                WhatsappMessage.whatsapp_message(whatsapp_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton Emp {instance.user.username} in notifications about HRMS status update: {e}")  
                        
            # sending Mail to Employee if Work location changes
            if work_details and work_details.get('work_location',''):
                existing_location = instance.work_details.work_location
                current_work_location = work_details.get('work_location')
                if existing_location != current_work_location:
                    text_patch = f'changed from {existing_location} to {current_work_location}'
                    if existing_location is None:
                        text_patch = f'updated to {current_work_location}'
                    hr_email = list(Employee.objects.filter(is_deleted=False,work_details__employee_status='Active',roles__name='HR',
                                company_id=instance.company.id).values_list('official_email',flat=True))
                    
                    manager_ins = instance.employee.filter(is_deleted=False, manager_type__manager_type=ManagerType.PRIMARY).first()
                    # email to Manager
                    try:
                        man_em_id = manager_ins.manager.work_details.employee_number
                        body=f"""
    Hello {manager_ins.manager.user.username.title()} [{man_em_id}],

    We would like to inform you that employee {instance.user.username.title()}'s work location is {text_patch}, 
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},
        
    We kindly request your support in ensuring a smooth transition for your team members during this period of change. 
    
    Please reach out to them to provide any necessary guidance or support they may need.
    
    If you have any questions or require further assistance, please don't hesitate to contact the HR department.

    
    Thanks & Regards,
    {instance.company.company_name.title()}.
                """
                        data={
                                'subject': f'Changes in Work Location of {instance.user.username}',
                                'body':body,
                                'to_email': manager_ins.manager.official_email,
                                'cc':hr_email
                            }
                        if check_alert_notification("Employee Management",'Work Location Update', email=True):
                            Util.send_email(data)
                    except Exception as e:
                        pass
                    # email to Employee
                    try:
                        emp_number = instance.work_details.employee_number
                        body=f"""
    Hello {instance.user.username.title()} [{emp_number}],

    We would like to inform you that your work location is {text_patch}.
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},

    Please refer the link for more information {domain}userprofile

    Thanks & Regards,
    {instance.company.company_name.title()}.
                """
                        data={
                                'subject': 'Changes in Your Work Location',
                                'body':body,
                                'to_email': instance.official_email,
                                'cc':hr_email
                            }
                        if check_alert_notification("Employee Management",'Work Location Update', email=True):
                            Util.send_email(data)
                    except Exception as e:
                        pass  
            
            # department update mails
            if work_details and work_details.get('department',''):
                existing_dep = instance.work_details.department.name if instance.work_details.department else None
                current_dep = work_details.get('department').name
                if existing_dep != current_dep:
                    text_patch = f'changed from {existing_dep} to {current_dep}'
                    if existing_dep is None:
                        text_patch = f'updated to {current_dep}'
                    hr_email = list(Employee.objects.filter(is_deleted=False,work_details__employee_status='Active',roles__name='HR',
                                company_id=instance.company.id).values_list('official_email',flat=True))
                    
                    manager_ins = instance.employee.filter(is_deleted=False, manager_type__manager_type=ManagerType.PRIMARY).first()
                    # email to Manager
                    if manager_ins:
                        try:
                            man_em_id = manager_ins.manager.work_details.employee_number
                            body=f"""
        Hello {manager_ins.manager.user.username.title()} [{man_em_id}],

    We would like to inform you that employee {instance.user.username.title()}'s Department is {text_patch}, 
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},
        
    We kindly request your support in ensuring a smooth transition for your team members during this period of change. 
    
    Please reach out to them to provide any necessary guidance or support they may need.
    
    If you have any questions or require further assistance, please don't hesitate to contact the HR department.
    
    Thanks & Regards,
    {instance.company.company_name.title()}.
                """
                            data={
                                    'subject': f'Changes in Department of {instance.user.username}',
                                    'body':body,
                                    'to_email': manager_ins.manager.official_email,
                                    'cc':hr_email
                                }
                            if check_alert_notification("Employee Management",'Department Update', email=True):
                                Util.send_email(data)
                        except Exception as e:
                            pass
                    
                    #manager Whatsapp notifications about Department
                    try:
                        whatsapp_data = {
                                        'phone_number': manager_ins.manager.user.phone,
                                        'subject': f'Changes in Department of {instance.user.username}',
                                        "body_text1":f"{instance.user.username.title()}'s Department is {text_patch}",
                                        'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                        'url': f"{domain}directory",
                                        "company_name":instance.company.company_name.title()
                                        }
                        if check_alert_notification("Employee Management",'Department Update', whatsapp=True):
                            WhatsappMessage.whatsapp_message(whatsapp_data)
                    except Exception as e:
                        # logger.warning(f"Error while sending Whatsapp notificaton to {manager_ins.manager.user.username} in notifications about about Department: {e}")
                        logger.warning(f"Error while sending Whatsapp notificaton to {manager_ins} in notifications about about Department: {e}")
                    
                    # email to Employee
                    try:
                        emp_number = instance.work_details.employee_number
                        body=f"""
    Hello {instance.user.username.title()} [{emp_number}],

    We would like to inform you that your Department is {text_patch}.
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},

    Please refer the link for more information {domain}userprofile

    Thanks & Regards,
    {instance.company.company_name.title()}.
                """
                        data={
                                'subject': 'Changes in Your Department',
                                'body':body,
                                'to_email': instance.official_email,
                                'cc':hr_email
                            }
                        if check_alert_notification("Employee Management",'Department Update', email=True):
                            Util.send_email(data)
                    except Exception as e:
                        pass  
                    
                    #employee Whatsapp notifications about Department
                    try:
                        whatsapp_data = {
                                        'phone_number': instance.user.phone,
                                        'subject': 'Changes in Your Department',
                                        "body_text1":f"We would like to inform you that your Department is {text_patch}",
                                        'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                        'url': f"{domain}userprofile",
                                        "company_name":instance.company.company_name.title()
                                        }
                        if check_alert_notification("Employee Management",'Department Update', whatsapp=True):
                            WhatsappMessage.whatsapp_message(whatsapp_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {instance.user.username} in notifications about about Department: {e}")  
                        
            # designation update mails
            if work_details and work_details.get('designation',''):
                existing_desig = instance.work_details.designation.name if instance.work_details.designation else None
                current_desig = work_details.get('designation').name
                if existing_desig != current_desig:
                    text_patch = f'changed from {existing_desig} to {current_desig}'
                    if existing_desig is None:
                        text_patch = f'updated to {current_desig}'
                    hr_email = list(Employee.objects.filter(is_deleted=False,work_details__employee_status='Active',roles__name='HR',
                                company_id=instance.company.id).values_list('official_email',flat=True))
                    
                    manager_ins = instance.employee.filter(is_deleted=False, manager_type__manager_type=ManagerType.PRIMARY).first()
                    # email to Manager
                    try:
                        man_em_id = manager_ins.manager.work_details.employee_number
                        body=f"""
    Hello {manager_ins.manager.user.username.title()} [{man_em_id}],

    We would like to inform you that a employee {instance.user.username.title()}'s Designation is {text_patch}, 
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},
        
    We kindly request your support in ensuring a smooth transition for your team members during this period of change. 
    
    Please reach out to them to provide any necessary guidance or support they may need.
    
    If you have any questions or require further assistance, please don't hesitate to contact the HR department.
    
    Thanks & Regards,
    {instance.company.company_name.title()}.
                """
                        data={
                                'subject': f'Changes in Designation of {instance.user.username}',
                                'body':body,
                                'to_email': manager_ins.manager.official_email,
                                'cc':hr_email
                            }
                        if check_alert_notification("Employee Management",'Designation Update', email=True):
                            Util.send_email(data)
                    except Exception as e:
                        pass
                    
                    #manager Whatsapp notifications about Designation
                    try:
                        whatsapp_data = {
                                        'phone_number': manager_ins.manager.user.phone,
                                        'subject': f'Changes in Designation of {instance.user.username}',
                                        "body_text1":f"{instance.user.username.title()}'s Designation is {text_patch}",
                                        'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                        'url': f"{domain}directory",
                                        "company_name":manager_ins.manager.company.company_name.title()
                                        }
                        if check_alert_notification("Employee Management",'Designation Update', whatsapp=True):
                            WhatsappMessage.whatsapp_message(whatsapp_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to Manager in notifications about Designation, emp {instance.user.username}: {e}")  
                    
                    # email to Employee
                    try:
                        emp_number = instance.work_details.employee_number
                        body=f"""
    Hello {instance.user.username.title()} [{emp_number}],

    We would like to inform you that your Department is {text_patch}.
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},

    Please refer the link for more information {domain}userprofile

    Thanks & Regards,
    {instance.company.company_name.title()}.
                """
                        data={
                                'subject': 'Changes in Your Designation',
                                'body':body,
                                'to_email': instance.official_email,
                                'cc':hr_email
                            }
                        if check_alert_notification("Employee Management",'Designation Update', email=True):
                            Util.send_email(data)
                    except Exception as e:
                        pass  
                    
                    #employee Whatsapp notifications about Designation
                    try:
                        whatsapp_data = {
                                        'phone_number': instance.user.phone,
                                        'subject': 'Changes in Your Designation',
                                        "body_text1":f"We would like to inform you that your Department is {text_patch}",
                                        'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                        'url': f"{domain}userprofile",
                                        "company_name":instance.company.company_name.title()
                                        }
                        if check_alert_notification("Employee Management",'Designation Update', whatsapp=True):
                            WhatsappMessage.whatsapp_message(whatsapp_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {instance.user.username} in notifications about about Designation: {e}") 
            # transaction.commit()
            data = super().update(instance, validated_data)
            #update employee ATS
            dep_id =work_details.get('department').id if work_details and work_details.get('department','') else instance.work_details.department_id
            desig_id =work_details.get('designation').id if work_details and work_details.get('designation','') else instance.work_details.designation_id
            emp_status = work_details.get('employee_status') if work_details and work_details.get('employee_status','') else instance.work_details.employee_status
            status_id = 4
            if emp_status == 'Active':
                status_id=1
            elif emp_status == 'InActive':
                status_id=2
            elif emp_status == 'YetToJoin':
                status_id=3
                
            payload = {
                'company_id':instance.company.id,
                'emp_code': instance.work_details.employee_number,
                'emp_first_name': validated_data.get('first_name',instance.first_name),
                'emp_middle_name': validated_data.get('middle_name',instance.middle_name),
                'emp_last_name': validated_data.get('middle_name',instance.middle_name),
                'dept_id': dep_id,
                'designation_id': desig_id,
                'pernonal_email': validated_data.get('personal_email',instance.personal_email),
                'office_email': validated_data.get('official_email',instance.official_email),
                'is_active': status_id
            }
            update_employee_ats(payload)
            
        except Exception as e:
            # transaction.rollback(sid)
            raise e
        return data


class EmployeeDetailSerializer(serializers.ModelSerializer):
    """
    `EmployeeDetailSerializer` is a serializer class that serializes the `Employee` model and its

    -- Directory Table Data

    AJAY, 12.01.2023
    """

    number = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    sub_department = serializers.SerializerMethodField()
    designation = serializers.SerializerMethodField()
    # manager = serializers.SerializerMethodField()
    employee_type = serializers.SerializerMethodField()
    employee_status = serializers.SerializerMethodField()
    signed_in = serializers.SerializerMethodField(read_only=True)
    work_location = serializers.SerializerMethodField()
    employee_grade = serializers.SerializerMethodField()
    reporting_manager = serializers.SerializerMethodField()
    attendance_rules = serializers.SerializerMethodField()
    leave_rules = serializers.SerializerMethodField()
    workweek_rule = serializers.SerializerMethodField()
    employee_role = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "name",
            "employee_image",
            "official_email",
            "phone",
            "number",
            "department",
            "sub_department",
            "designation",
            "date_of_birth",
            "date_of_join",
            "gender",
            "first_name",
            "middle_name",
            "last_name",
            "official_email",
            "work_location",
            "phone",
            "blood_group",
            "marital_status",
            "anniversary_date",
            "personal_email",
            "alternate_phone",
            "pre_onboarding",
            "linkedin_profile",
            "facebook_profile",
            "twitter_profile",
            "employee_type",
            "employee_status",
            "employee_grade",
            "reporting_manager",
            "attendance_rules",
            "workweek_rule",
            "leave_rules",
            "signed_in",
            "employee_role",
            "payroll_entity", "work_entity"
        ]

    def get_employee_role(self, obj):
        return role.name if (role := obj.roles.first()) else None

    def _get_value(self, obj, key):
        try:
            return getattr(obj.work_details, key, "-")
        except ObjectDoesNotExist:
            return None

    def get_number(self, obj: Employee) -> str:
        """
        If the object has a work_details attribute, return the employee_number attribute of the
        work_details attribute. Otherwise, return a dash

        :param obj: The object that is being serialized
        :return: The employee number of the employee if the employee has work details, otherwise a dash.

        AJAY, 12.01.2023
        """
        return self._get_value(obj, "employee_number")

    def get_department(self, obj: Employee):
        """
        If the employee has a department, return the department name, otherwise return a dash.

        :param obj: The object that is being serialized
        :type obj: Employee
        :return: A list of all the employees in the database.

        AJAY, 12.01.2023
        """
        department = self._get_value(obj, "department")
        return department.name if department else None

    def get_sub_department(self, obj: Employee):
        """
        If the employee has a sub_department, return the sub_department name, otherwise return a dash.

        :param obj: The object that is being serialized
        :type obj: Employee
        :return: A list of all the employees in the database.

        SURESH, 19.01.2023
        """
        sub_department = self._get_value(obj, "sub_department")
        return sub_department.name if sub_department else None

    def get_designation(self, obj: Employee) -> str:
        """
        It returns the name of the designation of the employee if the designation exists, else it
        returns a dash

        :param obj: Employee
        :type obj: Employee
        :return: The name of the designation of the employee.

        AJAY, 12.01.2023
        """
        designation = self._get_value(obj, "designation")
        return designation.name if designation else None

    def get_employee_type(self, obj: Employee) -> str:
        """
        If the employee has a employee_type, return the employee_type, otherwise return a dash.

        :param obj: The object that is being serialized
        :type obj: Employee
        :return: A list of all the employees in the database.

        SURESH, 19.01.2023
        """
        employee_type = self._get_value(obj, "employee_type")
        return employee_type.get_employee_type_display() if employee_type else None

    def get_employee_status(self, obj: Employee):
        """
        If the employee has a work_location, return the work_location, otherwise return a dash.

        :param obj: The object that is being serialized
        :type obj: Employee
        :return: A list of all the employees in the database.

        SURESH, 19.01.2023
        """
        return self._get_value(obj, "employee_status")

    def get_work_location(self, obj: Employee) -> str:
        """
        It returns the name of the designation of the employee if the designation exists, else it
        returns a dash

        :param obj: Employee
        :type obj: Employee
        :return: The name of the designation of the employee.

        AJAY, 12.01.2023
        """
        work_location = self._get_value(obj, "work_location")
        return work_location or None

    def get_employee_grade(self, obj: Employee) -> str:
        """
        If the employee has a employee_grade, return the employee_type, otherwise return a dash.

        :param obj: The object that is being serialized
        :type obj: Employee
        :return: A list of all the employees in the database.

        SURESH, 19.01.2023
        """
        employee_grade = self._get_value(obj, "employee_grade")
        return employee_grade.grade if employee_grade else None

    def get_reporting_manager(self, obj: EmployeeReportingManager):
        """
        If the employee has a reporting manager, return the manager, otherwise return a dash.

        :param obj: The object that is being serialized
        :type obj: EmployeeReportingManager
        :return: A list of all the employees in the database.

        SURESH, 25.01.2023
        """
        manager_name = ''
        manager_details = EmployeeReportingManager.objects.filter(
            employee=obj.id, is_deleted=False,manager_type__manager_type = 10
        )
        if manager_details.exists():
            manager_name = manager_details.first().manager.name if not manager_details.first().is_multitenant else manager_details.first().multitenant_manager_name
        return manager_name

    def get_attendance_rules(self, obj: AssignedAttendanceRules):
        """
        If the employee has attendance rule, return the rule, otherwise return a dash.

        :param obj: The object that is being serialized
        :type obj: AssignedAttendanceRules
        :return: A list of all the employees in the database.

        SURESH, 12.04.2023, 21.04.2023,
        """
        if attendance_rule := AssignedAttendanceRules.objects.filter(
            employee=obj,
            is_deleted=False,
        ):
            return {
                "name": attendance_rule[0].attendance_rule.name,
                "enable_over_time": attendance_rule[0].attendance_rule.enable_over_time,
                "org_in_time": attendance_rule[0].attendance_rule.shift_in_time,
                "org_out_time": attendance_rule[0].attendance_rule.shift_out_time,
                "auto_clock_out": attendance_rule[0].attendance_rule.auto_clock_out,
            }
        return {
            "name": "-",
            "enable_over_time": "-",
            "org_in_time": "-",
            "org_out_time": "-",
            "auto_clock_out": "-",
        }

    def get_workweek_rule(self, obj: EmployeeWorkRuleRelation):
        """
        If the employee has workweek rule, return the rule, otherwise return a dash.

        :param obj: The object that is being serialized
        :type obj: Employee
        :return: A list of all the employees in the database.

        SURESH, 13.04.2023
        """
        if workweek_rule := EmployeeWorkRuleRelation.objects.filter(
            employee=obj,
            is_deleted=False,
        ):
            return {"name": workweek_rule[0].work_rule.name}
        return {"name": "-"}

    def get_leave_rules(self, obj: EmployeeLeaveRuleRelation):
        """
        If the employee has leave rule, return the rule, otherwise return a dash.

        :param obj: The object that is being serialized
        :type obj: EmployeeLeaveRuleRelation
        :return: A list of all the employees in the database.

        SURESH, 12.04.2023
        """
        context = []
        if leave_rules := EmployeeLeaveRuleRelation.objects.filter(
            employee=obj,
            is_deleted=False,
        ):
            for rule in leave_rules:
                context.append(rule.leave_rule.name)
            return {"name": context}
        return {"name": "-"}

    def get_signed_in(self, obj):
        # Checking if the user is authenticated.
        try:
            return obj.user.is_authenticated
        except Exception:
            return False


class EmployeeImportSerializer(serializers.Serializer):
    employee_file = serializers.FileField(required=False)

    def create(self, validated_data):
        request = self.context["request"]
        file = request.FILES["employee_file"]
        df = pd.read_excel(file, keep_default_na=False, skiprows=1, usecols="A:AC")
        optimized_data = [
            record for record in df.to_dict(orient="record") if any(record.values())
        ]
        errors = []
        serializer = None
        for data in optimized_data:
            try:
                payload = {
                    "company": request.POST["company"],
                    "first_name": data.get(
                        "First Name (Mandatory, if not already in the system)"
                    ),
                    "middle_name": data.get("Middle Name"),
                    "last_name": data.get(
                        "Last Name (Mandatory, if not already in the system)"
                    ),
                    "official_email": data.get(
                        "Official Email ID (Mandatory, if not already in the system or Contact Number is not set)"
                    ),
                    "phone": data.get(
                        "Contact Number (Mandatory, if not already in the system or Official Email ID is not set)"
                    ),
                    "date_of_join": datetime.datetime.strptime(data.get(
                        "Date of Joining(DD/MM/YYYY) (Mandatory, if not already in the system)"
                    ), "%d/%m/%Y").date(),
                    # "date_of_birth": data.get("DOB(DD/MM/YYYY)").date() if not isinstance(
                    #     data.get("DOB(DD/MM/YYYY)", ''), str) else datetime.datetime.strptime(data.get("DOB(DD/MM/YYYY)", ''), "%d/%m/%Y"
                    #     ).date() if data.get("DOB(DD/MM/YYYY)", "") != "" else datetime.datetime.now().date(),
                    # "gender": data.get("Gender","").upper(),
                    "pre_onboarding": False,

                    "document_details": {
                        "AadharCard": data.get("Aadhaar Card"),
                        "pancard": data.get("Pan Card"),
                        "employee_grade": CompanyGrades.objects.filter(grade=data.get("Grade"), 
                                company=request.POST["company"]).first().id if CompanyGrades.objects.filter(grade=data.get("Grade"),
                                                            company=request.POST["company"]).exists() else None
                    },
                    "emergency_details": {
                        "name": data.get("Emergency Contact Name"),
                        "phone_number": data.get("Emergency Contact Number"),
                        "relation": model_utils.get_relation_types(
                            data.get("Relation")
                        ),
                    },
                }
                if data.get("Annual CTC", "") != "": 
                    payload["salary_details"] =  {
                            "ctc": data.get("Annual CTC"),
                            "account_holder_name": data.get(
                                "First Name (Mandatory, if not already in the system)"
                            ),
                            "account_number": data.get("Account Number"),
                            "bank_name": data.get("Bank"),
                            "city": data.get("City"),
                            "branch_name": data.get("Branch"),
                            "ifsc_code": data.get("IFSC"),
                            # "account_type": "1",
                        }
                work_details = {
                    "employee_number": data.get("Employee ID"),
                    "employee_status":data.get("Employee Status") if data.get("Employee Status","") else 'YetToJoin' ,
                    "job_title": data.get("Employee Type"),
                    "work_location": data.get("Work Location"),
                    "probation_period": int(data["Probation Period"])
                    if data.get("Probation Period", None)
                    else 0
                }
                if data.get("Department", None) is not None:
                    try:
                        work_details["department"] = Departments.objects.get(
                            name=data.get("Department")
                        ).id
                    except Exception:
                        ...
                if data.get("Sub Department", None) is not None:
                    try:
                        work_details["sub_department"] = SubDepartments.objects.get(
                            name=data.get("Sub Department")
                        ).id
                    except Exception:
                        ...
                if data.get("Designation", None) is not None:
                    try:
                        work_details["designation"] = Designations.objects.get(
                            name=data.get("Designation")
                        ).id
                    except Exception:
                        ...
                if data.get("Reporting Manager(Emp ID/ Email ID)", None) is not None:
                    try:
                        work_details["reporting_manager"] = (
                            Employee.objects.get(
                                official_email=data.get(
                                    "Reporting Manager(Emp ID/ Email ID)"
                                )
                            ).id
                        )
                    except Exception:
                        ...
                        
                phone_number = str(payload.get('phone',''))
                if phone_number and not re.match(r'^\d{10}$', phone_number):
                    message = "Invalid phone number. It should have exactly 10 digits only"
                    raise serializers.ValidationError(message)
                    
                payload["work_details"] = work_details
                serializer = EmployeeSerialzer(data=payload)
                if serializer.is_valid(raise_exception=True):
                    obj = serializer.save()
                    if payload.get("work_details", {}).get('reporting_manager'):
                        EmployeeReportingManager.objects.get_or_create(
                            employee=obj, manager_id=payload.get("work_details", {}).get('reporting_manager'), 
                            manager_type=ManagerType.objects.get(manager_type=20), is_deleted=False
                        )
            except Exception as e:
                email = data.get("Official Email ID (Mandatory, if not already in the system or Contact Number is not set)")
                phone = data.get("Contact Number (Mandatory, if not already in the system or Official Email ID is not set)")
                if email is None or phone is None:
                    errors.append({"error": "Phone Number or Email cant be None"})
                elif str(email).strip() == "" or str(phone).strip() == "":
                    errors.append({"error": "Phone Number or Email cant be None"})
                else:
                    # errors.append({"error": "Employee with This Email or Phone number Already Exists"})
                    errors.append({"error": str(e).split("[ErrorDetail(string='")[1].split("', code=")[0]})

        if errors:
            raise serializers.ValidationError(errors)
        return serializer


class EmployeeReportingManagerSerializer(serializers.ModelSerializer):
    """
    Employee Reporting Manager Serializer

    SURESH, 17.01.2023
    """

    class Meta:
        model = EmployeeReportingManager
        fields = (
            "id",
            "manager_type",
            "employee",
            "manager",
            "is_deleted",
            "is_multitenant",
            "multitenant_manager_name",
            "multitenant_manager_emp_id",
            "multitenant_manager_company",
            "multitenant_manager_company_domain",
            "multitenant_manager_email"
        )
    
    def create(self, request, *args, **kwargs):
        domain = self.context.get('domain','')
        logged_in_user = self.context.get('logged_in_user','')
        # logged_in_user = self.context.get('request').user.username
        manager_type = request.get('manager_type')
        if not request.get('is_multitenant'):
            EmployeeWorkHistoryDetails.objects.create(
                employee_id=request.get('employee').id,
                manager_id=request.get('manager').id,
                work_from=timezone_now(), manager_type=manager_type)
        created = super().create(request, *args, **kwargs)
        
        instance = EmployeeReportingManager.objects.filter(
            employee_id=request.get('employee').id,
            is_deleted=False, manager_id=request.get('manager').id
        ).first() if not request.get('is_multitenant') else EmployeeReportingManager.objects.filter(            
            employee_id=request.get('employee').id, is_deleted=False,
            multitenant_manager_emp_id=request.get('multitenant_manager_emp_id')
        ).first()
        hr_email = list(Employee.objects.filter(is_deleted=False,work_details__employee_status='Active',roles__name='HR',
                                           company_id=instance.employee.company.id).values_list('official_email',flat=True))
        #Email to Manager
        try:
            emp_designation = instance.employee.work_details.designation.name if instance.employee.work_details.designation else ''
            rm_emp_number = instance.manager.work_details.employee_number if not request.get('is_multitenant') else request.get('multitenant_manager_emp_id')
            rm_username = instance.manager.user.username.title() if not request.get('is_multitenant') else request.get('multitenant_manager_name', '').title()
            body=f"""
    Hello {rm_username} [{rm_emp_number}],

    We would like to inform you that a new employee, {instance.employee.user.username.title()} has been successfully added to your team in the HRMS system, 
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},
    
    {instance.employee.user.username.title()} will be contributing to {emp_designation} We Trust they will be a valuable addition to your team.
    
    Thank you for your attention, and we appreciate your support in welcoming our new team member.
   
    Thanks & Regards,
    {instance.employee.company.company_name.title()}.
    """
            data={
                    'subject': f'New Employee Assignment',
                    'body':body,
                    'to_email': instance.manager.official_email if not request.get('is_multitenant') else request.get('multitenant_manager_email', ''),
                    'cc':hr_email
                }
            if check_alert_notification("My Profile",'Reporting Manager Update', email=True):
                Util.send_email(data)
        except Exception as e:
            pass
        # manager Whatsapp notifications
        try:
            manager_data = {
                            'phone_number': instance.manager.user.phone,
                            'subject': 'New Employee Assignment',
                            "body_text1":f"{instance.employee.user.username.title()} has been successfully added to your team",
                            'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                            'url': f"{domain}directory",
                            "company_name":instance.employee.company.company_name.title()
                            }
            WhatsappMessage.whatsapp_message(manager_data)
        except Exception:
            # logger.warning(f"Error while sending Whatsapp notificaton to {instance.manager.user.username} in assign reporting manager: {e}") 
            pass
        #Email to Employee about reporting manager
        try:
            emp_number = instance.employee.work_details.employee_number
            rm_emp_number = instance.manager.work_details.employee_number if not request.get('is_multitenant') else request.get('multitenant_manager_emp_id')
            rm_username = instance.manager.user.username.title() if not request.get('is_multitenant') else request.get('multitenant_manager_name', '').title()
            body=f"""
    Hello {instance.employee.user.username.title()} [{emp_number}],

    We would like to inform you that a new reporting manager {rm_username}, has been assigned to you in our HRMS system, 
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},
    
    {rm_username},will be overseeing your role and responsibilities moving forward. If you have any questions or need assistance during this transition, 
   
    please feel free to reach out to {rm_username} directly.

    We appreciate your cooperation and wish you continued success in your role under the guidance of your new reporting manager.

    Please refer the link for more information {domain}userdashboard

    Thanks & Regards,,
    {instance.employee.company.company_name.title()}.
    """
            data={
                    'subject': f'New Reporting Manager Assignment',
                    'body':body,
                    'to_email': instance.employee.official_email,
                    'cc':hr_email
                }
            if check_alert_notification("My Profile",'Reporting Manager Update', email=True):
                Util.send_email(data)
        except Exception as e:
            pass
        
        #employee Whatsapp notifications
        try:
            employee_data = {
                    'phone_number': instance.employee.user.phone,
                    'subject': 'New Reporting Manager Assignment',
                    "body_text1": f"We would like to inform you that a new reporting manager {instance.manager.user.username.title()} has been assigned to you",
                    'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                    'url': f"{domain}userprofile",
                    "company_name":instance.employee.company.company_name.title()
                    }
            if check_alert_notification("My Profile",'Reporting Manager Update', whatsapp=True):
                WhatsappMessage.whatsapp_message(employee_data)
        except Exception as e:
            logger.warning(f"Error while sending Whatsapp notificaton to {instance.employee.user.username} in assign reporting manager: {e}") 
        return created
    
    
    
    def update(self, instance, validated_data):
        # company_id = instance.employee.company.id
        # ceo_employee = Employee.objects.filter(company_id = company_id, is_deleted = False,roles__name = 'CEO').first()
        # if validated_data.get('manager_type').manager_type == 10:
        #     EmployeeReportingManager.objects.get_or_create(
        #                             employee_id = validated_data.get('manager').id,
        #                             manager_id = ceo_employee.id,
        #                             manager_type_id = validated_data.get('manager_type').id)
        employee = validated_data.get('employee')
        domain = self.context.get('domain','')
        logged_in_user = self.context.get('logged_in_user','')
        try:
            pre_rep_manager = employee.employee.first().manager
        except:
            pre_rep_manager = None
        is_exist = EmployeeReportingManager.objects.filter(is_deleted=False, manager=validated_data.get('manager'), 
                                                           employee=validated_data.get('employee'), manager_type=validated_data.get('manager_type')).exists()
        final_data = super().update(instance, validated_data)
        hr_email = list(Employee.objects.filter(is_deleted=False,work_details__employee_status='Active',roles__name='HR',
                                           company_id=instance.employee.company.id).values_list('official_email',flat=True))
        print("is_exist:",is_exist)
        if not is_exist:
            try:
                emp_designation = instance.employee.work_details.designation.name if instance.employee.work_details.designation else ''
                man_em_id = instance.manager.work_details.employee_number
                body=f"""
        Hello {instance.manager.user.username.title()} [{man_em_id}],

        We would like to inform you that a new employee, {instance.employee.user.username.title()} has been successfully added to your team in the HRMS system, 
        
        Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},
        
        {instance.employee.user.username.title()} will be contributing to {emp_designation} We Trust they will be a valuable addition to your team.
        
        Thank you for your attention, and we appreciate your support in welcoming our new team member.
        
        Thanks & Regards,
        {instance.employee.company.company_name.title()}.
        """
                data={
                        'subject': f'New Employee Assignment',
                        'body':body,
                        'to_email': instance.manager.official_email,
                        'cc':hr_email
                    }
                if check_alert_notification("My Profile",'Reporting Manager Update', email=True):
                    Util.send_email(data)
            except Exception as e:
                pass
            
            # manager Whatsapp notifications
            try:
                manager_data = {
                            'phone_number': instance.manager.user.phone,
                            'subject': 'New Employee Assignment',
                            "body_text1":f"{instance.employee.user.username.title()} has been successfully added to your team",
                            'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                            'url': f"{domain}directory",
                            "company_name":instance.employee.company.company_name.title()
                            }
                if check_alert_notification("My Profile",'Reporting Manager Update', whatsapp=True):
                    WhatsappMessage.whatsapp_message(manager_data)
            except Exception as e:
                logger.warning(f"Error while sending Whatsapp notificaton Emp {instance.employee.user.username} in assign reporting manager: {e}") 
                
                
            try:
                emp_number = instance.employee.work_details.employee_number
                body=f"""
        Hello {instance.employee.user.username.title()} [{emp_number}],

        We would like to inform you that a new reporting manager {instance.manager.user.username.title()}, has been assigned to you in our HRMS system, 
        
        Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},
        
        {instance.manager.user.username.title()},will be overseeing your role and responsibilities moving forward. If you have any questions or need assistance during this transition, 
    
        please feel free to reach out to {instance.manager.user.username.title()} directly.

        We appreciate your cooperation and wish you continued success in your role under the guidance of your new reporting manager.

        Please refer the link for more information {domain}userdashboard

        Thanks & Regards,
        {instance.employee.company.company_name.title()}.
        """
                data={
                        'subject': 'New Reporting Manager Assignment',
                        'body':body,
                        'to_email': instance.employee.official_email,
                        'cc':hr_email
                    }
                if check_alert_notification("My Profile",'Reporting Manager Update', email=True):
                    Util.send_email(data)
            except Exception as e:
                pass
            
            #employee Whatsapp notifications
            try:
                employee_data = {
                        'phone_number': instance.employee.user.phone,
                        'subject': 'New Reporting Manager Assignment',
                        "body_text1":f"We would like to inform you that a new reporting manager {instance.manager.user.username.title()} has been assigned to you",
                        'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                        'url': f"{domain}userprofile",
                        "company_name":instance.employee.company.company_name.title()
                        }
                if check_alert_notification("My Profile",'Reporting Manager Update', whatsapp=True):
                    WhatsappMessage.whatsapp_message(employee_data)
            except Exception as e:
                logger.warning(f"Error while sending Whatsapp notificaton to {instance.employee.user.username} in add employee: {e}") 
                    
        # all_emps = list(EmployeeReportingManager.objects.filter(
        #     manager_id=ceo_employee,manager_type__manager_type = 10).values_list('employee',flat=True))        
                
        # emp_rep_ceo = {'emps_1':all_emps}
        # new_emp_df = pd.DataFrame(emp_rep_ceo)
        # new_emp_df.emps_1 = new_emp_df.emps_1.apply(lambda emp :'' if EmployeeReportingManager.objects.filter(manager_id = emp).exists() else 
        #                 EmployeeReportingManager.objects.filter(employee_id = emp).delete())
        current_date = timezone_now()
        manager_type = validated_data.get('manager_type').manager_type
        m_type = "Secondary"
        if manager_type == 10:
            m_type = "Primary"
        emp_df = pd.DataFrame({'ids': [validated_data.get('employee').id], 'rep_m': [validated_data.get('manager').id]})
        emp_df.apply(lambda obj: EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],manager_id=obj['rep_m'], work_to__isnull=True, work_from__date=current_date.date()).update(manager_type=m_type) 
                            if EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],manager_id=obj['rep_m'], work_to__isnull=True, work_from__date=current_date.date()).exists()
                            else (EmployeeWorkHistoryDetails.objects.get_or_create(employee_id=obj['ids'], manager_id=obj['rep_m'], work_from=current_date, manager_type=m_type),
                                  EmployeeWorkHistoryDetails.objects.filter(Q(employee_id=obj['ids'],manager_id=obj['rep_m'], work_to__isnull=True), ~Q(manager_type=m_type)).update(work_to=current_date)), axis=1)
        emp_df['manager_ids'] = emp_df.apply(lambda obj:
                            list(EmployeeReportingManager.objects.filter(employee_id=obj['ids'], is_deleted=False).values_list('manager_id',flat=True)), axis=1)                   
        emp_df.apply(lambda obj:
            EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],work_to__isnull=True,department__isnull=True).exclude(manager_id__in =obj['manager_ids']).update(work_to=timezone_now()), axis=1) 
        return final_data


class EmployeeReportingManagerDetailSerializer(serializers.ModelSerializer):
    """
    Employee Reporting Manager Serializer

    SURESH, 17.01.2023
    """

    manager_type = ManagerTypeSerializer(read_only=True)
    manager = EmployeeDetailSerializer(read_only=True)

    class Meta:
        model = EmployeeReportingManager
        fields = (
            "id",
            "manager_type",
            "employee",
            "manager",
            "is_deleted",
        )



class EmployeeEducationSerializer(serializers.ModelSerializer):
    """
    Employee Education Serializer

    SURESH, 16.01.2023
    """
    def validate(self, data):
        course_start_date = data.get('course_start_date')
        course_end_date = data.get('course_end_date')
        if course_end_date < course_start_date:
            raise serializers.ValidationError(
                    {"errors": "Course start date should be less than the end date", "status": status.HTTP_400_BAD_REQUEST}
                )
        return super().validate(data)
    class Meta:
        model = EmployeeEducationDetails
        fields = (
            "id",
            "employee",
            "qualification",
            "course_name",
            "course_type",
            "stream",
            "course_start_date",
            "course_end_date",
            "college_name",
            "university_name",
            "is_deleted",
        )


class EmployeeEducationDetailSerializer(serializers.ModelSerializer):
    """
    Employee Education Serializer

    SURESH, 16.01.2023
    """

    course_type = CourseTypeSerializer(read_only=True)
    qualification = QualificationTypeSerializer(read_only=True)

    class Meta:
        model = EmployeeEducationDetails
        fields = (
            "id",
            "employee",
            "qualification",
            "course_name",
            "course_type",
            "stream",
            "course_start_date",
            "course_end_date",
            "college_name",
            "university_name",
            "is_deleted",
        )


class EmployeeFamilySerializer(serializers.ModelSerializer):
    """
    Employee Family Details Serializer

    SURESH, 16.01.2023
    """

    class Meta:
        model = EmployeeFamilyDetails
        fields = (
            "id",
            "employee",
            "name",
            "relationship",
            "date_of_birth",
            "dependent",
            "is_deleted",
        )


class EmployeeFamilyDetailSerializer(serializers.ModelSerializer):
    """
    Employee Family Details Serializer

    SURESH, 16.01.2023
    """

    relationship = RelationshipTypeSerializer(read_only=True)

    class Meta:
        model = EmployeeFamilyDetails
        fields = (
            "id",
            "employee",
            "name",
            "relationship",
            "date_of_birth",
            "dependent",
            "is_deleted",
        )


class EmployeeEmergencyContactSerializer(serializers.ModelSerializer):
    """
    Employee Employee Emergency Contact Serializer

    SURESH, 16.01.2023
    """

    class Meta:
        model = EmployeeEmergencyContact
        fields = (
            "id",
            "employee",
            "name",
            "relationship",
            "phone_number",
            "is_deleted",
        )


class EmployeeEmergencyContactDetailSerializer(serializers.ModelSerializer):
    """
    Employee Employee Emergency Contact Serializer

    SURESH, 16.01.2023
    """

    relationship = RelationshipTypeSerializer(read_only=True)

    class Meta:
        model = EmployeeEmergencyContact
        fields = (
            "id",
            "employee",
            "name",
            "relationship",
            "phone_number",
            "is_deleted",
        )


class EmployeeDocumentsSerializer(serializers.ModelSerializer):
    """
    Employee Document Serializer

    SURESH, 17.01.2023
    """

    class Meta:
        model = EmployeeDocuments
        fields = (
            "id",
            "employee",
            "document_type",
            "document_number",
            "photo_id",
            "date_of_birth",
            "current_address",
            "parmanent_address",
            "is_verified",
            "select_file",
            "created_by",
            "is_deleted",
            "document_description",
            "document_submission_date",
            "is_uploaded_by_tenant",
            "tenant_domain",
            "tenant_company_id",
            "tenant_user_email"
        )


class EmployeeDocumentsDetailSerializer(serializers.ModelSerializer):
    """
    Employee Document Serializer

    SURESH, 17.01.2023
    """

    document_type = DocumentsTypeSerializer(read_only=True)
    employee = EmployeeDetailSerializer(read_only=True)
    uploaded_by = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDocuments
        fields = (
            "id",
            "employee",
            "document_type",
            "document_number",
            "photo_id",
            "date_of_birth",
            "current_address",
            "parmanent_address",
            "is_verified",
            "select_file",
            "created_by",
            "uploaded_by",
            "is_deleted",
        )
    
    def get_uploaded_by(self, obj):
        if name := Employee.objects.filter(official_email = obj.created_by.email).first():
            return name.name if name else "-"


class EmployeeCertificationsSerializer(serializers.ModelSerializer):
    """
    Employee Certifications Serializer

    SURESH, 17.01.2023
    """

    class Meta:
        model = EmployeeCertifications
        fields = (
            "id",
            "employee",
            "course_type",
            "certification_title",
            "is_verified",
            "select_file",
            "created_by",
            "is_deleted",
        )


class EmployeeCertificationsDetailSerializer(serializers.ModelSerializer):
    """
    Employee Certifications Serializer

    SURESH, 17.01.2023
    """

    course_type = CertificationCourseTypeSerializer(read_only=True)
    employee = EmployeeDetailSerializer(read_only=True)
    uploaded_by = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeCertifications
        fields = (
            "id",
            "employee",
            "course_type",
            "certification_title",
            "is_verified",
            "select_file",
            "created_by",
            "uploaded_by",
            "is_deleted",
        )
    
    def get_uploaded_by(self, obj):
        if name := Employee.objects.filter(official_email = obj.created_by.email).first():
            return name.name if name else "-"


class EmployeeDocumentationWorkSerializer(serializers.ModelSerializer):
    """
    Employee Documentation Work Serializer

    SURESH, 17.01.2023
    """

    class Meta:
        model = EmployeeDocumentationWork
        fields = (
            "id",
            "employee",
            "document_title",
            "document_description",
            "select_file",
            "created_by",
            "is_deleted",
        )


class EmployeeDocumentationWorkDetailSerializer(serializers.ModelSerializer):
    """
    Employee Documentation Work Serializer

    SURESH, 17.01.2023
    """

    employee = EmployeeDetailSerializer(read_only=True)
    uploaded_by = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDocumentationWork
        fields = (
            "id",
            "employee",
            "document_title",
            "document_description",
            "select_file",
            "created_by",
            "uploaded_by",
            "is_deleted",
        )
    
    def get_uploaded_by(self, obj):
        if name := Employee.objects.filter(official_email = obj.created_by.email).first():
            return name.name if name else "-"
        
# By Uday Shankar

class GetEmployeeDetails(serializers.ModelSerializer):
    """
    Employee Details Serializer

    UDAY, 09.06.2023
    """
    
    class Meta:
        model = Employee
        fields = "__all__"
        # fields = (
        #     # "id",
        #     "first_name",
        #     "middle_name",
        #     "last_name",
        #     "phone",
        #     "official_email",
        # )

class PastExperienceDetailserializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeExperienceDetails
        fields = '__all__'
        
    def validate(self, data):
        emp = data.get('employee')
        exp_id = self.context.get('obj_id','')
        exclude = Q()
        if exp_id: exclude = Q(id = exp_id)
        employee = data.get('employee')
        today = employee.date_of_join
        if not today:
            today = timezone_now().date()
        if 'from_date' and 'to_date' in data:
            from_date = data.get('from_date')
            to_date = data.get('to_date')
            
            if from_date > today:
                raise serializers.ValidationError("From Date must be Less than Joining Date")
            if to_date <= from_date:
                raise serializers.ValidationError("To Date must be Greater than from Date")
            if to_date >= today:
                raise serializers.ValidationError("To Date must be Less than Joining Date")
            if EmployeeExperienceDetails.objects.filter(employee=emp, from_date__lte=to_date, to_date__gte=from_date, is_deleted=False).exclude(exclude).exists():
                raise serializers.ValidationError("Experience is already added for the given dates")
        return data

class CompanyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyPolicyDocuments
        fields = '__all__'

    # def validate(self, data):
    #     title = data.get('title') 
    #     policy_type = data.get('policy_type')
    #     if  CompanyPolicyDocuments.objects.filter(
    #             title=title,policy_type = policy_type
    #         ).exists():
    #         raise serializers.ValidationError(
    #             "Title name is already Exists"
    #         )
        
        # return data

class OnboardingEmployeeSerialzer(serializers.ModelSerializer):

    work_details = EmployeeWorkDetailsSerializer(write_only=True, required=False)
    work_info = serializers.SerializerMethodField(read_only=True)
    salary_details = EmployeeSalaryDetailsSerializer(write_only=True, required=False)

    class Meta:
        model = Employee
        fields = [
            "id",
            "company",
            "first_name",
            "middle_name",
            "last_name",
            "employee_image",
            "official_email",
            "phone",
            "date_of_join",
            "date_of_birth",
            "gender",
            "personal_email",
            "is_rehire",
            "work_details",
            "work_info",
            "salary_details"
        ]
        extra_kwargs = {
            "date_of_birth": {"required": False},
            "work_info": {"required": False}
        }

    def get_work_info(self, obj):
        try:
            return EmployeeWorkDetailsRetrieveSerializer(obj.work_details).data
        except EmployeeWorkDetails.DoesNotExist:
            return None

    def get_salary_info(self, obj):
        try:
            return EmployeeSalaryDetailsRetrieveSerializer(obj.salary_details).data
        except EmployeeSalaryDetails.DoesNotExist:
            return None

    def get_signed_in(self, obj):
        return obj.user.is_authenticated

    def validate(self, attrs):
        if self.partial:
            return super().validate(attrs)
        official_email = attrs.get('official_email','')
        personal_email = attrs.get('personal_email','')
        email = official_email if official_email else personal_email
        if get_user(email=email, phone=attrs["phone"]):
            raise serializers.ValidationError("Employee with this Email/Phone Number already exists")

        return super().validate(attrs)
    
    def check_contact_info(self,phone,email,company_id,id):
        # work_details__employee_status='Active'
        mail_filter = Q()
        if email:
            mail_filter |= Q(official_email__isnull=False,official_email=email)
            mail_filter |= Q(personal_email__isnull=False,personal_email=email)   
        emp_obj = Employee.objects.filter(
                Q(company_id__isnull=False,company_id=company_id,is_deleted=False) &
                (Q(phone=phone) | mail_filter)
            ).exclude(id=id)
        if emp_obj.exists():
            raise serializers.ValidationError({"personal_email":"Employee with this Email/Phone Number already exists"})
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        domain = self.context.get('domain','')
        if instance.employee_image:
            representation['employee_image'] = f"{domain}{instance.employee_image.url}"
        return representation
        
    @transaction.atomic()
    def create(self, validated_data):
        """
        Customize default create method

        * create Employee
        * create User
        * create Employee Work Details

        """
        # sid = transaction.set_autocommit(autocommit=False)
        try:
            # import pdb
            # pdb.set_trace()
            logged_in_user = self.context.get('logged_in_user','')
            work_details = validated_data.pop("work_details", [])
            # emergency_details = self.initial_data.pop("emergency_details", [])
            document_details = validated_data.pop("document_details", {})
            # reporting_manager = self.initial_data.pop("reporting_manager", [])
            investment_info = validated_data.pop("investment_info", [])
            emp_grade = document_details.pop("employee_grade", [])
            # attendance_rule = self.initial_data.pop("attendance_rule", [])
            domain = self.context.get('domain','')
            extra_data = self.context.get('extra_data',{})
            pf_details = extra_data.get("pf_details", {})
            emergency_details = extra_data.get("emergency_details", [])
            reporting_manager = extra_data.get("reporting_manager", [])
            attendance_rule = extra_data.get("attendance_rule", [])
            insurence_doc = extra_data.get("insurence_doc", [])
            salary_details = extra_data.get("salary_details", [])
            ctc = self.context.get('ctc',{})
            added_from = self.context.get('added_from',{})
            # roles = validated_data.get('roles', [])
            if  ('personal_email' and 'phone') in validated_data:
                self.check_contact_info(validated_data.get('phone'), validated_data.get('personal_email'), validated_data.get('company').id, None)
            if 'payroll_status' not in validated_data:
                validated_data['payroll_status'] = False
            company = validated_data.get("company")
            company_size = company.company.first().company_size
            if not company_size == '500+' and int(company_size.split('-')[1]) < company.employees.filter(work_details__employee_status__in=['Active', 'YetToJoin']).count():
                raise serializers.ValidationError(
                    {
                        "error": "Number of Employees Cant be more than the company size"
                    }
                )
                
            official_email = validated_data.get('official_email','')
            personal_email = validated_data.get('personal_email','')
            email = official_email if official_email else personal_email
            user = User.objects.create_user(
                email=email, phone=validated_data["phone"], username=f'{validated_data.get("first_name")} {validated_data.get("last_name")}'
            )
            if validated_data.get("middle_name"):
                user.username = f'{validated_data.get("first_name")} {validated_data.get("middle_name")} {validated_data.get("last_name")}'
                user.save()    
            if validated_data.get("official_email",'') == validated_data.get("personal_email",'') :
                raise serializers.ValidationError(
                    {
                        "error": "Employee Official Email and Personal Email should not be same"
                    }
                )
            if 'middle_name' not in validated_data:
                validated_data['middle_name'] = ''
            validated_data["user"] = user
            employee = Employee.objects.create(**validated_data)
            employee_role = Roles.objects.filter(name__icontains='employee')
            logger.debug(f"User is created: {user}")
            if employee_role.exists():
                employee.roles.add(employee_role.first().id)
                employee.save()

            if not work_details:
                wd_instance,is_created = EmployeeWorkDetails.objects.get_or_create(
                    employee=employee
                )
                wd_instance.probation_period = 180
                wd_instance.probation_period_left = 180
                wd_instance.save()
            if work_details:
                wd_instance,is_created = EmployeeWorkDetails.objects.get_or_create(
                    employee=employee, **work_details
                )
                if 'probation_period' not in work_details:
                    wd_instance.probation_period = 180
                logger.debug(f"Employee Work Details are created: {wd_instance}")
                wd_instance.probation_period_left = 0
                if probation_period := work_details.get("probation_period", 180):
                    data_of_join = validated_data.get("date_of_join",timezone_now().date())
                    employee_regular = data_of_join + datetime.timedelta(days=probation_period)
                    pb_left = max((employee_regular - timezone_now().date()).days,0)
                    wd_instance.probation_period_left = pb_left
                wd_instance.save()
            
            if investment_info:
                doj=validated_data.get("date_of_join", timezone_now())
                start_year, end_year = get_financial_year_start_and_end(doj)
                investment_obj, created = InvestmentDeclaration.objects.update_or_create(
                    employee = employee,
                    income_from_previous_employer = investment_info["income_from_previous_employer"],
                    tds_from_previous_employer = investment_info["tds_from_previous_employer"],
                    regime_type = investment_info["regime_type"],
                    final_approved_amount = investment_info["final_approved_amount"],
                    start_year = start_year,
                    end_year = end_year
                )
            if salary_details:
                if salary_details.get('ifsc_code','').strip() == "":
                    fund_transfer_type = None
                elif salary_details['ifsc_code'].strip().lower().startswith('icic'):
                    fund_transfer_type = "I"
                else:
                    fund_transfer_type = "N"
                instance = EmployeeSalaryDetails.objects.create(
                    employee=employee, fund_transfer_type=fund_transfer_type,**salary_details
                )
            
            if ctc:
                instance = EmployeeSalaryDetails.objects.create(
                    employee=employee, fund_transfer_type="N", ctc=ctc
                )
                
            if emp_grade:
                if EmployeeWorkDetails.objects.filter(employee=employee).exists():
                    obj_wd = EmployeeWorkDetails.objects.get(employee=employee)
                    obj_wd.employee_grade = emp_grade
                    obj_wd.save()
                else:
                    EmployeeWorkDetails.objects.get_or_create(employee=employee, employee_grade = emp_grade)
            primary = ManagerType.objects.filter(manager_type=ManagerType.PRIMARY).first()
            if reporting_manager:
                instance = EmployeeReportingManager.objects.create(
                    employee=employee, manager_id=reporting_manager, manager_type=primary
                )
                
                EmployeeWorkHistoryDetails.objects.create(employee=employee, manager_id=reporting_manager, work_from=timezone_now())
                
            else:
                user_id = Registration.objects.first().user_id
                emp = Employee.objects.filter(user_id=user_id).first().id
                instance = EmployeeReportingManager.objects.create(
                    employee=employee, manager_id=emp, manager_type=primary
                )
                EmployeeWorkHistoryDetails.objects.create(employee=employee, manager_id=emp, work_from=timezone_now())
                logger.debug(f"Employee reporting manager created: {instance}")
            
            # Creating employee pf instance 
            if pf_details:
                pf_obj,created = EmployeeComplianceNumbers.objects.get_or_create(employee=employee)
                pf_obj.pf_num = pf_details.get('pf_num','')
                pf_obj.uan_num = pf_details.get('uan_num','')
                pf_obj.esi_num = pf_details.get('esi_num','')
                pf_obj.nominee_name = pf_details.get('nominee_name','')
                pf_obj.nominee_rel = pf_details.get('nominee_rel','')
                pf_obj.nominee_dob = pf_details.get('nominee_dob',None)
                pf_obj.health_insurence = pf_details.get('health_insurence',None)
                pf_obj.insurence_date = pf_details.get('insurence_date',None)
                if insurence_doc:
                    pf_obj.insurence_file=insurence_doc
                pf_obj.save()
            else:
                obj,is_created = EmployeeComplianceNumbers.objects.get_or_create(employee=employee)

            company = employee.company
            
            try:
                leave_rules = LeaveRules.objects.filter(company_id=company.id, is_deleted=False, 
                                                        allowed_under_probation=True, valid_from__lte=timezone_now().date(), 
                                                        valid_to__gte=timezone_now().date()).values_list('id',flat=True)
                if leave_rules.exists():
                    leave_ser = EmployeeLeaveRuleRelationSerializer(data = {'employee': [employee.id], 'rules': leave_rules, 'effective_date': timezone_now().date()})
                    if leave_ser.is_valid(raise_exception=False):
                        leave_ser.save()
            except Exception as e:
                print(e, 15555)
            if work_details and work_details.get('department',''):
                EmployeeWorkHistoryDetails.objects.create(employee=employee,department=work_details.get('department'),work_from=timezone_now())
            if attendance_rule:
                att_data = {"attendance_rule_id":attendance_rule}
                current_session_year, is_created = SessionYear.objects.get_or_create(session_year=timezone_now().year)
                att_data['session_year'] = current_session_year
                att_data['employee'] = employee
                att_data['effective_date'] = timezone_now().date()
                obj, created = AssignedAttendanceRules.objects.get_or_create(**att_data)
            
            # assign employee to Template
            template = OnBoardingModule.objects.filter(company=employee.company)
            if template.exists():
                EmployeeOnboardStatus.objects.get_or_create(employee=employee, onboarding_module=template.first())
            
            #create Onboarding Obj
            preboard, is_created = EmployeePreBoardingDetails.objects.get_or_create(employee=employee)
            preboard.added_from=added_from
            preboard.save()
            # transaction.commit()
        except Exception as e:
            # transaction.rollback(sid)
            raise e
        return employee

    @transaction.atomic()
    def update(self, instance, validated_data):
        # sid = transaction.set_autocommit(autocommit=False)
        try:
            logged_in_user = self.context.get('logged_in_user','')
            domain = self.context.get('domain','')
            user_id = self.context.get('user_id','')
            extra_data = self.context.get('extra_data',{})
            attendance_rule = extra_data.get("attendance_rule", [])
            reporting_manager = extra_data.get("reporting_manager", [])
            onboarding_status = extra_data.get("onboarding_status", [])
            official_email = validated_data.get('official_email','')
            if ('personal_email' and 'phone') in validated_data:
                self.check_contact_info(validated_data.get('phone'),validated_data.get('personal_email'),instance.company.id,instance.id)
            if 'official_email' in validated_data:
                self.check_contact_info(validated_data.get('phone'),validated_data.get('official_email'),instance.company.id,instance.id)
            if 'phone' in validated_data and validated_data.get('phone',''):
                instance.user.phone = validated_data.get('phone')
                instance.user.save()
            work_details = validated_data.pop("work_details", {})
            # getting a new employee_number
            if validated_data.get('official_email','') and not instance.work_details.employee_number:
                db_name = connections.databases['default']['NAME'].upper()
                cmp = ''
                num=0
                if 'PSS' in db_name:
                    cmp = 'PSS'
                    num = 1309
                elif 'VG' in db_name:
                    cmp = 'VG'  
                    num = 2028 
                elif 'VARUNDIGITAL' in db_name:
                    cmp = 'VDM'  
                    num = 3000 
                elif 'VGTS' in db_name:
                    cmp = 'VGT'  
                    num = 4091 
                emp_number = ''
                if cmp:
                    while EmployeeWorkDetails.objects.filter(employee_number__icontains=f"{cmp}-{num}").exists():
                        num+=1
                        emp_number = f"{cmp}-{num}"
                            
                if emp_number and official_email:
                    if not EmployeeWorkDetails.objects.filter(employee=instance).exists():
                        EmployeeWorkDetails.objects.create(
                            employee=instance,
                            # employee_number=f"{slugify(company.brand_name).upper()}-{int(EmployeeWorkDetails.objects.filter(employee__company=company).order_by('-id').first().employee_number.split('-')[1]) + 1}"
                            employee_number = emp_number,
                            employee_status = "Active"
                        )
                    else:
                        wd = EmployeeWorkDetails.objects.get(employee=instance)
                        # wd.employee_number = f"{slugify(company.brand_name).upper()}-{int(EmployeeWorkDetails.objects.filter(employee__company=company).order_by('-id').first().employee_number.split('-')[1]) + 1}"
                        wd.employee_number = emp_number
                        wd.employee_status = "Active"
                        wd.save()
                elif official_email:
                    new_num = int(EmployeeWorkDetails.objects.filter(employee_number__icontains=instance.company.brand_name, employee__company=instance.company).order_by('employee_number').first().employee_number.split('-')[1]) + 1
                    new_emp_code = f"{slugify(instance.company.brand_name).upper()}-{new_num}"
                    while EmployeeWorkDetails.objects.filter(employee_number__icontains=new_emp_code).exists():
                        new_num+=1
                        new_emp_code = f"{slugify(instance.company.brand_name).upper()}-{new_num}"
                    new_emp_code = new_emp_code if official_email else ''
                    if not EmployeeWorkDetails.objects.filter(employee=instance).exists():
                        EmployeeWorkDetails.objects.create(
                        employee=instance,
                        # employee_number=f"{slugify(company.brand_name).upper()}-{int(EmployeeWorkDetails.objects.filter(employee__company=company).order_by('-id').first().employee_number.split('-')[1]) + 1}"
                        employee_number = new_emp_code,
                        employee_status = "Active"
                        )
                    else:
                        wd = EmployeeWorkDetails.objects.get(employee=instance)
                        # wd.employee_number = f"{slugify(company.brand_name).upper()}-{int(EmployeeWorkDetails.objects.filter(employee__company=company).order_by('-id').first().employee_number.split('-')[1]) + 1}"
                        wd.employee_number = new_emp_code
                        wd.employee_status = "Active"
                        wd.save()      
            
            if work_details and 'employee_status' in work_details and instance.user.is_superuser and work_details.get('employee_status') != 'Active':
                raise serializers.ValidationError(
                                {
                                    "data": {
                                        "error": "You are not allowed to modify the Employee Status of a SuperAdmin"
                                    }
                                }
                            )
            # company = instance.company
            # subscription = company.subscriptions.all().order_by('-taken_date').first()
            # current_count = company.employees.filter(work_details__employee_status='Active').count()
            # if work_details and 'employee_status' in work_details and work_details.get('employee_status') == 'Active' and subscription.total_no_of_employes < current_count + 1:
            #     raise serializers.ValidationError(
            #         {
            #             "error": "Active List Cant be more than Subscription limit count."
            #         }
            #     )   
            today = timezone_now().date()
            probation_period = work_details.get('probation_period','')
            date_of_join = validated_data.get('date_of_join','')
            if date_of_join and EmployeeExperienceDetails.objects.filter(employee_id=instance.id, to_date__gte=date_of_join, is_deleted=False).exists():
                raise serializers.ValidationError(
                                {
                                    "data": {
                                        "error": "Date of Joining should be more than the Work Experience TO DATE"
                                    }
                                }
                            ) 
            work_details["probation_period_left"] = 0
            if probation_period:
                if not date_of_join:
                    date_of_join = instance.date_of_join 
                employe_regular = date_of_join + datetime.timedelta(days=probation_period)
                if probation_period != 0 and today <= employe_regular:
                    EmployeeLeaveRuleRelation.objects.filter(employee_id=instance.id, leave_rule__allowed_under_probation=False
                                                    ).update(effective_date=employe_regular)
                pb_left = max((employe_regular - today).days, 0)
                work_details["probation_period_left"] = pb_left
            # WORK DETAILS
            wd_id = None
            if ('first_name' or 'last_name') in validated_data :
                user_obj = instance.user                    
                if 'middle_name' in validated_data and validated_data.get("middle_name").strip():
                    user_obj.username = f'{validated_data.get("first_name", instance.first_name)} {validated_data.get("middle_name", instance.middle_name)} {validated_data.get("last_name", instance.last_name)}'
                else:
                    user_obj.username = f'{validated_data.get("first_name", instance.first_name)} {validated_data.get("last_name", instance.last_name)}'
                if official_email:
                    user_obj.email = official_email
                user_obj.save()
            if 'middle_name' not in validated_data:
               validated_data['middle_name'] = ''        
            try:
                wd_id = instance.work_details.id
            except ObjectDoesNotExist:
                ...
            if validated_data.get('employee_image'):
                if 'image' not in validated_data['employee_image'].content_type:
                    raise serializers.ValidationError(
                        {
                            'data': 'File Must be image format'
                        }
                    )

            if attendance_rule:
                att_data = {"attendance_rule_id":attendance_rule}
                current_session_year, is_created = SessionYear.objects.get_or_create(session_year=timezone_now().year)
                att_data['session_year'] = current_session_year
                att_data['employee_id'] = instance.id
                att_data['effective_date'] = timezone_now().date()
                obj = AssignedAttendanceRules.objects.filter(employee_id=instance.id)
                if obj.exists():
                    obj.update(**att_data)
                else:
                    obj = AssignedAttendanceRules.objects.create(**att_data)
                
            today = timezone_now().date()
            if work_details and work_details.get('employee_status') and work_details.get('employee_status') == 'Active':
                k = EmployeeResignationDetails.objects.filter(employee=instance,is_deleted=False)
                if k.exists() and k.first().termination_date and k.first().termination_date<=today:
                    k.update(termination_date = None)
                    if not k.first().resignation_date:
                        k.update(resignation_status = '')
                if k.exists() and k.first().resignation_date:
                    final_resign_day = k.first().resignation_date + datetime.timedelta(days=k.first().notice_period) 
                    if final_resign_day <= today :
                        k.update(resignation_date = None, notice_period = None)
                        if not k.first().termination_date:
                            k.update(resignation_status = '')
                    
            work_details["employee"] = instance
            # EmployeeWorkDetails.objects.update_or_create(id=wd_id, defaults=work_details)
            if wd_id:
                EmployeeWorkDetails.objects.filter(id=wd_id).update(**work_details)
                if 'department' in work_details and 'sub_department' not in work_details:
                    EmployeeWorkDetails.objects.filter(id=wd_id).update(sub_department=None)
            else:
                EmployeeWorkDetails.objects.create(employee=instance,**work_details)
                
            if validated_data.get('official_email') and validated_data.get('personal_email'):
                if validated_data.get('official_email') == validated_data.get('personal_email'):
                    raise serializers.ValidationError(
                                {
                                    "data": {
                                        "error": "Employee Official Email and Personal Email should not be same"
                                    }
                                }
                            )
            reporting_manager_qs = EmployeeReportingManager.objects.filter(manager_id=instance.id,is_deleted=False,manager_type__manager_type=ManagerType.PRIMARY)
            if work_details.get('employee_status') == "Inactive" and reporting_manager_qs.exists():
                try:
                    # Get Primary Manger
                    manager_type = ManagerType.objects.get(manager_type=ManagerType.PRIMARY)
                    #Get First Admin for company
                    first_admin = Employee.objects.get(id=1)
                    # Reporting manager Employee List
                    emp_list = list(reporting_manager_qs.values_list('employee_id',flat=True))
                    EmployeeReportingManager.objects.filter(employee_id__in=emp_list,manager_type__manager_type=ManagerType.PRIMARY, is_deleted=False).delete()
                    # EmployeeReportingManager.objects.filter(employee_id_in=emp_list,manager_typemanager_type_in=[ManagerType.PRIMARY,ManagerType.SECONDARY], is_deleted=False).delete()
                    for emp in emp_list:
                        secondary_mangr_obj = EmployeeReportingManager.objects.filter(employee_id=emp,manager_type__manager_type=ManagerType.SECONDARY,is_deleted=False).first()
                        if secondary_mangr_obj:
                            secondary_mangr_obj.manager_type=manager_type
                            secondary_mangr_obj.save()             
                        else:
                            EmployeeReportingManager.objects.create(employee_id = emp,manager=first_admin,manager_type=manager_type)  
                except Exception as e:
                    pass

            if work_details.get('employee_status') == "Inactive":
                EmployeeWorkHistoryDetails.objects.filter(employee=instance).update(work_to=timezone_now())     
            
            #update reporting manager in EmployeeWorkHistorydetails
            if reporting_manager:
                employee_ids = [instance.id]
                data = {'ids':employee_ids,'rep_m':reporting_manager}
                manager_type_first = ManagerType.objects.filter(manager_type=ManagerType.PRIMARY).first()
                for emp_id in employee_ids:
                    if EmployeeReportingManager.objects.filter(employee_id=emp_id, manager_id=reporting_manager, 
                                                               manager_type__manager_type=ManagerType.PRIMARY, is_deleted=False).exists():
                        continue
                    elif EmployeeReportingManager.objects.filter(employee_id=emp_id, manager_id=reporting_manager, 
                                                               manager_type__manager_type=ManagerType.SECONDARY, is_deleted=False).exists():
                        EmployeeReportingManager.objects.filter(employee_id=emp_id,
                                                                manager_type__manager_type=ManagerType.PRIMARY, 
                                                               is_deleted=False).update(is_deleted=True)
                        EmployeeReportingManager.objects.filter(employee_id=emp_id, manager_id=reporting_manager, 
                                                               manager_type__manager_type=ManagerType.SECONDARY, is_deleted=False).update(
                                                                manager_type = manager_type_first 
                                                               )
                    else:
                        EmployeeReportingManager.objects.filter(employee_id=emp_id,
                                                                manager_type__manager_type=ManagerType.PRIMARY, 
                                                               is_deleted=False).update(is_deleted=True)
                        EmployeeReportingManager.objects.create(
                            employee_id=emp_id, manager_id=reporting_manager,manager_type = manager_type_first
                        ) 
                        
                emp_df = pd.DataFrame(data)
                current_date = timezone_now()
                m_type = "Primary"
                emp_df.apply(lambda obj: EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],manager_id=obj['rep_m'], work_to__isnull=True, work_from__date=current_date.date()).update(manager_type=m_type) 
                                    if EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],manager_id=obj['rep_m'], work_to__isnull=True, work_from__date=current_date.date()).exists()
                                    else (EmployeeWorkHistoryDetails.objects.get_or_create(employee_id=obj['ids'], manager_id=obj['rep_m'], work_from=current_date, manager_type=m_type),
                                        EmployeeWorkHistoryDetails.objects.filter(Q(employee_id=obj['ids'],manager_id=obj['rep_m'], work_to__isnull=True), ~Q(manager_type=m_type)).update(work_to=current_date)), axis=1)
                emp_df['manager_ids'] = emp_df.apply(lambda obj:
                                    list(EmployeeReportingManager.objects.filter(employee_id=obj['ids'], is_deleted=False).values_list('manager_id',flat=True)), axis=1)                   
                emp_df.apply(lambda obj:
                    EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],work_to__isnull=True,department__isnull=True).exclude(manager_id__in =obj['manager_ids']).update(work_to=timezone_now()), axis=1)  
            #update Department in EmployeeWorkHistorydetails
            if work_details and work_details.get('department',''):
                e_ids = [instance.id]
                dep_id =  work_details.get('department')
                dep_df = pd.DataFrame(e_ids,columns=['e_ids']) 
                dep_df['dep_id'] = dep_id.id 
                if len(dep_df) !=0:
                    dep_df.apply(lambda obj: ''
                                    if EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['e_ids'],department_id=obj['dep_id'], work_to__isnull=True).exists()
                                    else EmployeeWorkHistoryDetails.objects.get_or_create(employee_id=obj['e_ids'],department_id=obj['dep_id'], work_from=timezone_now()), axis=1 )
                    
                    dep_df.apply(lambda obj: EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['e_ids'],department_id__isnull=False, work_to__isnull=True
                                                                                       ).exclude(department_id=obj['dep_id']).update(work_to=timezone_now()), axis=1) 
            ###  Email and Whatsapp Funcs
            hr_query = Employee.objects.filter(is_deleted=False,work_details__employee_status='Active',roles__name='HR',
                company_id=instance.company.id)
            hr_email =  list(hr_query.values_list('official_email',flat=True))  
            hr_phone =  list(hr_query.values_list('user__phone',flat=True))  
            manager_ins = instance.employee.filter(is_deleted=False, manager_type__manager_type=ManagerType.PRIMARY).first()
            hr_phone.append(manager_ins.manager.user.phone) if manager_ins else hr_phone
            # if manager_ins and official_email:
                # manager/hr Email notifications
                # manager_hr_email_notifications(instance, manager_ins, hr_email, logged_in_user)
                
                # manager/hr Whatsapp notifications
                # manager_hr_whatsapp_notifications(instance, manager_ins, hr_phone, domain)
                
                #employee email notifications about reporting manager
                # employee_email_about_manager(instance, manager_ins, logged_in_user)
                
                #employee Whatsapp notifications about reporting manager
                # employee_whatsapp_about_manager(instance, manager_ins, domain)
                
                #employee email notifications about welcome
                # employee_email_welcome(instance, manager_ins)
                
                #employee Whatsapp notifications about welcome
                # employee_whatsapp_welcome(instance, domain)
            
            #update onboarding status
            template = OnBoardingModule.objects.filter(company=instance.company)
            if onboarding_status and template.exists():
                status = False if onboarding_status == 'Assigned' else True
                emp_on_board, is_created = EmployeeOnboardStatus.objects.get_or_create(employee_id=instance.id, onboarding_module=template.first())
                emp_on_board.is_deleted = status
                emp_on_board.save()
            
            # transaction.commit()
            data = super().update(instance, validated_data)
            #update employee ATS
            dep_id =work_details.get('department').id if work_details and work_details.get('department','') else instance.work_details.department_id
            desig_id =work_details.get('designation').id if work_details and work_details.get('designation','') else instance.work_details.designation_id
            emp_status = work_details.get('employee_status') if work_details and work_details.get('employee_status','') else instance.work_details.employee_status
            status_id = 4
            if emp_status == 'Active':
                status_id=1
            elif emp_status == 'InActive':
                status_id=2
            elif emp_status == 'YetToJoin':
                status_id=3
                
            payload = {
                'company_id':instance.company.id,
                'emp_code': instance.work_details.employee_number,
                'emp_first_name': validated_data.get('first_name',instance.first_name),
                'emp_middle_name': validated_data.get('middle_name',instance.middle_name),
                'emp_last_name': validated_data.get('middle_name',instance.middle_name),
                'dept_id': dep_id,
                'designation_id': desig_id,
                'pernonal_email': validated_data.get('personal_email',instance.personal_email),
                'office_email': validated_data.get('official_email',instance.official_email),
                'is_active': status_id
            }
            update_employee_ats(payload)
            
        except Exception as e:
            # transaction.rollback(sid)
            raise e
        return data
    
class EmployeeWorkDocSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDocumentationWork
        fields = (
            "id",
            "employee",
            "document_title",
            "document_description",
            "created_by",
            "is_deleted",
        )

class CTCHistorySerializer(serializers.ModelSerializer):
    employee_code = serializers.ReadOnlyField()
    employee_name = serializers.ReadOnlyField()
    old_ctc = serializers.ReadOnlyField()
    changed_on = serializers.ReadOnlyField()
    changed_by = serializers.ReadOnlyField()
    new_ctc = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CTCHistory
        fields = ['employee_code', 'employee_name', 'old_ctc', 'changed_on', 'changed_by', 'new_ctc']
    
    def get_new_ctc(self, obj):
        new_ctc_history_obj = obj.employee.employee_ctc_history.filter(updated_at__gt = obj.updated_at).order_by('updated_at').first()
        if new_ctc_history_obj:
            return new_ctc_history_obj.updated_ctc
        else:
            return obj.employee.salary_details.ctc

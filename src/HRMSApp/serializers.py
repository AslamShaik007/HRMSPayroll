import random
import subprocess
import datetime
import logging
import django

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db import transaction
from django.contrib.auth.models import Permission
from django.utils.text import slugify
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework import serializers

from attendance.models import AssignedAttendanceRules, AttendanceRuleSettings
from company_profile.models import StatutoryDetails , CompanyPolicyTypes
from core.serializers import ContentTypeRelatedField
from core.utils import get_user, timezone_now
from directory.models import Employee, EmployeeWorkDetails
from directory.serializers import EmployeeDetailSerializer
from HRMSApp.models import (
    Attachment,
    CompanyDetails,
    Modules,
    Registration,
    Roles,
    States,
    User,
    CompanyCustomizedConfigurations
)
from billing.models import PlanDetail
from leave.serializers import EmployeeLeaveRuleRelationSerializer
from leave.models import LeaveRules, EmployeeLeaveRuleRelation
from leave.services import init_leaverules, init_leaverule_settings
from attendance.services import init_shiftsetup_settings
from payroll.services import (
    init_epfsetup,
    init_esi,
    init_paysalarycomponents,
    init_professiontax,
    init_taxdetails,
    init_payslip_fields,
    init_payslip_templates,    
    init_default_list, 
)
from directory.services import init_session_year
from roles import models as role_models
from roles.utils import ROLES_INPUT
from roles.role_creation import role_creation
from roles.module_sub_creation import RoleModuleMappingsOnInitial
from payroll.models import EmployeeComplianceNumbers
from performance_management.models import NotificationDates
from attendance.models import ConsolidateNotificationDates, AttendanceRules
from django.db import models as db_models
from leave.models import WorkRules, WorkRuleChoices
            
logger = logging.getLogger('django')
class RegistrationSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(
        queryset=CompanyDetails.objects.filter(), required=False
    )
    password = serializers.CharField(required=False, write_only=True)
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
    )

    class Meta:
        model = Registration
        fields = [
            "email",
            "name",
            "terms_and_conditions",
            "phone",
            "company_size",
            "company",
            "password",
            "user",
        ]

    # Validating Password and Confirm Password while Registration
    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        return super().create(validated_data)


class UpdatePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        max_length=255, style={"input_type": "password"}, write_only=True
    )
    email = serializers.EmailField()
    token = serializers.CharField(write_only=True)

    class Meta:
        fields = ("password", "email", "token")

    def validate(self, attrs):
        user = get_user(**attrs)
        if user is None:
            raise serializers.ValidationError("User Not Found")

        if not PasswordResetTokenGenerator().check_token(user, attrs.get("token", "-")):
            raise serializers.ValidationError("Token is not Valid or Expired")

        return attrs

    def create(self, validated_data):
        user = get_user(**validated_data)
        user.set_password(validated_data["password"])
        user.save()
        return user

    def update(self, instance, validated_data):
        instance.set_password(validated_data["password"])
        instance.save()
        return instance


# Send password reset mail to user
class SendPasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)

    class Meta:
        fields = ["email"]

    def validate(self, attrs):
        email = attrs.get("email")
        if User.objects.filter(email=email).exists():
            User.objects.get(email=email)
            return attrs
        else:
            raise serializers.ValidationError("You are not a Registered User")


class RoleSerializer(serializers.ModelSerializer):
    employee = serializers.CharField(write_only=True, required=False)
    delete_role = serializers.BooleanField(
        write_only=True, required=False, default=False
    )
    employees = EmployeeDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Roles
        fields = (
            "id",
            "name",
            "code",
            "slug",
            "description",
            "employee",
            "delete_role",
            "employees",
        )

    def update(self, instance, validated_data):
        if "employee" in validated_data and not instance.is_deleted:
            employee = Employee.objects.get(id=validated_data["employee"])
            if validated_data.get("delete_role", False):
                employee.roles.remove(instance)
            else:
                employee.roles.add(instance)
            employee.save()

        return super().update(instance, validated_data)


class RoleDetailSerializer(serializers.ModelSerializer):
    employees = EmployeeDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Roles
        fields = (
            "id",
            "name",
            "code",
            "slug",
            "description",
            "employees",
        )


class ModuleManagement_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Modules
        fields = "__all__"


# Serializer for user login
class UserLoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255)

    class Meta:
        model = Registration
        fields = ["email", "password"]


class state_serializer(serializers.ModelSerializer):
    class Meta:
        model = States
        fields = "__all__"


class CompanyDetailsSerializer(FlexFieldsSerializerMixin, serializers.ModelSerializer):
    """
    Serializer to represent Companay Details

    Args:
        FlexFieldsSerializerMixin (_type_): _description_
        serializers (_type_): _description_
    
    Updated-By: Padmaraju P
    Changes: When User Registerd User Got permission of Admin
    AJAY, 24.12.2022
    """

    reg_details = RegistrationSerializer(required=False)
    employee = serializers.SerializerMethodField(required=False)
    selfie_status = serializers.SerializerMethodField(required=False)

    class Meta:
        model = CompanyDetails
        fields = [
            "company_name",
            "brand_name",
            "domain_name",
            "reg_details",
            "id",
            "employee",
            "selfie_status",
            "company_id",
            "multitenant_key",
            "company_uid",
            "is_multitenant",
            "web_site"
        ]
        extra_kwargs = {"id": {"read_only": True}}

    def primary_validation(self, data, **kwargs):
        """
        Initial validation during creation

        AJAY, 28.12.2022
        """
        company = CompanyDetails.objects.filter(company_name=data["company_name"])
        phone = Registration.objects.filter(phone=data["reg_details"]["phone"])
        email = Registration.objects.filter(email=data["reg_details"]["email"])
        brand_name = CompanyDetails.objects.filter(brand_name=data.get("brand_name",''))
        # multitenant = data["multitenant"]
        # features    = data["feature"]

        if company.exists():
            raise serializers.ValidationError(
                f'The Company {data["company_name"]} is already registered.'
            )

        if phone.exists() or Employee.objects.filter(phone=data["reg_details"]["phone"]).exists():
            raise serializers.ValidationError("The Phone Number alreday registered.")

        if email.exists() or Employee.objects.filter(official_email=data["reg_details"]["email"]).exists():
            raise serializers.ValidationError("The Email alreday registered.")

        if brand_name.exists():
            raise serializers.ValidationError(
                "The Brand Name is already registered."
            )

        # return data
        
        # if multitenant:
        #     CompanyDetails.is_multitenat = True
            
        # for feature in features:
        #     CompanyDetails.feature.add(feature.id)
        #     CompanyDetails.sav()    

        return data

    def validate(self, data):
        """
        Validator processor

        Args:
            attrs (_type_): _description_

        AJAY, 24.12.2022
        """
        return data

    def get_employee(self, obj):
        # print(self.context["email"])
        # employee = Employee.objects.get(official_email=self.context["email"])
        # return {"id": employee.id, "name": employee.name}
        try:
            return Employee.objects.filter(
                official_email=self.context["email"]
                ).annotate(
                    name = db_models.F("user__username"),
                    ).values(
                    "id", 
                    "name",
                    "work_details__employee_number"
                )[0]
        except Exception as e:
            print("EXCEPTION", e)
            return {}
    def get_selfie_status(self, obj):
        employee = Employee.objects.get(official_email=self.context["email"])
        try:
            selfie_status = AssignedAttendanceRules.objects.get(employee=employee)
            return {"status": selfie_status.attendance_rule.enable_attendance_selfie}
        except Exception:
            return {"status": "false"}

        # selfie_status = AssignedAttendanceRules.objects.filter(employee=obj.id)
        # if selfie_status:
        # selfie_status = AssignedAttendanceRules.objects.get(employee=obj.id)
        # return {"status": selfie_status.attendance_rule.enable_attendance_selfie}
        # else:
        #     return {"status": "-"}

    # from directory.serializers import EmployeeDetailSerializer

    # return EmployeeDetailSerializer(instance=employee).data

    # return employe
    
    def roles_data_creation(self, company_id, role_id):
        """
        Adding All role Modules And Submodules Model Level Permissions to New Company Admin
        """
        module_names = list(ROLES_INPUT['modules'])
        submodule_names = []
        modules = role_models.RolesModules.objects.filter(name__in=module_names).values_list('id', flat=True)
        [submodule_names.extend(list(ROLES_INPUT['modules'][module_name]['submodules'])) for module_name in ROLES_INPUT['modules'].keys()]
        for module in modules:
            role_module_map, role_module_map_created = role_models.RoleModuleMapping.objects.get_or_create(
                module_id=module,
                role_id=role_id,
                company_id=company_id,
                can_add=True,
                can_change=True,
                can_view=True,
                can_delete=True
            )
            submodules = role_models.RolesSubModule.objects.filter(name__in=list(ROLES_INPUT['modules'][
                    role_module_map.module.name
                ]['submodules'])).values_list('id', flat=True)
            for submodule in submodules:
                module_submodule_map, module_submodule_map_created = role_models.ModuleSubmoduleMapping.objects.get_or_create(
                    role_module_map_id=role_module_map.id,
                    submodule_id=submodule,
                    can_add=True,
                    can_change=True,
                    can_view=True,
                    can_delete=True
                )
                submod_models = role_models.SubModuleModelLeavelMapping.objects.filter(submodule_id=module_submodule_map.submodule.id).values(
                    'model_id', 'model__name'
                    )
                for model in submod_models:
                    role_models.RoleSubmoduleModelMapping.objects.get_or_create(
                        mod_sub_map_id=module_submodule_map.id, model_id=model['model_id'],
                        can_add=True,
                        can_change=True,
                        can_view=True,
                        can_delete=True
                    )
                    permission_add = Permission.objects.get(codename=f'add_{model["model__name"]}'.lower())
                    permission_view = Permission.objects.get(codename=f'view_{model["model__name"]}'.lower())
                    permission_delete = Permission.objects.get(codename=f'delete_{model["model__name"]}'.lower())
                    permission_change = Permission.objects.get(codename=f'change_{model["model__name"]}'.lower())
                    role_module_map.permissions.add(permission_add.id)
                    role_module_map.permissions.add(permission_view.id)
                    role_module_map.permissions.add(permission_change.id)
                    role_module_map.permissions.add(permission_delete.id)
        return

    # @transaction.atomic
    def create(self, validated_data):
        """
        Overwrite default create method

        Args:
            validated_data (_type_): _description_

        Returns:
            _type_: CompanyDetails

        AJAY, 24.12.2022
        """
        logger.critical(f"Current DB {django.db.connections.databases['default']['NAME']}")
        sid = transaction.set_autocommit(autocommit=False)
        try:
            plan_type =  self.context.get("plan_type")
            self.primary_validation(data=validated_data)
            secret = random.randint(111, 999)
            logger.info(validated_data["company_name"])
            company = CompanyDetails(company_name=validated_data["company_name"])
            company.brand_name = validated_data["company_name"][:3] + str(secret)
            if validated_data.get('brand_name') and validated_data.get('brand_name').strip():
                company.brand_name = validated_data.get('brand_name').strip()
            company.domain_name = validated_data["company_name"][:3] + str(secret)
            company.company_uid = validated_data.get("company_uid")
            company.multitenant_key = validated_data.get("multitenant_key")
            company.is_multitenant = validated_data.get("is_multitenant", False)
            company.web_site = validated_data.get("web_site", None)
            company.company_id = validated_data.get("company_id", "")
            company.save()
            CompanyCustomizedConfigurations.objects.create(company_id=company.id)
            PlanDetail.objects.get_or_create(plan_type=plan_type)
            # creating user
            user = User.objects.create_superuser(
                email=validated_data["reg_details"]["email"],
                username=validated_data["reg_details"]["name"],
                phone=validated_data["reg_details"]["phone"],
                password=validated_data["reg_details"].pop("password")
            )
            # Registration Model
            validated_data["reg_details"]["company"] = company.id
            validated_data["reg_details"]["user"] = user.id
            user_serializer = RegistrationSerializer(data=validated_data["reg_details"])
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()

            statutory = StatutoryDetails(company=company)
            statutory.save()
            attendance_rules = AttendanceRuleSettings(company=company)
            attendance_rules.save()
            # Default Leave rules create
            # plan_details =  [{'plan_type': 'premium', 'price': 50000.0, 'num_of_employees': 50}, {'plan_type': 'enterprise', 'price': 25000.0, 'num_of_employees': 2500}, {'plan_type': 'basic', 'price': 10000.0, 'num_of_employees': 1000}]
            # for plan in plan_details:
            #     PlanDetail.objects.get_or_create(**plan)
            init_leaverules(self, company=company)
            init_leaverule_settings(self, company=company)
            #Default Session year Create
            init_session_year(self, company=company)
            # Default payroll setup
            init_epfsetup(self, company=company)
            init_esi(self, company=company)
            init_professiontax(self, company=company)
            init_paysalarycomponents(self, company=company)
            init_taxdetails(self, company=company)
            # init_paySchedule(self, company=company)
            #Default Attendance Shifts Setup
            init_shiftsetup_settings(self, company=company)
            init_payslip_fields(self, company=company)
            init_payslip_templates(self, company=company)
            #init_default_list(self, company=company)
            choices = ("Recruitment and Hiring", "Onboarding", "Performance and Development", "Compensation and Benefits",
                       "Employee Relations","Legal and Compliance", "Termination and Exit", "Miscellaneous")
            for choice in choices:
                CompanyPolicyTypes.objects.get_or_create(policy_name=choice)
            emp = Employee.objects.create(
                company=company,
                user=user,
                first_name=validated_data["reg_details"]["name"],
                middle_name = '',
                last_name = '',
                official_email=validated_data["reg_details"]["email"],
                phone=validated_data["reg_details"].get("phone", ""),
                date_of_join=timezone_now().date(),
            )
            EmployeeWorkDetails.objects.create(employee=emp, 
                                            employee_status='Active',
                                            employee_number=f'{slugify(company.brand_name).upper()}-{company.employees.count()}')
            obj,is_created = EmployeeComplianceNumbers.objects.get_or_create(employee=emp)
            logger.critical(f"started roles")
            role_creation()
            logger.critical(f"roles ended")
            roles = Roles.objects.filter()
            if roles.exists():
                for role in roles:
                    RoleModuleMappingsOnInitial().main()
                    self.roles_data_creation(company.id, role.id)
                    if role.name == "ADMIN":
                        emp.roles.add(role.id)
                        emp.payroll_status=False
                        emp.save()
            # roles = Roles.objects.filter(name='ADMIN')
            # if roles.exists():
            #     RoleModuleMappingsOnInitial().main()
            #     emp.roles.add(roles.first().id)
            #     self.roles_data_creation(company.id, roles.first().id)
            #     emp.payroll_status=False
            #     emp.save()
            try:
                lop_id = LeaveRules.objects.get(company_id=company.id, name='Loss Of Pay', is_deleted=False)
                addition_id,created = LeaveRules.objects.get_or_create(company_id=company.id, name='Additional Leaves', is_deleted=False)
                addition_id.leaves_allowed_in_year = 160
                addition_id.save()
                comp_off_id, created = LeaveRules.objects.get_or_create(company_id=company.id, name='Comp Off', is_deleted=False)
                leave_ser = EmployeeLeaveRuleRelationSerializer(data = {'employee': [emp.id], 'rules': [lop_id.id, addition_id.id, comp_off_id.id], 'effective_date': timezone_now().date()})
                if leave_ser.is_valid(raise_exception=False):
                    leave_ser.save()
            except Exception as e :
                print("exception;",e)
                pass
            
            now_date = timezone_now().date()
            notification_qs = NotificationDates.objects.create(
                company_id = company.id,
                notification_start_date = now_date,
                notification_end_date = now_date,
                reporting_manager_start_date = now_date,
                reporting_manager_end_date = now_date,
                employees_kra_deadline_date = now_date
            )
            cn_qs = ConsolidateNotificationDates.objects.create(
                company_id = company.id,
                employee_start_date = now_date,
                employee_end_date  = now_date,
                reporting_manager_start_date  = now_date,
                reporting_manager_end_date  = now_date,
                hr_manager_start_date  = now_date,
                hr_manager_end_date  = now_date
                )
            
            #adding default attendance rules
            try:
                att_data = {"company":company ,"name":"Default Attendance Rule", "shift_in_time":"11:00", "shift_out_time":"20:00", 
                            "full_day_work_duration":"08:00", "half_day_work_duration":"5:0"}
                AttendanceRules.objects.create(**att_data)
            except Exception as e:
                logging.critical(f"Error in adding default attendance rules - {company.company_name}")
            
            #adding default Work Week rules
            try:
                wr = WorkRules.objects.create(company=company, name='Default_Work_Rule')
                dts = [WorkRuleChoices(work_rule=wr, saturday=0, sunday=0, week_number=i) for i in range(6)]
                WorkRuleChoices.objects.bulk_create(dts)
            except Exception as e:
                logging.critical(f"Error in adding default Work Week rules - {company.company_name}")
            
            
            
            transaction.commit()
        except Exception as e:
            transaction.rollback(sid)
            raise e
        return company

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class AttachmentSerializer(serializers.ModelSerializer):
    """
    Basic Attachment Serailizer

    """

    content_type = ContentTypeRelatedField()

    class Meta:
        model = Attachment
        fields = "__all__"

# import packages
import logging
import random
import traceback
import datetime
from core.utils import success_response, error_response
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models as db_models
from core.utils import generate_random_string

from django.db.models import F, Value, Case, When, Q
from django.db.models.functions import Concat
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db.models import Prefetch
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.shortcuts import get_object_or_404

from rest_framework import permissions, status
from rest_framework.generics import (
    DestroyAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated

from core.smtp import send_email
from core.utils import email_render_to_string, get_user,timezone_now
from core.views import AbstractListAPIView, AbstractListCreateAPIView
from directory.models import Employee
from .custom_permissions import IsHrAdminPermission
from HRMSProject.multitenant_setup import MultitenantSetup

from roles import models as role_models
from roles.utils import ROLES_INPUT

from HRMSApp.models import (
    Attachment,
    CompanyDetails,
    PhoneOTP,
    Registration,
    Roles,
    User,
    # Features,
    Grade, CompanyCustomizedConfigurations
)
from company_profile.models import CompanyGrades
from HRMSApp.renderers import UserRenderer
from HRMSApp.serializers import (
    CompanyDetailsSerializer,
    RoleDetailSerializer,
    RoleSerializer,
    SendPasswordResetEmailSerializer,
    UpdatePasswordSerializer,
)
from HRMSApp.utils import Util
from performance_management.models import NotificationDates
from billing.models import TransactionDetails, PlanDetail

# from billing.models import TransactionDetails
from .utils import get_user_totp_device
# from django.contrib.sites.models import Site
import requests
from attendance.models import ConsolidateNotificationDates
import pyotp
# import twillo
from twilio.rest import Client
from HRMSProject.settings.base import twilio_account_sid, twilio_auth_token

from alerts.utils import check_alert_notification
# current_site = Site.objects.get_current()
# domain=current_site.domain


logger = logging.getLogger(__name__)
UserModel = get_user_model()
from core.whatsapp import WhatsappMessage


def get_tokens_for_user(user):
    """
    refresh token for new login
    """
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }

def get_role_data_of_user(role_id, company_id):
    existed_data = role_models.RoleModuleMapping.objects.filter(role_id=role_id, company_id=company_id).values(
        'module_id',
        'module__name', 'can_add', 'can_delete', 'can_change', 'can_view',
        'modulesubmodulemapping__submodule__id',
        'modulesubmodulemapping__submodule__name',
        'modulesubmodulemapping__can_add', 'modulesubmodulemapping__can_delete',
        'modulesubmodulemapping__can_change', 'modulesubmodulemapping__can_view',
        )
    existed_data_convert = {
        'modules': {}
    }
    final_output = ROLES_INPUT
    for module_data in existed_data:
        if module_data['module__name'] not in existed_data_convert['modules'].keys():
            existed_data_convert['modules'][module_data['module__name']] = {
                'module_name':  module_data['module__name'],
                'add': False, 'delete': False, 'change': False, 'view': False,
                'submodules': {}
            }
        if module_data['modulesubmodulemapping__submodule__name'] not in existed_data_convert['modules'][module_data['module__name']]['submodules'].keys():
            existed_data_convert['modules'][module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']] = {
                'submodule__name': module_data['modulesubmodulemapping__submodule__name'],
                'add': False, 'delete': False, 'change': False, 'view': False
            }
        existed_data_convert['modules'][module_data[
            'module__name']]['add'] = module_data['can_add']
        existed_data_convert['modules'][
            module_data['module__name']]['delete'] = module_data['can_delete']
        existed_data_convert['modules'][
            module_data['module__name']]['change'] = module_data['can_change']
        existed_data_convert['modules'][
            module_data['module__name']]['view'] = module_data['can_view']
        existed_data_convert['modules'][
            module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']]['add'] = module_data['modulesubmodulemapping__can_add']
        existed_data_convert['modules'][
            module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']]['change'] = module_data['modulesubmodulemapping__can_change']
        existed_data_convert['modules'][
            module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']]['view'] = module_data['modulesubmodulemapping__can_view']
        existed_data_convert['modules'][
            module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']]['delete'] = module_data['modulesubmodulemapping__can_delete']
    for module_name in final_output['modules'].keys():
        # print(module_name)
        if existed_data_convert['modules'].get(module_name):
            final_output['modules'][module_name]['add'] = existed_data_convert['modules'][module_name]['add']
            final_output['modules'][module_name]['delete'] = existed_data_convert['modules'][module_name]['delete']
            final_output['modules'][module_name]['view'] = existed_data_convert['modules'][module_name]['view']
            final_output['modules'][module_name]['change'] = existed_data_convert['modules'][module_name]['change']
            for sub_module in ROLES_INPUT['modules'][module_name]['submodules'].keys():
                # print(sub_module)
                if existed_data_convert['modules'][module_name]['submodules'].get(sub_module):
                    final_output['modules'][module_name]['submodules'][sub_module]['add'] = existed_data_convert['modules'][module_name]['submodules'][sub_module]['add']
                    final_output['modules'][module_name]['submodules'][sub_module]['view'] = existed_data_convert['modules'][module_name]['submodules'][sub_module]['view']
                    final_output['modules'][module_name]['submodules'][sub_module]['delete'] = existed_data_convert['modules'][module_name]['submodules'][sub_module]['delete']
                    final_output['modules'][module_name]['submodules'][sub_module]['change'] = existed_data_convert['modules'][module_name]['submodules'][sub_module]['change']
                if final_output['modules'][module_name]['submodules'][sub_module].get('models'):
                    del final_output['modules'][module_name]['submodules'][sub_module]['models']
    return final_output

# Function for User Registration
class UserRegistrationView(ListCreateAPIView):
    renderer_classes = [UserRenderer]
    model = CompanyDetails
    serializer_class = CompanyDetailsSerializer
    allowed_methods = ("GET", "POST", "PUT", "PATCH")
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        data = self.request.GET if self.request.method == "GET" else self.request.data
        qs = CompanyDetails.objects.all()

        if "company_name" in data:
            return qs.filter(company_name__iexact=data["company_name"])

        return qs

    def post(self, request, *args, **kwargs):
        data = request.data
        domain = f"{self.request.scheme}://{self.request.get_host()}/"
        serializer = CompanyDetailsSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            instance = serializer.save()
            body=f'''
    Hello {data["reg_details"]["name"]},
    
    Your registration has been completed successfully,
    Please click the following link to log in: {domain}
    
    Thanks & Regards,
    {data["company_name"]}.
    '''
            email_data={
                'subject':f'Welcome to {data["company_name"]}',
                'body':body,
                'to_email':data["reg_details"]["email"]
            }
            if check_alert_notification("Company Profile",'Sign Up', email=True):
                Util.send_email(email_data)

            # employee Whatsapp notifications
            phone = data["reg_details"].get("phone",'')
            company_name = data['company_name']
            try:
                employee_data = {
                        'phone_number': phone,
                        'subject': f"Welcome to {company_name}",
                        'body_text1' :"Your registration has been completed successfully",
                        'body_text2' : " ",
                        'url': f"{domain}organization",
                        "company_name":  data["company_name"]
                        }
                if check_alert_notification("Company Profile",'Sign Up', whatsapp=True):
                    WhatsappMessage.whatsapp_message(employee_data)
            except Exception as e:
                logger.warning(f"Error while sending Whatsapp notificaton to {phone} in Company {company_name} creation: {e}") 
            # welcome_url = settings.WELCOME_URL
            # email_context = {
            #     "user": data["reg_details"]["name"],
            #     "welcome_url": welcome_url,
            # }
            # email_subject = email_render_to_string(
            #     template_name="mails/welcome_message_subject.txt",
            #     context=email_context,
            #     strip=True,
            # )
            # email_message = email_render_to_string(
            #     template_name="mails/welcome_message.html", context=email_context
            # )
            # send_email(
            #     data["reg_details"]["email"], email_subject, message=email_message
            # )
            return Response(
                {
                    "status": status.HTTP_201_CREATED,
                    "data" : "you are successfully registered "
                    # "data": CompanyDetailsSerializer(
                    #     instance=instance,
                    #     context={"email": data["reg_details"]["email"]},
                    # ).data,
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {
                    "status": status.HTTP_400_BAD_REQUEST,
                    "data": {"message": "System error, please contact Sys Admin!"},
                },
                status=status.HTTP_201_CREATED,
            )


class CompanyCustomizedConfigurationsAPIView(APIView):
    model = CompanyCustomizedConfigurations
    
    def get(self, request):
        company_id = self.request.user.employee_details.first().company.id
        data = self.model.objects.filter(company_id=company_id).values()
        
        return Response(
            success_response(list(data), "Success", 200),
            status=status.HTTP_200_OK
        )
    
    def put(self, request):
        data = request.data
        company_id = self.request.user.employee_details.first().company.id
        obj = self.model.objects.filter(company_id=company_id)
        if not obj.exists():
            obj = self.model.objects.create(company_id=company_id, **data)
            obj = self.model.objects.filter(company_id=company_id)
        else:
            obj.update(**data)
        return Response(
            success_response(list(obj.values()), "Updated", 200),
            status=status.HTTP_200_OK
        )
        

class CompanyDetailsRetrieveUpdateView(RetrieveUpdateAPIView):
    """
    Company Details view

    AJAY, 02.01.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyDetailsSerializer
    detail_serializer_class = CompanyDetailsSerializer
    lookup_field = "id"
    queryset = CompanyDetails.objects.all()


# GET Api's for Module Access and Role Management
class RoleRetrieveUpdateView(RetrieveUpdateAPIView):
    """
    View to update ROLES

    AJAY, 02.01.2023
    """

    renderer_classes = [UserRenderer]

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = RoleSerializer
    detail_serializer_class = RoleDetailSerializer
    lookup_field = "id"
    queryset = Roles.objects.order_by('-id')


class RoleCreateView(AbstractListCreateAPIView):
    """
    View to get or create CompanyDepartment

    AJAY, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = RoleSerializer
    detailed_serializer_class = RoleDetailSerializer
    queryset = Roles.objects.prefetch_related(
        Prefetch("roles_employees", to_attr="employees")
    ).all()


class RoleRetrieveView(AbstractListAPIView):
    # serializer_class = RoleDetailSerializer
    # lookup_field = "company"
    # lookup_url_kwarg = "company_id"
    # queryset = Roles.objects.all().order_by("id")

    # def filter_queryset(self, queryset):
    #     filter_kwargs = {
    #         self.lookup_field: self.kwargs[self.lookup_url_kwarg],
    #         "is_deleted": False,
    #     }
    #     print(filter_kwargs)
    #     return queryset.prefetch_related(
    #         Prefetch(
    #             "roles_employees",
    #             queryset=Employee.objects.filter(**filter_kwargs),
    #             to_attr="employees",
    #         )
    #     )
    model = Roles
    def get(self, request, *args, **kwargs):
        params = request.query_params
        company = kwargs.get("company_id")
        try:
            q_filters = db_models.Q(is_deleted=False)
            qs = self.model.objects.filter(q_filters).prefetch_related("roles_employees","employees").annotate(
                count =db_models.Count("roles_employees__id",filter=db_models.Q(roles_employees__id__isnull=False,roles_employees__company_id=company,roles_employees__work_details__employee_status__in=["Active","YetToJoin"])),
                employees = ArrayAgg(
                    db_models.expressions.Func(
                    db_models.Value('id'), 'roles_employees__id',
                    db_models.Value('name'), 'roles_employees__user__username',
                    default=db_models.Value(""),
                    function='jsonb_build_object',
                    output_field=db_models.JSONField()
                ),filter = Q(roles_employees__id__isnull=False, roles_employees__company_id=company,roles_employees__work_details__employee_status__in=["Active","YetToJoin"])
                )
            ).values(
                "id","name","code","slug","description","employees","count"
            ).order_by("id")
            return Response(
                qs
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "Got error in role data fetch", 400),
                status=status.HTTP_400_BAD_REQUEST
            )
        
    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            role_name = data.get("role_name").upper().strip()
            if int((len(role_name))) >= 20:
                return Response(
                        error_response('Role name should not be more then 20 charecters', "Role name should not be more then 20 charecters", 400),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            role = request.user.employee_details.first().roles.values_list('name', flat=True).first()
            if role == "ADMIN":
                qs = self.model.objects.filter(name=role_name) #,is_deleted = True
                if qs.exists():
                    return Response(
                        error_response('Role with this name already exists', "Role with this name already exists", 400),
                        status=status.HTTP_400_BAD_REQUEST
                    )   
                code_name = f'{role_name}-{generate_random_string()}'
                self.model.objects.create(
                    name = role_name,
                    slug=code_name.lower(),
                    code=code_name.upper(),
                )
                return Response(
                    success_response("Succusfully created the role","Succusfully created the role",200),
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    error_response('Only Admin can add the role', 'Only Admin can add the role', 400),
                    status=status.HTTP_400_BAD_REQUEST
                ) 
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "Got error while create role", 400),
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def patch(self, request, *args, **kwargs):
        data = request.data
        params = request.query_params
        try:
            if "id" not in params:
                    return Response(
                        error_response("Id required","Id required",200),
                        status=status.HTTP_200_OK
                    )
            role = request.user.employee_details.first().roles.values_list('name', flat=True).first()
            if role == "ADMIN":
                role_name = data.get("role_name").upper().strip()
                qs = self.model.objects.filter(name=role_name).exclude(id = params.get("id"))
                if qs.exists():
                    return Response(
                        error_response('Role with this name already exists', "Role with this name already exists", 400),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                obj = self.model.objects.get(id=params.get("id"))
                if obj.name in Roles.DEFAULT_ADMIN_ROLES:
                    return Response(
                        error_response(f"{obj.name} is default role you can't update", f"{obj.name} is default role you can't update", 400),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                code_name = f'{role_name}-{generate_random_string()}'
                obj.name = role_name
                obj.slug=code_name.lower()
                obj.code=code_name.upper()
                obj.save()
                return Response(
                    success_response("Succusfully updated the role","Succusfully updated the role",200),
                    status=status.HTTP_200_OK
                )   
            else:
                return Response(
                    error_response('Only Admin can update the role', 'Only Admin can update the role', 400),
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "Got error while update role", 400),
                status=status.HTTP_400_BAD_REQUEST
            )
        
    def delete(self, request, *args, **keargs):
        params = request.query_params
        try:
            if "id" not in params:
                return Response(
                    error_response("Id required","Id required",200),
                    status=status.HTTP_200_OK
                )
            role = request.user.employee_details.first().roles.values_list('name', flat=True).first()
            if role == "ADMIN":
                obj = self.model.objects.get(id=params.get("id"))
                if obj.name in Roles.DEFAULT_ADMIN_ROLES:
                    return Response(
                        error_response(f"{obj.name} is default role you can't delete", f"{obj.name} is default role you can't delete", 400),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if Employee.objects.filter(roles__name=obj.name,work_details__employee_status__in = ["Active","YetToJoin"]).exists():
                    return Response(
                        error_response(f"{obj.name} is already assigned,cannot be deleted", f"{obj.name} is already assigned,cannot be deleted", 400),
                        status=status.HTTP_400_BAD_REQUEST
                    ) 
                obj.is_deleted = True
                obj.save()
                return Response(
                    success_response("Succusfully deleted the role","Succusfully deleted the role",200),
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    error_response('Only Admin can delete the role', 'Only Admin can delete the role', 400),
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "Got error while delete role", 400),
                status=status.HTTP_400_BAD_REQUEST
            )


# Mobile number Existed in User model or not
class MobileNumbrValidationAPIView(APIView):
    renderer_classes = [UserRenderer]
    permission_classes = (IsAuthenticated, )

    def post(self, request, format=None):
        phone_number = request.data.get("phone")
        if phone_number:
            phone = str(phone_number)
            user = Registration.objects.filter(phone__iexact=phone)

            if user.exists():
                return Response(
                    {"status": False, "detail": "Phone number already exists."}
                )
            else:
                return Response({"status": True, "detail": "phone number not existed"})
        else:
            return Response(
                {
                    "status": False,
                    "detail": "Phone number is not given in post request.",
                }
            )


# Email Id Filter and existed in User model or not
class EmailValidationAPIView(APIView):
    renderer_classes = [UserRenderer]
    permission_classes = (IsAuthenticated, )

    def post(self, request, format=None):
        email = request.data.get("email")
        if email:
            email = str(email)
            user = Registration.objects.filter(email__iexact=email)

            if user.exists():
                return Response({"status": False, "detail": "Email_Id already exists."})
            else:
                return Response({"status": True, "detail": "Email_Id not existed"})
        else:
            return Response(
                {"status": False, "detail": "Email_Id is not given in post request."}
            )


# User Login View
class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(
        self,
        request,
    ):
        """
        Default post handler

        """
        data = request.data
        password = request.data.get("password")
        email = request.data.get("email")
        phone = request.data.get("phone")

        if email is None and phone is None:
            return Response(
                {
                    "status": status.HTTP_400_BAD_REQUEST,
                    "errors": {"non_field_errors": ["Invalid Credentials!"]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if phone:
            try:
                # _user = Registration.objects.get(phone=phone)
                # email = _user.email
                email = get_user(**data)
            except Registration.DoesNotExist:
                return Response(
                    {
                        "status": status.HTTP_404_NOT_FOUND,
                        "errors": {"non_field_errors": ["Invalid Phone Number"]},
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        user = authenticate(request=request, email=email, password=password)
        if user is not None:
            user = get_user(**data)
            token = get_tokens_for_user(user)
            employee = Employee.objects.get(official_email=email)
            try:
                if employee.work_details.employee_status == 'Inactive':
                    return Response(
                        {'message': 'User is Inactive'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                if employee.work_details.employee_status == 'YetToJoin':
                    return Response(
                        {'message': 'User Yet To Join'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            except Exception as e:
                pass
                    
            company = employee.company
            roles_assigned = employee.roles.all()
            if not roles_assigned.exists():
                return Response(
                    {
                        "status": status.HTTP_404_NOT_FOUND,
                        "errors": {"message": "No role Assigned for this employee, please Contact Admin."},
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            role_data = get_role_data_of_user(roles_assigned.first().id, company.id)
            try:
                plan_type = PlanDetail.objects.first().plan_type
            except:
                plan_type = "integrated"
            employee.is_sign_up = True
            employee.save()
            from django.db import connection
            current_db_name = connection.settings_dict['NAME']
            
            # onboard restriction
            emp_roles = employee.roles.all().values_list('name',flat=True)
            is_role = True
            for i in ['HR', 'ADMIN']:
                if i not in emp_roles:
                    is_role = False
                else:
                    is_role = True
            doj = employee.date_of_join + datetime.timedelta(days=30)
            is_onboard_enable = False
            if is_role or (doj and doj >= timezone_now().date()):
                is_onboard_enable = True
                
                
            return Response(
                {
                    "status": status.HTTP_200_OK,
                    "token": token,
                    "data": CompanyDetailsSerializer(
                        instance=company, context={"email": email}
                    ).data,
                    "roles": list(roles_assigned.values_list('name', flat=True)),
                    "existed_roles_data": role_data,
                    "roles_id": list(roles_assigned.values_list('id', flat=True)),
                    "plan": plan_type,
                    "employee_image": employee.employee_image.name,
                    "attendance_rules": company.attendancerulesettings_set.values('attendance_input_cycle_from', 
                                                                                'attendance_input_cycle_to').first(),
                    "user_email" : user.email,
                    "user_phone" : user.phone,
                    "first_name" : employee.first_name,
                    "middle_name" : employee.middle_name,
                    "last_name" : employee.last_name,
                    "sub_domain" : current_db_name.split("_")[0],
                    "is_onboard_enable":is_onboard_enable
                },  # , context={"email": email}
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "status": status.HTTP_404_NOT_FOUND,
                    "errors": {"message": "Invalid Credentials"},
                },
                status=status.HTTP_404_NOT_FOUND,
            )


class UpdatePasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    renderer_classes = [UserRenderer]

    def post(self, request, format=None):
        serializer = UpdatePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Emails to Admins    
        try:
            user = User.objects.get(email=serializer.data.get('email'))
            company_id = user.employee_details.first().company.id
            company_name = user.employee_details.first().company.company_name
            user_emp_code = user.employee_details.first().work_details.employee_number
            admin_email = Employee.objects.filter(is_deleted=False, roles__name='ADMIN', company_id=company_id,
                                                  work_details__employee_status='Active'
                                                  ).values('official_email','user__username','work_details__employee_number','phone'
                                                           ).exclude(id=user.employee_details.first().id)
            subject = f"Password Updated For {user.username} [{user_emp_code}]"
            domain = f"{self.request.scheme}://{self.request.get_host()}/"
            for obj in admin_email:
                body=f'''
    Hello {obj['user__username']} [{obj['work_details__employee_number']}],
    
    This is to notify you that changes have been made to an employee's account credentials. Please review the details of the changes below:
    
    Employee Name: {user.username}
    Employee ID: {user_emp_code}
    Date & Time of Change: {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")}
    Nature of Change: Credentials Reset
    
    If these changes were not authorized or if you have any concerns regarding the security of the account, please take appropriate action to investigate and rectify the situation. 
    
    Ensuring the security of our employees accounts is paramount, and prompt attention to any discrepancies is crucial.
        
    Thanks & Regards,
    {company_name.title()}
            
            '''
                data={
                    'subject':subject,
                    'body':body,
                    'to_email':obj['official_email']
                }
                if check_alert_notification("Company Profile",'Change Password', email=True) or check_alert_notification("Company Profile",'Forgot password', email=True):
                    Util.send_email(data)
                # employee Whatsapp notifications
            try:
                employee_data = {
                        'phone_number': obj['phone'] ,
                        'subject': subject,
                        'body_text1' :f"{user.username} [{user_emp_code}] account credentials were changed",
                        'body_text2' : "Nature of Change: Credentials Update",
                        'url': f"{domain}userprofile",
                        "company_name":  company_name.title()
                        }
                if check_alert_notification("Company Profile",'Change Password', whatsapp=True) or check_alert_notification("Company Profile",'Forgot password', email=True):
                    WhatsappMessage.whatsapp_message(employee_data)
            except Exception as e:
                logger.warning(f"Error while sending Whatsapp notificaton to {obj['user__username']} for password update : {e}") 
        except Exception as e:
            logger.warning(f"Error in pasword update to {serializer.data.get('email', '')} : {e}")
        
        #Emails to Employee
        try:
            user_emp_code = user.employee_details.first().work_details.employee_number
            body=f'''
    Hello {user.username} [{user_emp_code}],

    We are writing to inform you that changes have been made to your account credentials in our HRMS. 
    
    This could include updates to your login information or a recent password reset.
    
    If you did not initiate these changes or if you have any concerns regarding the security of your account, 
    
    please contact our HR department, Your security is our top priority.
        
    Thanks & Regards,
    {company_name.title()}
        
        '''
            data={
                'subject':'Important Changes to Your Account Credentials',
                'body':body,
                'to_email':user.email
            }
            if check_alert_notification("Company Profile",'Change Password', email=True):
                Util.send_email(data)
            # employee Whatsapp notifications
            try:
                employee_data = {
                        'phone_number': user.phone ,
                        'subject': "Important Changes to Your Account Credentials",
                        'body_text1' :"We are writing to inform you that changes have been made to your account credentials in our HRMS",
                        'body_text2' : " If you did not initiate these changes. please contact our HR department, Your security is our top priority. ",
                        'url': f"{domain}userprofile",
                        "company_name":  company_name.title()
                        }
                if check_alert_notification("Company Profile",'Change Password', whatsapp=True):
                    WhatsappMessage.whatsapp_message(employee_data)
            except Exception as e:
                logger.warning(f"Error while sending Whatsapp notificaton to  {user.username}  in Important Changes : {e}") 
        except Exception as e:
            print("error_2:",e)
        
        return Response(
            data={
                "message": "Password Changed Successfully",
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )

class UserChangePasswordView(APIView): 
    permission_classes = [permissions.AllowAny]
    allowed_methods = ["post"]

    def post(self, request, format=None):
        data = request.data
        if data.get("old_password", None) is None:
            result = {
                "errors": "password not provided",
                "status": status.HTTP_400_BAD_REQUEST,
            }
            return Response(data=result, status=status.HTTP_400_BAD_REQUEST)

        if (
            any(key not in data for key in ("new_password", "confirm_password"))
            or data["new_password"] != data["confirm_password"]
        ):
            result = {
                "errors": "passwords did not match",
                "status": status.HTTP_400_BAD_REQUEST,
            }
            return Response(data=result, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(data.get("old_password", None)):
            result = {
                "errors": "Invalid password!",
                "status": status.HTTP_400_BAD_REQUEST,
            }
            return Response(data=result, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(data["new_password"])
        user.save()
    
        # Emails to Admins    
        try:
            company_id = user.employee_details.first().company.id
            company_name = user.employee_details.first().company.company_name
            user_emp_code = user.employee_details.first().work_details.employee_number
            admin_email = Employee.objects.filter(is_deleted=False, roles__name='ADMIN', company_id=company_id,
                                                  work_details__employee_status='Active'
                                                  ).values('official_email','user__username','work_details__employee_number','phone'
                                                           ).exclude(id=user.employee_details.first().id)
            subject = f"Password Updated For {user.username} [{user_emp_code}]"
            domain = f"{self.request.scheme}://{self.request.get_host()}/"
            for obj in admin_email:
                body=f'''
    Hello {obj['user__username']} [{obj['work_details__employee_number']}],
    
    This is to notify you that changes have been made to an employee's account credentials. Please review the details of the changes below:
    
    Employee Name: {user.username}
    Employee ID: {user_emp_code}
    Date & Time of Change: {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")}
    Nature of Change: Credentials Update
    
    If these changes were not authorized or if you have any concerns regarding the security of the account, please take appropriate action to investigate and rectify the situation. 
    
    Ensuring the security of our employees accounts is paramount, and prompt attention to any discrepancies is crucial.
        
    Thanks & Regards,
    {company_name.title()}
            
            '''
                data={
                    'subject':subject,
                    'body':body,
                    'to_email':obj['official_email']
                }
                if check_alert_notification("Company Profile",'Change Password', email=True):
                    Util.send_email(data)
            # Admin Whatsapp notifications
            
            try:
                employee_data = {
                        'phone_number': obj['phone'],
                        'subject': subject,
                        'body_text1' :f"{user.username} [{user_emp_code}] account credentials were changed",
                        'body_text2' : "Nature of Change: Credentials Update",
                        'url': f"{domain}changepassword",
                        "company_name":  company_name.title()
                        }
                if check_alert_notification("Company Profile",'Change Password', email=True):
                    WhatsappMessage.whatsapp_message(employee_data)
            except Exception as e:
                logger.warning(f"Error while sending Whatsapp notificaton to {obj['user__username']} in passwoard: {e}") 
        except Exception as e:
            pass
        
        #Emails to Employee
        try:
            user_emp_code = user.employee_details.first().work_details.employee_number
            body=f'''
    Hello {user.username} [{user_emp_code}],

    We are writing to inform you that changes have been made to your account credentials in our HRMS. 
    
    This could include updates to your login information or a recent password reset.
    
    If you did not initiate these changes or if you have any concerns regarding the security of your account, 
    
    please contact our HR department, Your security is our top priority.
        
    Thanks & Regards,
    {company_name.title()}
        
        '''
            data={
                'subject':'Important Changes to Your Account Credentials',
                'body':body,
                'to_email':user.email
            }
            if check_alert_notification("Company Profile",'Change Password', email=True):
                Util.send_email(data)
            # employee Whatsapp notifications
            try:
                employee_data = {
                        'phone_number': user.phone,
                        'subject': 'Important Changes to Your Account Credentials',
                        'body_text1' :"This is to notify you that changes have been made to your account credentials in our HRMS",
                        'body_text2' : ' ',
                        'url': f"{domain}changepassword",
                        "company_name":  {company_name.title()}
                        }
                if check_alert_notification("Company Profile",'Change Password', email=True):
                    WhatsappMessage.whatsapp_message(employee_data)
            except Exception as e:
                logger.warning(f"Error while sending Whatsapp notificaton to {user.username} in Important Changes to Your Account: {e}")
        except Exception as e:
            pass
        return Response(
            {"msg": "Password Changed Successfully"}, status=status.HTTP_200_OK
        )


# Function for User ForgetPassword and Reset The New Password
class SendResetPasswordEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    """
    Password reset email view

    Note: Serialzer is not required as no data is save or update in the DB

    AJAY, 04.02.2023
    """

    renderer_classes = [UserRenderer]

    def post(self, request, format=None):
        """
        Default post handler

        Args:
            request (_type_): _description_
            format (_type_, optional): _description_. Defaults to None.

        AJAY, 05.02.2023
        """
        data = request.data
        user = get_user(**data)
        if user is None:
            return Response(
                data={
                    "message": "User is not registered",
                    "status": status.HTTP_404_NOT_FOUND,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        token = PasswordResetTokenGenerator().make_token(user)
        emp_code = '-'
        company_name = user.employee_details.first().company.company_name
        try:
            user_info = user.employee_details.first()
            emp_code = user_info.work_details.employee_number
        except Exception as e:
            pass
        body=f'Hello {user.username} [{emp_code}],\n\nclick on below link to reset your pasword\n\n{request.scheme}://{request.get_host()}/newpassword?email={user.email}&token={token}\n\nThanks & Regards,\n{company_name}.'  
        data={
            'subject':'Reset Your Password',
            'body':body,
            'to_email':user.email
        }
        if check_alert_notification("Company Profile",'Forgot password', email=True):
            Util.send_email(data)
                    # employee Whatsapp notifications
        try:
            employee_data = {
                    'phone_number': user.phone,
                    'subject': 'Reset Your Password',
                    'body_text1' : "Please reset your password ",
                    'body_text2' : " ",
                    'url': f"{request.scheme}://{request.get_host()}/newpassword?email={user.email}&token={token}",
                    "company_name": company_name
                    }
            if check_alert_notification("Company Profile",'Forgot password', whatsapp=True):
                WhatsappMessage.whatsapp_message(employee_data)
        except Exception as e:
            print('e',e)
            logger.warning(f"Error while sending Whatsapp notificaton to {user.username} reset Your Password: {e}")

        # reset_url = f"{settings.RESET_URL}?email={user.email}&token={token}"

        # email_context = {"user": user.email, "reset_url": reset_url}

        # email_subject = email_render_to_string(
        #     template_name="mails/password_reset_subject.txt",
        #     context=email_context,
        #     strip=True,
        # )
        # email_message = email_render_to_string(
        #     template_name="mails/password_reset.html", context=email_context
        # )

        # email = send_email(user.email, email_subject, message=email_message)

        return Response(
            data={
                "message": "Password Reset link sent successfully",
                "uid": user.email,
                "token": token,
                # "email": email.get_status_display(),
            },
            status=status.HTTP_200_OK,
        )


# Function for User RESEND ACTIVATION Link and set The Password
class ResendActivationLinkAPIView(APIView):
    model = Employee 
    renderer_classes = [UserRenderer]
    # permission_classes = (IsHrAdminPermission, )

    def post(self, request, format=None):
        print("Coming Here")
        data = request.data
        # domain = f" {request.scheme}://{request.get_host()}/userLoginForm?email={emp_email}&phone={emp_phone}"
        emp_code = '-'
        company_name = request.user.employee_details.first().company.company_name
        try:
            user_info = request.user.employee_details.first()
            emp_code = user_info.work_details.employee_number
        except Exception as e:
                pass
        for i in data: 
            emp_name = i['name']
            emp_email = i['email']
            emp_phone = i['phone']
            body = f'''

    Hello {emp_name.title()} [{emp_code}],

    We are excited to welcome you to {company_name.title()}! As you prepare to embark on this exciting journey with us, kindly click on the link below to login

    {request.scheme}://{request.get_host()}/userLoginForm?email={emp_email}&phone={emp_phone}

    This link will guide you through the steps to finalize your profile, provide essential documents, and familiarize yourself with our company policies.

    If you encounter any issues or have questions during the process, please don't hesitate to reach out to our HR team at hr@pranathiss.com.

    We look forward to having you on board and wish you a smooth and successful onboarding experience.

    Thanks & Regards,
    {company_name.title()}.
            '''
            data={
                'subject':'Join your team',
                'body':body,
                'to_email':emp_email
            }
            
            try:
                emp = Employee.objects.get(official_email=emp_email)
                wd = emp.work_details
                wd.employee_status = 'Active'
                wd.save()
            except:
                pass
            if check_alert_notification("Employee Management",'Invite', email=True):
                Util.send_email(data)
            # employee Whatsapp activation link
            try:
                employee_data = {
                        'phone_number': emp_phone,
                        'subject': 'Join your team',
                        'body_text1' : f"We are excited to welcome you to {company_name}! As you prepare to embark on this exciting journey with us",
                        'body_text2' : " ",
                        'url': f"{request.scheme}://{request.get_host()}/userLoginForm?email={emp_email}&phone={emp_phone}",
                        "company_name":  company_name
                        }
                if check_alert_notification("Employee Management",'Invite', whatsapp=True):
                    WhatsappMessage.whatsapp_message(employee_data)
            except Exception as e:
                logger.warning(f"Error while sending Whatsapp notificaton to  {emp_name} Join your team: {e}")
        return Response(
            data={
                "message": "Resend Activation link sent successfully",
            },
            status=status.HTTP_200_OK,
        )

class ValidatePhoneSendOTP(APIView):
    """
    Validate Phone Number and send OTP View
    """

    permission_classes = [permissions.AllowAny]
    renderer_classes = [UserRenderer]

    def post(self, request, *args, **kwargs):
        # name = request.data.get('name' , False)
        phone_number = request.data.get("phone")
        if phone_number:
            phone = str(phone_number)
            user = User.objects.filter(phone__iexact=phone)

            if user.exists():
                return Response(
                    {"status": False, "detail": "Phone number already exists."}
                )
            else:
                key = send_otp(phone)

                if key:
                    old = PhoneOTP.objects.filter(phone__iexact=phone)
                    if old.exists():
                        old = old.first()
                        count = old.count
                        old.count = count + 1
                        old.save()
                        return Response(
                            {"status": True, "detail": "OTP sent successfully."}
                        )
                    else:
                        PhoneOTP.objects.create(
                            # name = name,
                            phone=phone,
                            otp=key,
                        )
                        # link = f'http://2factor.in/API/V1/{settings.API_KEY}/SMS/{phone}/{key}'
                        # link= "https://d7-verify.p.rapidapi.com/messages/v1/balance"
                        # requests.get(link)
                        return Response(
                            {"status": True, "detail": "OTP sent successfully."}
                        )
                else:
                    return Response({"status": False, "detail": "Sending OTP error."})

        else:
            return Response(
                {
                    "status": False,
                    "detail": ("Phone number is not given in post request."),
                }
            )


def send_otp(phone):
    if phone:
        key = random.randint(99999, 999999)
        return key
    else:
        return False


class ValidatePhoneOTP(APIView):
    """
    Validate OTP View
    """

    permission_classes = [permissions.AllowAny]
    renderer_classes = [UserRenderer]

    def post(self, request, *args, **kwargs):
        phone = request.data.get("phone", False)
        otp_sent = request.data.get("otp", False)

        if phone and otp_sent:
            old = PhoneOTP.objects.filter(phone__iexact=phone)
            if old.exists():
                old = old.first()
                otp = old.otp
                if str(otp_sent) == str(otp):
                    old.validated = True
                    old.save()
                    return Response(
                        {
                            "status": True,
                            "detail": "OTP mactched. Please proceed for registration.",
                        }
                    )

                else:
                    return Response({"status": False, "detail": "OTP incorrect."})
            else:
                return Response(
                    {
                        "status": False,
                        "detail": "First proceed via sending otp request.",
                    }
                )
        else:
            return Response(
                {
                    "status": False,
                    "detail": "Please provide both phone and otp for validations",
                }
            )


class ValidateEmailPhoneSendOTP(APIView):
    """
    Validate Phone/Email and send OTP View
    """

    permission_classes = [permissions.AllowAny]
    renderer_classes = [UserRenderer]

    def post(self, request, *args, **kwargs):
        data = request.data
        # print(data, "data")
        user = get_user(**data)
        # print(user)
        email = request.data.get("email")
        phone_number = request.data.get("phone")
        name = request.data.get("user__username")

        domain = f"{self.request.scheme}://{self.request.get_host()}/"
        if phone_number:
            phone = str(phone_number)
            user = User.objects.filter(phone__iexact=phone)
            company_name = user.first().employee_details.first().company.company_name

            if user.exists():
                key = send_otp(phone)
                if key:
                    PhoneOTP.objects.filter(phone__iexact=phone).delete()
                    PhoneOTP.objects.create(
                        phone=phone,
                        otp=key,
                    )
                    # link = f'http://2factor.in/API/V1/{settings.API_KEY}/SMS/{phone}/{key}'
                    # link= "https://d7-verify.p.rapidapi.com/messages/v1/balance"
                    # requests.get(link)
                    #employee OTP VALIDATION    
                    try:
                        employee_data = {
                                'phone_number': user.first().phone,
                                'subject': 'Reset Your Password',
                                'body_text1' : f"'Your OTP is {key}." ,
                                'body_text2' : " ",
                                'url': f"{domain}userprofile",
                                "company_name":  company_name.title()
                                }
                        if check_alert_notification("Company Profile",'Forgot password', whatsapp=True):
                            WhatsappMessage.whatsapp_message(employee_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to  {user.first().username.title()} Reset Your Password: {e}")
                    return Response(
                        {"status": True, "detail": "OTP sent successfully."}
                    )
                else:
                    return Response({"status": False, "detail": "Sending OTP error."})
            else:
                return Response(
                    {"status": False, "detail": "Phone number not exists in users."}
                )
        elif email:
            email = str(email)
            user = User.objects.filter(email__iexact=email)

            if user.exists():
                key = send_otp(email)
                if key:
                    PhoneOTP.objects.filter(email__iexact=email).delete()
                    PhoneOTP.objects.create(
                        email=email,
                        otp=key,
                    )
                    # link = f'http://2factor.in/API/V1/{settings.API_KEY}/SMS/{phone}/{key}'
                    # link= "https://d7-verify.p.rapidapi.com/messages/v1/balance"
                    # requests.get(link)
                    # body = f"Your OTP for reset password is: {key}"
                    emp_code = '-'
                    company_name = user.first().employee_details.first().company.company_name
                    try:
                        user_info = user.first().employee_details.first()
                        emp_code = user_info.work_details.employee_number
                    except Exception as e:
                            pass
                    body=f"Hello {user.first().username.title()} [{emp_code}],\n'Your OTP is {key}\n\nThanks & Regards,\n{company_name.title()}." 
                    data = {
                        "subject": "Reset Your Password",
                        "body": body,
                        "to_email": email,
                    }
                    if check_alert_notification("Company Profile",'Forgot password', email=True):
                        Util.send_email(data)
                    #employee rest password otp
                    try:
                        employee_data = {
                                'phone_number': user.first().phone,
                                'subject': 'Reset Your Password',
                                'body_text1' : f"Your OTP is {key}." ,
                                'body_text2' : " ",
                                'url': f"{domain}userprofile",
                                "company_name":  company_name.title()
                                }
                        if check_alert_notification("Company Profile",'Forgot password', whatsapp=True):
                            WhatsappMessage.whatsapp_message(employee_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {user.first().username.title()}Reset Your Password: {e}")
                    return Response(
                        {
                            "status": True,
                            "msg": "Password Reset OTP Sent, Please check your Email",
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response({"status": False, "detail": "Sending OTP error."})
            else:
                return Response(
                    {"status": False, "detail": "email not exists in User."}
                )

        else:
            return Response(
                {
                    "status": False,
                    "detail": "email/Phone number is not given in post request.",
                }
            )

        return False


class ValidateEmailPhoneOTP(APIView):
    """
    Validate Phone/Email OTP View
    """

    permission_classes = [permissions.AllowAny]
    renderer_classes = [UserRenderer]

    def post(self, request, *args, **kwargs):
        data = request.data
        phone = request.data.get("phone", False)
        otp_sent = request.data.get("otp", False)
        email = request.data.get("email", False)
        if phone and otp_sent:
            old = PhoneOTP.objects.filter(phone__iexact=phone)
            if old.exists():
                old = old.first()
                otp = old.otp
                if str(otp_sent) == str(otp):
                    old.validated = True
                    old.save()
                    User_data = User.objects.filter(phone=phone)[0]
                    email = User_data.email
                    user = get_user(**data)
                    # print(user)
                    # name = User_data.name
                    # serializer = SendPasswordResetEmailSerializer(data=data)
                    # serializer.is_valid(raise_exception=True)
                    user_email = User.objects.get(email=email)
                    uid = urlsafe_base64_encode(force_bytes(user_email.id))
                    token = PasswordResetTokenGenerator().make_token(user_email)
                    return Response(
                        {
                            "status": True,
                            "detail": "OTP mactched. Please proceed for next step.",
                            "uid": uid,
                            "token": token,
                            # "name": name,
                        }
                    )

                else:
                    return Response({"status": False, "detail": "OTP incorrect."})
            else:
                return Response(
                    {
                        "status": False,
                        "detail": "First proceed via sending otp request.",
                    }
                )

        elif email and otp_sent:
            old = PhoneOTP.objects.filter(email__iexact=email)
            if old.exists():
                old = old.first()
                otp = old.otp
                if str(otp_sent) == str(otp):
                    old.validated = True
                    old.save()
                    User_data = User.objects.filter(email=email)[0]
                    # name = User_data.first_name
                    serializer = SendPasswordResetEmailSerializer(data=data)
                    serializer.is_valid(raise_exception=True)
                    user_email = User.objects.get(email=email)
                    uid = urlsafe_base64_encode(force_bytes(user_email.id))
                    token = PasswordResetTokenGenerator().make_token(user_email)
                    return Response(
                        {
                            "status": True,
                            "detail": "OTP mactched. Please proceed for next step.",
                            "uid": uid,
                            "token": token,
                            # "name": name,
                        }
                    )

                else:
                    return Response({"status": False, "detail": "OTP incorrect."})
            else:
                return Response(
                    {
                        "status": False,
                        "detail": "First proceed via sending otp request.",
                    }
                )

        else:
            return Response(
                {
                    "status": False,
                    "detail": "Please provide both phone/email and otp for validations",
                }
            )


class TOTPRegisterView(APIView):
    """
    Use this endpoint to set up a new TOTP device
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None):
        params = request.GET
        user = None
        try:
            user = get_user(**params)
        except UserModel.DoesNotExist:
            return Response(
                status=status.HTTP_404_NOT_FOUND,
                data={
                    "message": "User Not Found",
                    "status": status.HTTP_404_NOT_FOUND,
                },
            )

        if user is None:
            return Response(
                status=status.HTTP_404_NOT_FOUND,
                data={
                    "message": "User Not Found",
                    "status": status.HTTP_404_NOT_FOUND,
                },
            )

        device = get_user_totp_device(user)
        if not device:
            device = user.totpdevice_set.create(confirmed=False)
        url = device.config_url
        return Response(url, status=status.HTTP_201_CREATED)


class TOTPVerifyView(APIView):
    """
    Use this endpoint to verify/enable a TOTP device
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, token, format=None):
        data = request.data

        try:
            user = get_user(**data)
        except UserModel.DoesNotExist:
            logger.error(f"User not found with email: {data.get('email', '')}")
            Response(
                status=status.HTTP_404_NOT_FOUND,
                data={
                    "message": f"User not found with the email << {data.get('email', '')} >>",
                    "status": status.HTTP_404_NOT_FOUND,
                },
            )

        if user is None:
            return Response(
                status=status.HTTP_404_NOT_FOUND,
                data={
                    "message": "User Not Found",
                    "status": status.HTTP_404_NOT_FOUND,
                },
            )
        device = get_user_totp_device(user)
        # device.tolerance = 0
        if device and device.verify_token(token):
            if not device.confirmed:
                device.confirmed = True
                device.save()
        # if device is not None and device.verify_token(token):
        #     if not device.confirmed:
        #         device.confirmed = True
        #         device.save()
            employee = Employee.objects.get(official_email=user.email)
            try:
                if employee.work_details.employee_status == 'Inactive':
                    return Response(
                        {'message': 'User is Inactive'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                if employee.work_details.employee_status == 'YetToJoin':
                    return Response(
                        {'message': 'User Yet To Join'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            except Exception as e:
                pass
            company = employee.company
            roles_assigned = employee.roles.all()
            if not roles_assigned.exists():
                return Response(
                    {
                        "status": status.HTTP_404_NOT_FOUND,
                        "errors": {"message": "No role Assigned for this employee, please Contact Admin."},
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            role_data = get_role_data_of_user(roles_assigned.first().id, company.id)
            try:
                plan_type = TransactionDetails.objects.first().plan_details
            except:
                plan_type = "premium"
            employee.is_sign_up = True
            employee.save()
            token = get_tokens_for_user(user)
            return Response(
                {
                    "status": status.HTTP_200_OK,
                    "token": token,
                    "data": CompanyDetailsSerializer(
                        instance=company, context={"email": user.email}
                    ).data,
                    "roles": list(roles_assigned.values_list('name', flat=True)),
                    "roles_id": list(roles_assigned.values_list('id', flat=True)),
                    "plan": plan_type,
                    "existed_roles_data": role_data,
                    "employee_image": employee.employee_image.name,
                    "attendance_rules": company.attendancerulesettings_set.values('attendance_input_cycle_from', 
                                                                                'attendance_input_cycle_to').first()
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            status=status.HTTP_404_NOT_FOUND,
            data={
                "message": "Invalid Credentials OR Device Not Registered",
                "status": status.HTTP_404_NOT_FOUND,
            },
        )


class AttachmentDeleteView(DestroyAPIView):
    lookup_field = "id"
    queryset = Attachment.objects.all()


class RolesFetchApiView(APIView):
    """
    Created-By: Padmaraju P
    Use-Case: Fetching Roles
    """
    
    permission_classes = (IsHrAdminPermission,)

    def get(self, request):
        employee = request.user.employee_details.first()
        current_company_ceo_roles = CompanyDetails.objects.filter(
            id=employee.company_id, employees__roles__id=1
            ).prefetch_related('employees__roles').order_by('employees__roles__id'
                                                            ).distinct().values_list('employees__roles__id', flat=True)

        roles = Roles.objects.filter(is_deleted=False).exclude(
            id__in=current_company_ceo_roles
        ).values('id', 'name')
        return Response(
            {
                "data": roles
            },
            status=status.HTTP_200_OK
        )

class PermissionsFetchApiView(APIView):
    """ 
    Created-By: Padmaraju
    DEFAULT:
    Permission is added to only HR-Admin

    Use-Case: 
    1. Fetching All Pemissions Provide to HR admin to provide for other roles
    
    Development Should be done:
    1. Based on Module we have to pass all other model names to give permissions
    2. Need to exclude basic django models
    3. view, add, update, delete permissions for each module should be differnt 
    4. Based On ERD diagram we have to pass all models on it.
    5. In Post Method from frontend what ever permissions we are getting based on code name we have to add to that role.
    """
    permission_classes = (IsHrAdminPermission, )
    
    # TODO RAJU
    def get(self, request):
        permissions = Permission.objects.all()
        
        return Response(
            {
                'data': permissions.values('id', 'name', 'codename')
            }
        )
    
    
class PincodeToAdressAPIView(APIView):
    """
    get adress from pincode
    """

    permission_classes = [permissions.AllowAny]
    def get(self,request):
        params = self.request.GET
        pincode = params.get("pincode")
        headers = {
        'authority': 'api.postalpincode.in',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Microsoft Edge";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.58',
        }
        response = requests.get(f'https://api.postalpincode.in/pincode/{pincode}', headers=headers)

        data=response.json()

        return Response(
                {
                    'data': data,
                },
                status=status.HTTP_200_OK
            )
    
# Fetch BANK Detailes With IFSCCODE
class FetchBankDetailes(APIView):
    renderer_classes = [UserRenderer]
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        params = self.request.GET
        ifsc = params.get("ifsccode")
        try:
            response = requests.get(f"https://bank-apis.justinclicks.com/API/V1/IFSC/{ifsc}/")  
            data = response.json()
            return Response(
                    {
                        'data': data,
                    },
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                error_response(str(e), "Data Not Found", 400),
                status=status.HTTP_400_BAD_REQUEST
            )


class GradeApiView(APIView):
    # permission_classes = [IsHrAdminPermission, ]
    model = Grade

    def get(self, request):
        params = request.query_params
        qs = self.model.objects.filter(is_deleted=False, company_id=params.get('company_id')).values('id', 'name')
        return Response(
            {
                'data': qs
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):
        data = request.data
        name = data.get('name')
        company_id = data.get('company_id')
        if self.model.objects.filter(is_deleted=False, company_id=company_id).exists():
            return Response(
                {
                    "message": "Can't Create more than one grade"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        if not name:
            return Response(
                {
                    "message": "Grade name Or Company ID were Empty"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        qs = self.model.objects.filter(name=name, company_id=company_id, is_deleted=False)
        if qs.exists():
            return Response(
                {
                    "message": f"Grade with Name {name} already exists in company"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        Grade.objects.create(
            name=name, company_id=company_id
        )
        return Response(
            {
                "message": "Grade Created Successfully"
            },
            status=status.HTTP_201_CREATED
        )

    def put(self, request):
        data = request.data
        grade_id = data.get('grade_id')
        if not grade_id:
            return Response(
                {
                    "messgae": "Grade ID is required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        obj = get_object_or_404(Grade, id=grade_id)
        old_grade_name = obj.name
        grades = CompanyGrades.objects.filter(company_id=obj.company.id, grade__icontains=old_grade_name, is_deleted=False)
        message = ""
        if 'name' in data:
            obj.name = data['name']
            message = "Grade Updated Successfully"
            for grade in grades:
                g_name = str(grade.grade)
                grade.grade = g_name.replace(old_grade_name, data['name'])
                grade.save()
        if 'is_deleted' in data:
            if data['is_deleted']:
                obj.is_deleted = data['is_deleted']
                grades.delete()
                message = "Grade deleted successfully"
        obj.save()
        return Response(
            {
                "message": message
            },
            status=status.HTTP_200_OK
        )

class ActiveEmployeesAPIView(APIView):

    # permission_classes = [permissions.IsAuthenticated]
    model = Employee

    def get(self, request):
        params = request.query_params
        from django.db import connections
        request_user_role_name =  request.user.employee_details.first().roles.values_list('name', flat=True).first()
        empids = request.user.employee_details.first().employee_manager.filter(is_deleted=False).values_list('manager__work_details__employee_number', flat=True)
        MultitenantSetup().create_to_connection(request)
        filters = Q(is_deleted=False, company_id=params.get("company_id"))
        if 'is_from_consolidated' in params:
            filters &= Q(payroll_status=True)
            if request_user_role_name in ["MANAGER", 'TEAM LEAD']:
                filters &= Q(work_details__employee_number__in=empids)
            if 'department_id' in params:
                filters &= Q(work_details__department_id__in=params.get('department_id', '').split(','))
        else:
            filters &= Q(work_details__employee_status="Active")
        exclude_filters = Q()
        if not request.headers.get("X-SELECTED-COMPANY"):
            if 'employee_ids' in params:
                exclude_filters = Q(id__in = params.get('employee_ids').split(','))
        if 'is_manager' in params :
            exclude_filters |= Q(roles__name = 'EMPLOYEE')
        if "status" in params:
            filters = Q(company_id=params.get("company_id"),work_details__employee_status__in = ["Active","YetToJoin"], is_deleted=False,)
        if 'employee_id' in params:
            filters &= Q(id__in=params.get("employee_id").split(','))
        print("filters", filters)
        qs = list(Employee.objects.filter(filters
                ).annotate(
                        employee_name = F("user__username"),
                        company_name = F("company__company_name")
                ).values(
                    'id', 'employee_name', 'work_details__employee_status','work_details__employee_number', 'official_email',
                    'first_name', 'last_name', 'middle_name', 'company_name'
                ).exclude(exclude_filters))
        MultitenantSetup().go_to_old_connection(request)
        return Response(
            {
                "data" : qs
            },
            status=status.HTTP_200_OK
        )


class ValidateOTP(APIView):
    """
    Use this endpoint to verify/enable a TOTP device
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, otp, format=None):
        data = request.data
        try:
            user = get_user(**data)
        except UserModel.DoesNotExist:
            logger.error(f"User not found with email: {data.get('email', '')}")
            Response(
                status=status.HTTP_404_NOT_FOUND,
                data={
                    "message": f"User not found with the email << {data.get('email', '')} >>",
                    "status": status.HTTP_404_NOT_FOUND,
                },
            )

        if user is None:
            return Response(
                status=status.HTTP_404_NOT_FOUND,
                data={
                    "message": "User Not Found",
                    "status": status.HTTP_404_NOT_FOUND,
                },
            )
        phone = user.phone
        # email = user.email    
        employee = Employee.objects.get(official_email=user.email)
        if employee.work_details.employee_status == 'Inactive':
            return Response(
                {'message': 'User is Inactive'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        if employee.work_details.employee_status == 'YetToJoin':
            return Response(
                {'message': 'User Yet To Join'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        company = employee.company
        roles_assigned = employee.roles.all()
        if not roles_assigned.exists():
            return Response(
                {
                    "status": status.HTTP_404_NOT_FOUND,
                    "errors": {"message": "No role Assigned for this employee, please Contact Admin."},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
            
        check_otp = PhoneOTP.objects.filter(phone__iexact=phone,validated=False,otp = str(otp))
        if not check_otp.exists() :
            return Response(
                {'message': 'Please provide correct OTP'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        check_otp_obj = check_otp.first()
        check_otp_obj.validated = True
        check_otp_obj.save()
        role_data = get_role_data_of_user(roles_assigned.first().id, company.id)

        token = get_tokens_for_user(user)
        return Response(
            {
                "status": status.HTTP_200_OK,
                "token": token,
                "data": CompanyDetailsSerializer(
                    instance=company, context={"email": user.email}
                ).data,
                "roles": list(roles_assigned.values_list('name', flat=True)),
                "existed_roles_data": role_data,
                "employee_image": employee.employee_image.name,
                "attendance_rules": company.attendancerulesettings_set.values('attendance_input_cycle_from', 
                                                                            'attendance_input_cycle_to').first()
            },
            status=status.HTTP_200_OK,
        )
        
class LoginOTP(APIView):
    
    permission_classes = [permissions.AllowAny]
    renderer_classes = [UserRenderer]

    def post(self, request, *args, **kwargs):
        data = request.data
        user = get_user(**data)
        user_secret_key = pyotp.random_base32()
        totp_mobile = pyotp.TOTP(user_secret_key, interval=60)
        domain = f"{self.request.scheme}://{self.request.get_host()}/"
        client = Client(twilio_account_sid, twilio_auth_token)
        if user is None:
                return Response(
                status=status.HTTP_404_NOT_FOUND,
                data={
                    "message": "User Not Found",
                    "status": status.HTTP_404_NOT_FOUND,
                },
            )
        phone_number = user.phone
        phone = str(phone_number)
        email = user.email
        key = totp_mobile.now()
        
        emp_code = '-'
        try:
            user_info = user.employee_details.first()
            emp_code = user_info.work_details.employee_number
        except Exception as e:
            pass
        
        if key:
            old = PhoneOTP.objects.filter(phone__iexact=phone,validated=False)
            if old.exists():
                # Mobile OTP Sending
                old = old.first()
                count = old.count
                old.count = count + 1
                old.save()
                key = old.otp

                ext = '+91'
                sms_message = f'Your OTP is: {key}'

                message = client.messages.create(
                    to=ext+phone,
                    from_='+12403396750',
                    body=sms_message
                )
                # print("came_here_finally")
                # Email OTP Sending
                company_name = user.employee_details.first().company.company_name
                body=f"Hello {user.username.title()} [{emp_code}],\n'Your OTP is {key}\n\nThanks & Regards,\n{company_name.title()}" 
                data={
                    'subject':'OTP Verification',
                    'body':body,
                    'to_email':user.email
                }
                Util.send_email(data)
                #employye login otp
                try:
                        employee_data = {
                                'phone_number': phone_number,
                                'subject': 'Reset Your Password',
                                'body_text1' : f"Your OTP is {key}" ,
                                'body_text2' : " ",
                                'url': f"{domain}userprofile",
                                "company_name":  company_name.title()
                        }
                        WhatsappMessage.whatsapp_message(employee_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to  {user.name} Reset Your Password: {e}")
                return Response(
                    {"status": True, "detail": "OTP sent successfully."}
                )
            else:
                PhoneOTP.objects.create(
                    phone=phone,
                    email = email,
                    otp=key,
                    count = 1
                )
                ext = '+91'
                sms_message = f'Your OTP is: {key}'
                
                message = client.messages.create(
                    to=ext+phone,
                    from_=+13346058360,
                    body=sms_message
                )
                company_name = user.employee_details.first().company.company_name
                body=f"Hello {user.username.title()} [{emp_code}],\n'Your OTP is {key}\n\nThanks & Regards,\n{company_name.title()}." 
                data={
                    'subject':'OTP Verification',
                    'body':body,
                    'to_email':user.email
                }
                Util.send_email(data)
                #employee login otp
                try:
                        employee_data = {
                                'phone_number': phone_number,
                                'subject': 'Reset Your Password',
                                'body_text1' : f"Your OTP is {key}" ,
                                'body_text2' : " ",
                                'url': f"{domain}userprofile",
                                "company_name":  company_name.title()
                                }
                        WhatsappMessage.whatsapp_message(employee_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to  {user.name} Reset Your Password: {e}")
                return Response(
                    {"status": True, "detail": "OTP sent successfully."}
                )
        else:
            return Response({"status": False, "detail": "Sending OTP error."})

class CompanyDeactivation(APIView):
    
    def put(self, request):
        data = request.data
        company = CompanyDetails.objects.first()
        company.is_deleted = True
        company.save()
        
        return Response(
            {
                "status": "Company Deactivated"
            }
        )

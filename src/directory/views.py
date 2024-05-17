import subprocess
import datetime
import requests
from nested_multipart_parser.drf import DrfNestedParser 
from django.contrib.postgres.aggregates import ArrayAgg, StringAgg

import traceback
from typing import Any, Optional
from ast import literal_eval

from django.apps import apps

from HRMSApp.models import FutureModule
from HRMSApp.utils import Util

from django.db import transaction
from django.db.models import Value, F, Q, CharField, Case, When

from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.db.models.functions import Concat

from rest_framework import permissions, status, response
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    UpdateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import (timezone_now, success_response, get_month_weeks, get_terminations_date, search_filter_decode, 
                        excel_converter, load_class, error_response, add_employee_ats, email_render_to_string, get_ip_address, TimestampToStrDateTime, TimestampToIST)
from core.views import AbstractListAPIView
from directory import serializers as dir_serializers
from directory.models import (
    CertificationCourseTypes,
    CourseTypes,
    DocumentsTypes,
    Employee,
    EmployeeCertifications,
    EmployeeDocumentationWork,
    EmployeeDocuments,
    EmployeeEducationDetails,
    EmployeeEmergencyContact,
    EmployeeFamilyDetails,
    EmployeeReportingManager,
    EmployeeTypes,
    ManagerType,
    QualificationTypes,
    RelationshipTypes,
    EmployeeWorkHistoryDetails,
    EmployeeExperienceDetails,
    EmployeeWorkDocuments,
    CTCHistory,
    StatusChoices,
    CompanySMTPSetup,
    CompanyDetails,
    EmployeeWorkDetails,
    EmployeePreBoardingDetails
)
from directory.serializers import (
    CertificationCourseTypeDetailSerializer,
    CertificationCourseTypeSerializer,
    CourseTypeDetailSerializer,
    CourseTypeSerializer,
    DocumentsTypeDetailSerializer,
    DocumentsTypeSerializer,
    EmployeeCertificationsDetailSerializer,
    EmployeeCertificationsSerializer,
    EmployeeDocumentationWorkDetailSerializer,
    EmployeeDocumentationWorkSerializer,
    EmployeeDocumentsDetailSerializer,
    EmployeeDocumentsSerializer,
    EmployeeEducationDetailSerializer,
    EmployeeEducationSerializer,
    EmployeeEmergencyContactDetailSerializer,
    EmployeeEmergencyContactSerializer,
    EmployeeFamilyDetailSerializer,
    EmployeeFamilySerializer,
    EmployeeReportingManagerDetailSerializer,
    EmployeeReportingManagerSerializer,
    EmployeeTypeDetailSerializer,
    EmployeeTypeSerializer,
    ManagerTypeDetailSerializer,
    ManagerTypeSerializer,
    QualificationTypeDetailSerializer,
    QualificationTypeSerializer,
    RelationshipTypeDetailSerializer,
    RelationshipTypeSerializer,
    GetEmployeeDetails,
    PastExperienceDetailserializer,
    EmployeeWorkDocSerializer,
    CTCHistorySerializer,
)
from HRMSApp.models import FutureModule
import pandas as pd
from HRMSApp.models import Roles
from HRMSApp.custom_permissions import ATSAddEmployeePermission
from HRMSProject.multitenant_setup import MultitenantSetup
from pss_calendar.models import Holidays
from django.db import models as db_models

from core.custom_paginations import CustomPagePagination
from django.db import models as db_models
from alerts.utils import check_alert_notification
from company_profile.models import Departments
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMessage, get_connection
from django.core.files.base import ContentFile
import base64

from django.template.loader import render_to_string
import weasyprint
import html
# Views for All DropDown
class CompanyEmployeeTypeRetrieveView(ListAPIView):
    """
    DropDown retrieve employeetype

    Suresh, 11.01.2023
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeTypeSerializer
    detailed_serializer_class = EmployeeTypeDetailSerializer
    queryset = EmployeeTypes.objects.all()
    
    
    def list(self, request, *args, **kwargs):
        try:
            MultitenantSetup().create_to_connection(request)
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(list(queryset), many=True)
            MultitenantSetup().go_to_old_connection(request)
            return Response(serializer.data)
        except Exception:
            MultitenantSetup().go_to_old_connection(request)
            return Response([])
            
    
    
    


class CompanyManagerTypeRetrieveView(ListAPIView):
    """
    DropDown retrieve ManagerType

    Suresh, 13.01.2023
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ManagerTypeSerializer
    detailed_serializer_class = ManagerTypeDetailSerializer
    queryset = ManagerType.objects.all()


class QualificationTypeRetrieveView(ListAPIView):
    """
    DropDown retrieve QualificationType

    Suresh, 13.01.2023
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QualificationTypeSerializer
    detailed_serializer_class = QualificationTypeDetailSerializer
    queryset = QualificationTypes.objects.all()


class CourseTypeRetrieveView(ListAPIView):
    """
    DropDown retrieve CourseType

    Suresh, 13.01.2023
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseTypeSerializer
    detailed_serializer_class = CourseTypeDetailSerializer
    queryset = CourseTypes.objects.all()


class DocumentsTypeRetrieveView(ListAPIView):
    """
    DropDown retrieve DocumentsType

    Suresh, 13.01.2023
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentsTypeSerializer
    detailed_serializer_class = DocumentsTypeDetailSerializer
    queryset = DocumentsTypes.objects.all()
    
    
    def get(self, request, *args, **kwargs):
        print("get employee")
        MultitenantSetup().create_to_connection(request)
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(list(queryset), many=True)
        MultitenantSetup().go_to_old_connection(request)
        return Response(serializer.data)
    
    
    


class RelationshipTypeRetrieveView(ListAPIView):
    """
    DropDown retrieve RelationshipType

    Suresh, 16.01.2023
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RelationshipTypeSerializer
    detailed_serializer_class = RelationshipTypeDetailSerializer
    queryset = RelationshipTypes.objects.all()
    
    
    def get(self, request, *args, **kwargs):
        try:
            MultitenantSetup().create_to_connection(request)
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(list(queryset), many=True)
            MultitenantSetup().go_to_old_connection(request)
            return Response(serializer.data)
        except Exception:
            MultitenantSetup().go_to_old_connection(request)
            return Response([])
            
    
    
    


class CertificationCourseTypeRetrieveView(AbstractListAPIView):
    """
    DropDown retrieve CertificationCourseType

    Suresh, 17.01.2023
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CertificationCourseTypeSerializer
    detailed_serializer_class = CertificationCourseTypeDetailSerializer
    queryset = CertificationCourseTypes.objects.all()


class EmployeeCreateView(APIView):
    """
    View to create Employee

    AJAY, 07.01.2023
    """
    model = Employee
    serializer_class = dir_serializers.EmployeeSerialzer
    permission_classes = [ATSAddEmployeePermission]

    def post(self, request, *args, **kwargs):
        if request.data.get('is_multitenant'):
            MultitenantSetup().get_domain_connection(request, request.data.get('multitenant_manager_company_domain',None))
            tenant_manager_data = list(Employee.objects.filter(
                work_details__employee_number = request.data.get('multitenant_manager_emp_id',None)
            ).values(
                            "work_details__employee_number", "user__username", "official_email",
                            "user__phone", 
            )
            )
        else:
            tenant_manager_data = list(Employee.objects.filter(
                id = request.data.get('reporting_manager')
            ).values(
                            "work_details__employee_number", "user__username", "official_email",
                            "user__phone", 
            )
            )
        print("tenant data", tenant_manager_data)
        # MultitenantSetup().get_domain_connection(request, request.headers.get('X-SELECTED-COMPANY'))
        MultitenantSetup().create_to_connection(request)
        current_company = request.headers.get('X-SELECTED-COMPANY')
        domain = f"{self.request.scheme}://{self.request.get_host()}/"
        request_dataed = self.request.data
        if type(request_dataed) != dict:
            request_data = request_dataed.dict()
        else:
            request_data = request_dataed
        work_details = request_data.pop('work_details',[])
        salary_details = request_data.pop('salary_details',[])
        attendance_rule = request_data.pop('attendance_rule',[])
        pf_details = request_data.pop('pf_details',[]) 
        emergency_details = request_data.pop('emergency_details',[])
        aadhaar_card_photo = request_data.pop('aadhaar_card_photo',[])
        aadhaar_card_id = request_data.pop('aadhaar_card_id','')
        pan_card_photo = request_data.pop('pan_card_photo',[])
        pan_card_id = request_data.pop('pan_card_id','')
        reporting_manager = request_data.pop('reporting_manager',[])
        insurence_doc = request_data.pop('insurence_doc',[])
        # if 'date_of_join' not in request_data:
        #     request_data['date_of_join'] = timezone_now().date()
        converted_data = {
            'aadhaar_card_photo':aadhaar_card_photo, 'aadhaar_card_id':aadhaar_card_id, 'pan_card_photo':pan_card_photo,
            'pan_card_id':pan_card_id, 'reporting_manager':reporting_manager,'insurence_doc':insurence_doc,
            "current_company" : current_company, "multitenant_manager_emp_id": request_data.get('multitenant_manager_emp_id',None),
            "multitenant_manager_company_domain" :  request_data.get('multitenant_manager_company_domain',None),
            "is_multitenant": request_data.get('is_multitenant',None), "manager_data_info" : tenant_manager_data
        }
        if work_details and isinstance(work_details,str):
            work_details = literal_eval(work_details) 
            request_data['work_details'] = work_details

        if salary_details and isinstance(salary_details,str):
            salary_details = literal_eval(salary_details)
            request_data['salary_details'] = salary_details

        if attendance_rule and isinstance(attendance_rule,str):
            attendance_rule = literal_eval(attendance_rule) 
            converted_data['attendance_rule'] = attendance_rule
            
        if pf_details and isinstance(pf_details,str):
            pf_details =  literal_eval(pf_details) 
            converted_data['pf_details'] = pf_details
            
        if emergency_details and isinstance(emergency_details,str):
            emergency_details =  literal_eval(emergency_details) 
            converted_data['emergency_details'] = emergency_details

        user_info = self.request.user.username
        
        # #handling Employee Added from status
        # ats_key = request.headers.get('X-ATS-TOKEN','')
        # if ats_key == "ATS@123":
        #     request_data['added_from'] = 'ATS'
            
        serializer = self.serializer_class(data=request_data, context={'extra_data':converted_data, 'domain':domain, 'logged_in_user': user_info, "request_obj": request})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            # add employee into ATS
        employee = Employee.objects.filter(id=serializer.data.get('id')).first()
        payload = {
            'company_id':employee.company.id,
            'emp_code': employee.work_details.employee_number,
            'emp_first_name': employee.first_name ,
            'emp_middle_name': employee.middle_name if employee.middle_name else 'Null',
            'emp_last_name': employee.last_name,
            'dept_id': employee.work_details.department_id if employee.work_details.department_id else 'Null',
            'designation_id': employee.work_details.designation_id if employee.work_details.designation_id else 'Null',
            'pernonal_email': employee.personal_email if employee.personal_email else 'Null',
            'office_email':employee.official_email
        }
        add_employee_ats(payload)
        MultitenantSetup().go_to_old_connection(request)
        return Response(serializer.data, status=status.HTTP_201_CREATED) 

class EmployeeRetrieveUpdateView(RetrieveUpdateAPIView):
    """
    View to udpate Employee information.

    AJAY, 07.01.2023
    """
    def get_serializer_context(self):
        context = super().get_serializer_context()
        user_info = self.request.user.username
        domain = f"{self.request.scheme}://{self.request.get_host()}/"
        context['logged_in_user'] = user_info
        context['user_id'] = self.request.user.employee_details.first().id
        context['domain'] = domain
        return context
    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = dir_serializers.EmployeeSerialzer
    lookup_field = "id"
    queryset = Employee.objects.all()


class EmployeeRetrieveView(ListAPIView):
    """
    View to retrieve employee using company id

    AJAY, 07.01.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = dir_serializers.EmployeeDetailSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = Employee.objects.all().select_related("work_details").order_by("-id")

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)
    
    def get(self, request, *args, **kwargs):
        # try:
        authenticated_user = request.user.is_authenticated
        MultitenantSetup().create_to_connection(request)
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context = {"authenticated_user": authenticated_user})
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(list(queryset), many=True, context = {"authenticated_user": authenticated_user})
        MultitenantSetup().go_to_old_connection(request)
        return Response(serializer.data)
        # except Exception as e:
        #     print("excaption as e", e)
        #     MultitenantSetup().go_to_old_connection(request)
        #     return Response([])
            

def future_module_run(dmn=None,request_user=None):
    sid = transaction.set_autocommit(autocommit=False)
    domain = dmn
    futures = FutureModule.objects.filter(
        status=FutureModule.QUEUE, effective_date__lte=timezone_now().date()
    )

    for module in futures:
        try:
            ct = module.content_type
            payload = module.payload
            model = apps.get_model(app_label=ct.app_label, model_name=ct.model)  #model coming
            qs: Employee = model.objects.filter(id__in=payload["id"])
            if ("manager_details" in payload and payload['manager_details'].get("reporting_manager")):
                reporting_manager_id = int(payload["manager_details"]["reporting_manager"])
                employee_ids = payload["id"]
                manager_type_first = ManagerType.objects.filter(manager_type=10).first()
                if reporting_manager_id in employee_ids: employee_ids.remove(reporting_manager_id)
                
                # company_id = Employee.objects.get(id=reporting_manager_id).company_id
                # ceo_employee = Employee.objects.filter(company_id = company_id, is_deleted = False,roles__name = 'CEO').first().id
                # data = {'ids':employee_ids,'rep_m':reporting_manager_id,'ceo':ceo_employee}
                empl_data = {'ids':employee_ids,'rep_m':reporting_manager_id}
                manager_ins = Employee.objects.filter(id=reporting_manager_id).first()
                for emp_id in employee_ids:
                    if EmployeeReportingManager.objects.filter(employee_id=emp_id, manager_id=reporting_manager_id, 
                                                               manager_type__manager_type=ManagerType.PRIMARY, is_deleted=False).exists():
                        continue
                    elif EmployeeReportingManager.objects.filter(employee_id=emp_id, manager_id=reporting_manager_id, 
                                                               manager_type__manager_type=ManagerType.SECONDARY, is_deleted=False).exists():
                        EmployeeReportingManager.objects.filter(employee_id=emp_id,
                                                                manager_type__manager_type=ManagerType.PRIMARY, 
                                                               is_deleted=False).update(is_deleted=True)
                        EmployeeReportingManager.objects.filter(employee_id=emp_id, manager_id=reporting_manager_id, 
                                                               manager_type__manager_type=ManagerType.SECONDARY, is_deleted=False).update(
                                                                manager_type = manager_type_first 
                                                               )
                    else:
                        EmployeeReportingManager.objects.filter(employee_id=emp_id,
                                                                manager_type__manager_type=ManagerType.PRIMARY, 
                                                               is_deleted=False).update(is_deleted=True)
                        EmployeeReportingManager.objects.create(
                            employee_id=emp_id, manager_id=reporting_manager_id,manager_type = manager_type_first
                        )
                        
                    hr_email = list(Employee.objects.filter(is_deleted=False,work_details__employee_status='Active',roles__name='HR',
                                                    company_id=manager_ins.company.id).values_list('official_email',flat=True))
                    
                    employee_ins = Employee.objects.filter(id=emp_id).first()
                    # email to Manager
                    try:
                        emp_designation = employee_ins.work_details.designation.name if employee_ins.work_details.designation else ''
                        man_em_id = manager_ins.work_details.employee_number
                        body=f"""
    Hello {manager_ins.user.username.title()} [{man_em_id}],

    We would like to inform you that a new employee, {employee_ins.user.username.title()} has been successfully added to your team in the HRMS system, 
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {request_user.title()},
    
    {employee_ins.user.username.title()} will be contributing to {emp_designation} We Trust they will be a valuable addition to your team.
    
    Thank you for your attention, and we appreciate your support in welcoming our new team member.
    
    Thanks & Regards,
    {employee_ins.company.company_name.title()}.
                """
                        data={
                                'subject': f'New Employee Assignment',
                                'body':body,
                                'to_email': manager_ins.official_email,
                                'cc':hr_email
                            }
                        if check_alert_notification("Employee Management",'Reporting Manager Update', email=True):
                            Util.send_email(data)
                    except Exception as e:
                        pass
                    # email to Employee
                    try:
                        emp_number = employee_ins.work_details.employee_number
                        body=f"""
    Hello {employee_ins.user.username.title()} [{emp_number}],

    We would like to inform you that a new reporting manager {manager_ins.user.username.title()}, has been assigned to you in our HRMS system, 
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {request_user.title()},
    
    {manager_ins.user.username.title()},will be overseeing your role and responsibilities moving forward. If you have any questions or need assistance during this transition, 

    please feel free to reach out to {manager_ins.user.username.title()} directly.

    We appreciate your cooperation and wish you continued success in your role under the guidance of your new reporting manager.

    Please refer the link for more information {domain}userprofile

    Thanks & Regards,
    {manager_ins.company.company_name.title()}.
                """
                        data={
                                'subject': f'New Reporting Manager Assignment',
                                'body':body,
                                'to_email': employee_ins.official_email,
                                'cc':hr_email
                            }
                        if check_alert_notification("Employee Management",'Reporting Manager Update', email=True):
                            Util.send_email(data)
                    except Exception as e:
                        pass       
                        
                        
                    
                # EmployeeReportingManager.objects.filter(
                #     manager_id = reporting_manager_id,employee__in=employee_ids,manager_type__manager_type__in = [10,20]).delete()
                
                # EmployeeReportingManager.objects.filter(employee_id=reporting_manager_id,manager_type__manager_type__in = [10,20]).delete()
                
                emp_df = pd.DataFrame(empl_data)
                
                # emp_df['is_exist'] = emp_df.ids.apply(
                # lambda a: bool(EmployeeReportingManager.objects.filter(
                #     employee_id=a,manager_type__manager_type=10,is_deleted=False
                #     ).exists()))
                # emp_df.apply(lambda obj:EmployeeReportingManager.objects.filter(
                #         employee_id=obj['ids'],manager_type__manager_type=10,is_deleted=False
                #         ).update(manager_id = obj['rep_m']) if obj['is_exist'] else EmployeeReportingManager.objects.get_or_create(
                #             employee_id=obj['ids'], manager_id=obj['rep_m'],manager_type = manager_type_first
                #         ),axis=1)
                
                # emp_df.apply(lambda obj:EmployeeReportingManager.objects.get_or_create(employee_id = obj['rep_m'],
                #                                         manager_id = obj['ceo'],manager_type = manager_type_first),axis=1)
            
                # all_emps = list(EmployeeReportingManager.objects.filter(
                #     manager_id=ceo_employee,manager_type__manager_type = 10).values_list('employee',flat=True))        
                        
                # emp_rep_ceo = {'emps_1':all_emps}
                # new_emp_df = pd.DataFrame(emp_rep_ceo)
                # EmployeeReportingManager.objects.filter(employee_id = ceo_employee).delete()
                # new_emp_df.emps_1 = new_emp_df.emps_1.apply(lambda emp :'' if EmployeeReportingManager.objects.filter(manager_id = emp).exists() else 
                #                 EmployeeReportingManager.objects.filter(employee_id = emp).delete())
                
                current_date = timezone_now()
                # emp_df.apply(lambda obj: ''
                #                     if EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],manager_id=obj['rep_m'], work_to__isnull=True).exists()
                #                     else EmployeeWorkHistoryDetails.objects.get_or_create(employee_id=obj['ids'], manager_id=obj['rep_m'], work_from=current_date), axis=1 )
                # emp_df['manager_ids'] = emp_df.apply(lambda obj:
                #                     list(EmployeeReportingManager.objects.filter(employee_id=obj['ids'], is_deleted=False).values_list('manager_id',flat=True)), axis=1)                   
                # emp_df.apply(lambda obj:
                #    EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],work_to__isnull=True,department__isnull=True).exclude(manager_id__in =obj['manager_ids']).update(work_to=timezone_now()), axis=1)     
                m_type = "Primary"
                emp_df.apply(lambda obj: EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],manager_id=obj['rep_m'], work_to__isnull=True, work_from__date=current_date.date()).update(manager_type=m_type) 
                                    if EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],manager_id=obj['rep_m'], work_to__isnull=True, work_from__date=current_date.date()).exists()
                                    else (EmployeeWorkHistoryDetails.objects.get_or_create(employee_id=obj['ids'], manager_id=obj['rep_m'], work_from=current_date, manager_type=m_type),
                                        EmployeeWorkHistoryDetails.objects.filter(Q(employee_id=obj['ids'],manager_id=obj['rep_m'], work_to__isnull=True), ~Q(manager_type=m_type)).update(work_to=current_date)), axis=1)
                emp_df['manager_ids'] = emp_df.apply(lambda obj:
                                    list(EmployeeReportingManager.objects.filter(employee_id=obj['ids'], is_deleted=False).values_list('manager_id',flat=True)), axis=1)                   
                emp_df.apply(lambda obj:
                    EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],work_to__isnull=True,department__isnull=True).exclude(manager_id__in =obj['manager_ids']).update(work_to=timezone_now()), axis=1)      
                  
            if 'work_details' in payload and payload['work_details'].get('department',''):
                e_ids = payload.get('id')
                dep_id =  payload['work_details'].get('department')
                dep_df = pd.DataFrame(e_ids,columns=['e_ids']) 
                dep_df['dep_id'] = dep_id 
                if len(dep_df) !=0:
                    dep_df.apply(lambda obj: ''
                                    if EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['e_ids'],department_id=obj['dep_id'], work_to__isnull=True).exists()
                                    else EmployeeWorkHistoryDetails.objects.get_or_create(employee_id=obj['e_ids'],department_id=obj['dep_id'], work_from=timezone_now()), axis=1 )
                    
                    dep_df.apply(lambda obj: EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['e_ids'],department_id__isnull=False, work_to__isnull=True
                                                                                       ).exclude(department_id=obj['dep_id']).update(work_to=timezone_now()), axis=1)      
            for instance in qs:
                serializer = load_class(module.serializer)(
                    instance=instance, data=payload, partial=True, context={'domain':domain, 'logged_in_user':request_user}
                )
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                module.status = FutureModule.SUCCESS

        except Exception:
            traceback.print_exc()
            module.logs = traceback.format_exc()
            module.status = FutureModule.FAIL

        module.save()

    transaction.commit()
    

class EmployeeBulkUpdateView(ListCreateAPIView):
    serializer_class = dir_serializers.EmployeeSerialzer

    def get_queryset(self):
        return Employee.objects.filter(id__in=self.request.data["id"]).select_related(
            "work_details"
        )

    def post(self, request, *args, **kwargs):
        data = request.data
        effective_date = data.pop("effective_date", timezone_now().date())
        env = "local"
        
        payload = {
            "serializer": (
                f"{dir_serializers.EmployeeSerialzer.__module__}."
                f"{dir_serializers.EmployeeSerialzer.__qualname__}"
            ),
            "effective_date": effective_date,
            "payload": data,
            "content_type": ContentType.objects.get_for_model(Employee),
        }
        FutureModule.objects.create(**payload)
        if datetime.datetime.strftime(datetime.datetime.now().date(), "%d-%m-%Y") == effective_date:
            # TODO when implement the environments settings module should change
            # subprocess.run(f"python manage.py run_future_modules --commit --settings=HRMSProject.settings.{env}", shell=True)
            if ("manager_details" in request.data and request.data['manager_details'].get("reporting_manager")):
                reporting_manager_id = int(request.data["manager_details"]["reporting_manager"])
                employee_ids = request.data["id"]
                rep_man_info = Employee.objects.filter(id=reporting_manager_id).select_related('company').first()
                
                # if not Employee.objects.filter(roles__name = 'CEO',company_id = rep_man_info.company_id,is_deleted=False).exists():
                #     return response.Response(
                #         {
                #             'error': f"{rep_man_info.company.company_name} company does't have a CEO "
                #         },
                #         status=status.HTTP_400_BAD_REQUEST
                #     )
                    
                if Employee.objects.filter(roles__name = 'EMPLOYEE',id = reporting_manager_id).exists():
                    return response.Response(
                        {
                            'error': "Employee can't be assigned as Reporing manager"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if Employee.objects.filter(roles__name = 'CEO',id__in = employee_ids).exists():
                    return response.Response(
                        {
                            'error': "Reporting manager can't be assigned for CEO"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # if Employee.objects.filter(roles__name = 'CEO',id = reporting_manager_id).exists():
                #     return response.Response(
                #         {
                #             'error': "CEO can't be assigned as the Reporting manager explicitly"
                #         },
                #         status=status.HTTP_400_BAD_REQUEST
                #     )
                # if EmployeeReportingManager.objects.filter(manager_id__in=employee_ids, is_deleted=False, manager_type__manager_type = 10).exists():
                #     return response.Response(
                #         {
                #             'error': "employee is already a primary manager"
                #         },
                #         status=status.HTTP_400_BAD_REQUEST
                #     )
                if EmployeeReportingManager.objects.filter(manager_id__in=employee_ids, is_deleted=False, employee_id=reporting_manager_id).exists():
                    return response.Response(
                        {
                            'error': "Reporter can't be your reporting manager"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            user_domain = f"{self.request.scheme}://{self.request.get_host()}/" 
            request_user = self.request.user.username   
            future_module_run(dmn=user_domain,request_user=request_user)
        return Response(
            status=status.HTTP_200_OK,
            data={
                "status": status.HTTP_200_OK,
                "message": "Employees update information saved successfully",
                "data": {},
            },
        )


class EmployeeImportView(APIView):
    """
    View to create Employee from the file

    AJAY, 21.01.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    model = Employee
    serializer_class = dir_serializers.EmployeeImportSerializer

    def post(self, request, *args, **kwargs):
        name = request.FILES["employee_file"]._name
        try:
            if name.split('.')[1].lower() not in ['xlsx', 'csv']:
                return Response(
                    {"data": {"status": "File Format is Incorrect"}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                    {"data": {"status": e}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        
        if serializer.is_valid():

            serializer.save()
            return Response(
                status=status.HTTP_201_CREATED,
                data={
                    "status": status.HTTP_201_CREATED,
                    "message": "Employees successfully created",
                    "data": [],
                },
            )

        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "Contact system admin",
                "data": serializer.errors,
            },
        )


class EmployeeReportingManagerCreateView(CreateAPIView):
    """
    View to create Employee Reporting Manager

    SURESH, 17.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeReportingManagerSerializer
    detailed_serializer_class = EmployeeReportingManagerDetailSerializer
    queryset = EmployeeReportingManager.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['domain'] = f"{self.request.scheme}://{self.request.get_host()}/"
        user_info = self.request.user.username
        context['logged_in_user'] = user_info
        return context
    
    def post(self, request, *args, **kwargs):
        data = request.data
        employee_id = int(data.get("employee"))
        manager_id = int(data.get("manager", 0))
        # MultitenantSetup().create_to_connection(request)
        employee_info = Employee.objects.filter(id=employee_id).select_related('company').first()
        

        if (str(data.get("employee")) == str(manager_id)) or (
            employee_info.work_details.employee_number == data.get('multitenant_manager_emp_id', '')
        ):
            return response.Response(
                {
                    'message': 'An employee cannot report to themselves.Please Select Correct Reporting Manager'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        """         emp_query = EmployeeReportingManager.objects.filter(employee=data["employee"],
                                                            manager_type_id__in=[1, 2],
                                                            
                                                            is_deleted=False
                                                            ).filter(db_models.Q(manager=manager_id) | db_models.Q(multitenant_manager_emp_id=data.get('multitenant_manager_emp_id')))
        if emp_query.exists():
            emp_fullname = emp_query.annotate(
                emp = db_models.Case(
                    db_models.When(
                        manager__isnull=True,
                        then=db_models.F('multitenant_manager_name')
                    ),
                    default=db_models.F('manager__user__username'),
                    output_field=db_models.CharField()
                )
            ).values('emp').first()
            
            emp_name = emp_fullname['emp']
        """
        emp_query = EmployeeReportingManager.objects.filter(employee=data["employee"],
                                                            manager_type_id__in=[1, 2],
                                                            is_deleted=False,
                                                            manager=manager_id)
        if emp_query.exists():
            manager_type = emp_query.first().manager_type.get_manager_type_display()
            emp_name = emp_query.first().manager.user.username
            return response.Response(
                {
                    'message': f"{emp_name} already reported as a {manager_type} manager"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        # if not Employee.objects.filter(roles__name = 'CEO',company_id = employee_info.company_id,is_deleted=False).exists():
        #     return response.Response(
        #         {
        #             'message': f"{employee_info.company.company_name} company does't have a CEO "
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        
        if Employee.objects.filter(roles__name = 'EMPLOYEE',id = manager_id).exists():
            return response.Response(
                {
                    'message': "Employee can't be assigned as Reporing manager"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
                
        if Employee.objects.filter(roles__name = 'CEO',id = employee_id).exists():
            return response.Response(
                {
                    'message': "Reporting manager can't be assigned for CEO"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # if Employee.objects.filter(roles__name = 'CEO',id = manager_id).exists():
        #     return response.Response(
        #         {
        #             'message': "CEO can't be assigned as the Reporting manager explicitly"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        
        if int(data['manager_type']) == 2 and EmployeeReportingManager.objects.filter(
            manager__work_details__employee_number=employee_info.work_details.employee_number,
            is_deleted=False ,manager_type_id=2).exists():
            return response.Response(
                {
                    'message': "Secondary manager can't be assigned for secondary manager"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # if EmployeeReportingManager.objects.filter(manager=data['employee'], is_deleted=False, manager_type_id=1).exists():
        #     return response.Response(
        #         {
        #             'message': "employee is already a primary manager"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        
        if EmployeeReportingManager.objects.filter(manager_id=data['employee'], is_deleted=False, employee_id=manager_id).exists():
                    return response.Response(
                        {
                            'error': "Reporter can't be your reporting manager"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
        if data.get('manager_type') == '1':
            if EmployeeReportingManager.objects.filter(employee=data['employee'], is_deleted=False, manager_type_id=1).exists():
                return response.Response(
                    {
                        'message': "Multiple primary managers can not be assign"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        return self.create(request, *args, **kwargs)


class EmployeeReportingManagerUpdateView(RetrieveUpdateDestroyAPIView):
    """
    View to update Employee Reporting Manager

    SURESH, 17.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeReportingManagerSerializer
    detailed_serializer_class = EmployeeReportingManagerDetailSerializer
    lookup_field = "id"
    queryset = EmployeeReportingManager.objects.all()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['domain'] = f"{self.request.scheme}://{self.request.get_host()}/"
        user_info = self.request.user.username
        context['logged_in_user'] = user_info
        return context
    
    def put(self, request, *args, **kwargs):
        data = request.data
        instance = self.get_object()

        if data.get("employee") == data.get("manager"):
            return response.Response(
                {
                    'message': 'An employee cannot report to themselves.Please Select Correct Reporting Manager'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        # if EmployeeReportingManager.objects.filter(manager=data['employee'], is_deleted=False, manager_type_id=1).exists():
        #     return response.Response(
        #         {
        #             'message': "employee is already primary manager"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        emp_query = EmployeeReportingManager.objects.filter(employee=data["employee"], manager_type_id__in=[1, 2], manager=data['manager'], is_deleted=False).exclude(id=instance.id)
        if emp_query.exists():
            emp_fullname = emp_query.annotate(
                emp = Concat(F('manager__first_name'),
                             Value(' '),
                             F('manager__middle_name'),
                             Value(' '),
                             F('manager__last_name'))
                             ).values('emp').first()
            
            emp_name = emp_fullname['emp']
            manager_type = emp_query.first().manager_type.get_manager_type_display()
            return response.Response(
                {
                    'message': f"{emp_name} already reported as a {manager_type} manager"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        if EmployeeReportingManager.objects.filter(manager_id=data['employee'], is_deleted=False, employee_id=data["manager"]).exists():
            return response.Response(
                        {
                            'error': "Reporter can't be your reporting manager"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
        if data.get('manager_type') == '1':
            if EmployeeReportingManager.objects.filter(employee=data['employee'], is_deleted=False, manager_type_id=1).exists():
                return response.Response(
                    {
                        'message': "multiple primary managers can not be assign"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        return self.update(request, *args, **kwargs)
    def delete(self, request, id):
        manager_qs = EmployeeReportingManager.objects.filter(id=id).select_related('manager_type')
        # if manager_qs.first().manager_type.manager_type == 10:
        #     emp_qs = EmployeeReportingManager.objects.filter(manager_id = manager_qs.first().manager_id,manager_type__manager_type = 10)
        #     if emp_qs.count() == 1:
        #         EmployeeReportingManager.objects.filter(employee_id = manager_qs.first().manager_id).delete()
        EmployeeWorkHistoryDetails.objects.filter(employee_id=manager_qs.first().employee_id, manager_id=manager_qs.first().manager_id, work_to__isnull=True).update(work_to=timezone_now())
        manager_qs.update(is_deleted=True)
        return response.Response(
            {
                'message': 'Employee Reporting manager deleted Successfully'
            },
            status=status.HTTP_200_OK
        )


class EmployeeReportingManagerRetrieveView(ListAPIView):
    """
    View to retrieve Employee Reporting Manager

    SURESH, 17.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeReportingManagerDetailSerializer
    lookup_field = "employee"
    lookup_url_kwarg = "employee_id"
    queryset = EmployeeReportingManager.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)

class ManagerEmployeeDetails(APIView):
    model = EmployeeReportingManager
    
    def get(self, request):
        manager_id = request.query_params.get('id')
        qs = self.model.objects.filter(manager_id=manager_id, is_deleted=False).select_related('employee', 'manager_type').annotate(
            employee_name=Concat(F('employee__first_name'), Value(' '), F('employee__middle_name'), F('employee__last_name')),
            type_of_manager=Case(
                When(manager_type__manager_type=10, then=Value('Primary Manager')),
                When(manager_type__manager_type=20, then=Value('Secondary Manager')),
                default=Value(''),
                output_field=CharField()
            )
            ).values('employee_name', 'type_of_manager',
                    'employee__work_details__department__name', 
                    'employee__work_details__designation__name')
        return Response(
            {
                "is_manager": True if qs.exists() else False,
                "data": qs
            },
            status=status.HTTP_200_OK
        )

class EmployeeEducationDetailsCreateView(CreateAPIView):
    """
    View to create Employee Education

    SURESH, 16.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeEducationSerializer
    detailed_serializer_class = EmployeeEducationDetailSerializer
    queryset = EmployeeEducationDetails.objects.all()

    def post(self,request, *args, **kwargs):
        data=request.data
        qs = EmployeeEducationDetails.objects.filter(
            employee = data.get("employee"),
            qualification = data.get('qualification'),
            is_deleted = False
        ).exclude(qualification__qualification_type__in=[70,60])
        if qs.exists():
            return Response(
                {
                    "message" : "Employee already have this Qualification Type"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return self.create(request, *args, **kwargs)


class EmployeeEducationDetailsUpdateView(RetrieveUpdateDestroyAPIView):
    """
    View to update Employee Education

    SURESH, 16.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeEducationSerializer
    detailed_serializer_class = EmployeeEducationDetailSerializer
    lookup_field = "id"
    queryset = EmployeeEducationDetails.objects.all()

    def patch(self, request, *args, **kwargs):
        data=request.data
        if data.get("is_deleted"):
            obj = get_object_or_404(EmployeeEducationDetails, id=kwargs.get('id'))
            obj.is_deleted = True
            obj.save()
            return Response(
                {
                    'message': 'Deleted Successfully'
                },
                status=status.HTTP_200_OK
            )
        qs = EmployeeEducationDetails.objects.filter(
            employee = data.get("employee"),
            qualification = data.get('qualification'),
            is_deleted = False
        ).exclude(Q(id=kwargs.get('id')) | Q(qualification__qualification_type__in=[70,60]))
        if qs.exists():
            return Response(
                {
                    "message" : "Employee already have this Qualification Type"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return self.update(request, *args, **kwargs)

class EmployeeEducationDetailsRetrieveView(ListAPIView):
    """
    View to retrieve Employee Education

    SURESH, 16.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeEducationDetailSerializer
    lookup_field = "employee"
    lookup_url_kwarg = "employee_id"
    queryset = EmployeeEducationDetails.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


class EmployeeFamilyDetailsCreateView(CreateAPIView):
    """
    View to create Employee Family Details

    16.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeFamilySerializer
    detailed_serializer_class = EmployeeFamilyDetailSerializer
    queryset = EmployeeFamilyDetails.objects.all()
    
    def post(self, request, *args, **kwargs):
        data = request.data
        qs = EmployeeFamilyDetails.objects.filter(
            employee = data.get("employee"),
            relationship = data.get("relationship"),
            is_deleted=False
        ).exclude(relationship_id__in=[5,6,7,8,9])
        if qs.exists():
            return Response(
                {
                    'message': 'Employee have already record with this relation'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return self.create(request, *args, **kwargs)


class EmployeeFamilyDetailsUpdateView(RetrieveUpdateDestroyAPIView):
    """
    View to update Employee Family Details

    16.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeFamilySerializer
    detailed_serializer_class = EmployeeFamilyDetailSerializer
    lookup_field = "id"
    queryset = EmployeeFamilyDetails.objects.all()
    
    def patch(self, request, *args, **kwargs):
        data=request.data
        if data.get('is_deleted'):
            obj = get_object_or_404(EmployeeFamilyDetails, id=kwargs.get('id'))
            obj.is_deleted = True
            obj.save()
            return Response(
                {
                    'message': 'Deleted Successfully'
                },
                status=status.HTTP_200_OK
            )
        qs = EmployeeFamilyDetails.objects.filter(
            employee = data.get("employee"),
            relationship = data.get("relationship"),
            is_deleted=False
        ).exclude(Q(id=kwargs.get('id')) | Q(relationship_id__in=[5,6,7,8,9]))
        if qs.exists():
            return response.Response(
                {
                    'message': 'Employee have already record with this relation'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return self.update(request, *args, **kwargs)
    
    # def delete(self, request, id):
    #     qs = EmployeeFamilyDetails.objects.filter(id=id)
    #     if not qs.exists():
    #         return response.Response(
    #             {
    #                 'message': "Details not found"
    #             },
    #             status=status.HTTP_404_NOT_FOUND
    #         )
    #     qs.delete()
    #     return response.Response(
    #         {
    #             'message': 'Deleted Successfully'
    #         },
    #         status=status.HTTP_200_OK
    #     )



class EmployeeFamilyDetailsRetrieveView(ListAPIView):
    """
    View to retrieve Employee Family Details

    SURESH, 16.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeFamilyDetailSerializer
    lookup_field = "employee"
    lookup_url_kwarg = "employee_id"
    queryset = EmployeeFamilyDetails.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


class EmployeeEmergencyContactCreateView(CreateAPIView):
    """
    View to create Employee Emergency Contact

    SURESH, 16.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeEmergencyContactSerializer
    detailed_serializer_class = EmployeeEmergencyContactDetailSerializer
    queryset = EmployeeEmergencyContact.objects.all()

    def post(self, request, *args, **kwargs):
        data=request.data
        qs = EmployeeEmergencyContact.objects.filter(
            employee = data.get("employee"),
            phone_number = data.get("phone_number"),
            is_deleted=False,
        )
        if qs.exists():
            return Response(
                {
                    'message': 'Employee have already record with this Phone number'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        qs = EmployeeEmergencyContact.objects.filter(
            employee = data.get("employee"),
            relationship = data.get("relationship"),
            is_deleted=False,
        ).exclude(relationship_id__in=[5,6,7,8,9])
        if qs.exists():
            return Response(
                {
                    'message': 'Employee have already record with this relation'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return self.create(request, *args, **kwargs)



class EmployeeEmergencyContactUpdateView(RetrieveUpdateDestroyAPIView):
    """
    View to update Employee Emergency Contact

    SURESH, 16.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeEmergencyContactSerializer
    detailed_serializer_class = EmployeeEmergencyContactDetailSerializer
    lookup_field = "id"
    queryset = EmployeeEmergencyContact.objects.all()

    def patch(self, request, *args, **kwargs):
        data = request.data
        if data.get('is_deleted'):
            obj = get_object_or_404(EmployeeEmergencyContact, id=kwargs.get('id'))
            obj.is_deleted = True
            obj.save()
            return Response(
                    {
                        'message': 'Deleted Successfully'
                    },
                    status=status.HTTP_200_OK
                )
        qs = EmployeeEmergencyContact.objects.filter(
            employee = data.get("employee"),
            phone_number = data.get("phone_number"),
            is_deleted=False,
        ).exclude(Q(id=kwargs.get('id'))|Q(relationship_id__in=[5,6,7,8,9]))
        if qs.exists():
            return Response(
                {
                    'message': 'Employee have already record with this Phone number'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        qs = EmployeeEmergencyContact.objects.filter(
            employee = data.get("employee"),
            relationship = data.get("relationship"),
            is_deleted=False,
        ).exclude(Q(id=kwargs.get('id'))|Q(relationship_id__in=[5,6,7,8,9]))
        if qs.exists():
            return Response(
                {
                    'message': 'Employee have already record with this relation'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return self.update(request, *args, **kwargs)



class EmployeeEmergencyContactRetrieveView(ListAPIView):
    """
    View to retrieve Employee Emergency Contact

    SURESH, 16.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeEmergencyContactDetailSerializer
    lookup_field = "employee"
    lookup_url_kwarg = "employee_id"
    queryset = EmployeeEmergencyContact.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


class EmployeeDocumentsCreateView(CreateAPIView):
    """
    View to create Employee Document

    ASLAM, 17.01.2022
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeDocumentsSerializer
    detailed_serializer_class = EmployeeDocumentsDetailSerializer
    queryset = EmployeeDocuments.objects.all()
    
    def post(self, request, *args, **kwargs):
        MultitenantSetup().create_to_connection(request)
        data = request.data
        print("data here", data)
        if self.queryset.filter(employee_id=data.get('employee'), document_type_id=data.get("document_type"), is_deleted=False).exists():
            message = 'Document type already added'
            return Response(
                    error_response(message,message, 400),
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        MultitenantSetup().go_to_old_connection(request)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class EmployeeDocumentsUpdateView(UpdateAPIView):
    """
    View to update Employee Document

    ASLAM, 17.01.2022
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeDocumentsSerializer
    detailed_serializer_class = EmployeeDocumentsDetailSerializer
    lookup_field = "id"
    queryset = EmployeeDocuments.objects.all()
    
    def put(self, request, *args, **kwargs):
        data = request.data
        if self.queryset.filter(employee_id=data.get('employee'), document_type_id=data.get("document_type"), is_deleted=False).exclude(id=kwargs.get('id')).exists():
            return response.Response(
                {
                    "error": "Document type already added."
                }
            )
        return super().put(request, *args, **kwargs)


class EmployeeDocumentsRetrieveView(ListAPIView):
    """
    View to retrieve Employee Document

    ASLAM, 17.01.2022
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeDocumentsDetailSerializer
    lookup_field = "employee"
    lookup_url_kwarg = "employee_id"
    queryset = EmployeeDocuments.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


class EmployeeCertificationsCreateView(CreateAPIView):
    """
    View to create Employee Certifications

    SURESH, 17.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeCertificationsSerializer
    detailed_serializer_class = EmployeeCertificationsDetailSerializer
    queryset = EmployeeCertifications.objects.all()


class EmployeeCertificationsUpdateView(UpdateAPIView):
    """
    View to update Employee Certifications

    SURESH, 17.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeCertificationsSerializer
    detailed_serializer_class = EmployeeCertificationsDetailSerializer
    lookup_field = "id"
    queryset = EmployeeCertifications.objects.all()


class EmployeeCertificationsRetrieveView(ListAPIView):
    """
    View to retrieve Employee Certifications

    SURESH, 17.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeCertificationsDetailSerializer
    lookup_field = "employee"
    lookup_url_kwarg = "employee_id"
    queryset = EmployeeCertifications.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


class EmployeeDocumentationWorkCreateView(CreateAPIView):
    """
    View to create Employee Certifications

    SURESH, 17.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeDocumentationWorkSerializer
    detailed_serializer_class = EmployeeDocumentationWorkDetailSerializer
    queryset = EmployeeDocumentationWork.objects.all()


class EmployeeDocumentationWorkUpdateView(UpdateAPIView):
    """
    View to update Employee Certifications

    SURESH, 17.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeDocumentationWorkSerializer
    detailed_serializer_class = EmployeeDocumentationWorkDetailSerializer
    lookup_field = "id"
    queryset = EmployeeDocumentationWork.objects.all()


class EmployeeDocumentationWorkRetrieveView(ListAPIView):
    """
    View to retrieve Employee Certifications

    SURESH, 17.01.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeDocumentationWorkDetailSerializer
    lookup_field = "employee"
    lookup_url_kwarg = "employee_id"
    queryset = EmployeeDocumentationWork.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


class ChatBotEmployeeDetailsAPIView(APIView):
    
    """
    Temporary View Class
    """
    
    authentication_classes = ()
    permission_classes = ()
    
    def get(self, request):
        query_params = request.query_params
        email = query_params.get('email')
        data = Employee.objects.filter(user__email=email).annotate(
                employee_name=Concat(F('first_name'), Value(' '), F('middle_name'), Value(' '), F('last_name'))
            ).values('employee_name', 'phone', 'user__email')
        return Response(
            data,
            status=status.HTTP_200_OK
        )

class ChatboatEmployeePayrollInformation(APIView):
    """
    Temporary View Class
    for now year is fixed need to update
    """
    authentication_classes = ()
    permission_classes = ()
    
    def get(self, request):
        query_params = request.query_params
        email = query_params.get('email')
        month = query_params.get('month')
        year = 2023
        employee = Employee.objects.filter(
            user__email=email
            ).first().emp_payroll_info.select_related('employee').filter(
                month_year__month=month,
                month_year__year=year
                ).annotate(
                    employee_name=Concat(F('employee__first_name'), Value(' '), F('employee__middle_name'), Value(' '), F('employee__last_name'))
                ).values(
                    'employee_name', 'month_year', 'earned_gross', 'e_basic', 'e_hra', 'e_conv', 'e_special_allow'
                )
        return Response(
            employee,
            status=status.HTTP_200_OK
        )
        
class EmployeeWorkHistoryDetailsRetriveView(APIView):
    model = EmployeeWorkHistoryDetails
    
    def get(self,request):
        # employee_id = request.user.employee_details.first().id
        # get reporting manager details
        employee_id = request.query_params.get('emp_id')
        main_records = list(EmployeeWorkHistoryDetails.objects.filter(is_deleted=False,employee_id=employee_id,department__isnull=True).annotate(
            manager_name = F('manager__user__username'),
            ).values('id','manager_name','work_from__date','work_to__date','manager_type').order_by('work_to__date'))
        rem_df = dep_df=pd.DataFrame()
        rem_combined_records = []
        for obj in main_records:
            changed_records = f"Reporting Manager - {obj['manager_name']}" if obj['manager_type'] is None else f"Reporting Manager - {obj['manager_name']} ({obj['manager_type']})"
            rem_combined_records.append({
                    "id": obj["id"],
                    "work_from": obj["work_from__date"],
                    "work_to": obj["work_to__date"],
                    "changed_records": changed_records,
            })
        """
        i = 0
        while i < len(rem_records):
            current_record = rem_records[i]
            rep_man = current_record["manager_name"]
            m_type = current_record['manager_type']
            i += 1

            if i < len(rem_records) and current_record["work_to__date"] == rem_records[i]["work_from__date"]:
                rep_man = f"Reporting Manager changed from {rep_man}({m_type}) to {rem_records[i]['manager_name']} ({rem_records[i]['manager_type']})"
                i += 1

            if current_record["work_to__date"] is None:
                rm_man = f"Reporting Manager - {current_record['manager_name']} ({current_record['manager_type']})"
                rem_combined_records.append({
                    "id": current_record["id"],
                    "work_from": current_record["work_from__date"],
                    "work_to": '',
                    "changed_records": rm_man,
                })
            else:
                if "Reporting Manager changed" not in rep_man:
                    rep_man = f"Reporting Manager - {rep_man} ({m_type})" 
                rem_combined_records.append({
                    "id": current_record["id"],
                    "work_from": current_record["work_from__date"],
                    "work_to": current_record["work_to__date"] if current_record["work_to__date"] is not None else '',
                    "changed_records": rep_man,
                })
        """
        if rem_combined_records:
            rem_df = pd.DataFrame(rem_combined_records, columns=["id","work_from","work_to","changed_records"])
            
        # get Department names
        dep_records = list(EmployeeWorkHistoryDetails.objects.filter(is_deleted=False,employee_id=employee_id,manager__isnull=True).annotate(
            department_name = F('department__name')
            ).values('id','department_name','work_from__date','work_to__date').order_by('id'))
        dep_combined_records = []
        for obj in dep_records:
            dep_combined_records.append({
                    "id": obj["id"],
                    "work_from": obj["work_from__date"],
                    "work_to": obj["work_to__date"],
                    "changed_records": f"Department - {obj['department_name']}",
            })
        """
        i = 0
        while i < len(dep_records):
            current_record = dep_records[i]
            dep_name = current_record["department_name"]

            i += 1

            if i < len(dep_records) and current_record["work_to__date"] == dep_records[i]["work_from__date"]:
                dep_name = f"Department changed from {dep_name} to {dep_records[i]['department_name']}"
                i += 1

            if current_record["work_to__date"] is None:
                dept_name = f"Department - {current_record['department_name']}"
                dep_combined_records.append({
                    "id": current_record["id"],
                    "work_from": current_record["work_from__date"],
                    "work_to": '',
                    "changed_records": dept_name,
                })
            else:
                if "Department changed" not in dep_name:
                   dep_name = f"Department - {dep_name}" 
                dep_combined_records.append({
                    "id": current_record["id"],
                    "work_from": current_record["work_from__date"],
                    "work_to": current_record["work_to__date"] if current_record["work_to__date"] is not None else '',
                    "changed_records": dep_name,
                })
        """
        if dep_combined_records:
            dep_df = pd.DataFrame(dep_combined_records, columns=["id","work_from","work_to","changed_records"])
        
        final_df = pd.concat([rem_df, dep_df], ignore_index=True)
        if not final_df.empty:  
            final_df.sort_values(by='id', ascending=False, inplace=True)  
                    
        return Response(
                    success_response(final_df.to_dict('records'), "Successfully fetched Employee Work History Details", 200),
                    status=status.HTTP_200_OK
                )

class GetLastWorkingDay(APIView):
    model = Employee
    def get(self, request, *args, **kwargs):
        try:
            resign_date = request.query_params.get('date')
            notice_period = request.query_params.get('notice_period',0)
            user_info = request.user.employee_details.first()
            company_id = user_info.company_id
            employee_id = request.query_params.get('emp_id')
            final_day = datetime.datetime.strptime(resign_date, "%d/%m/%Y") + datetime.timedelta(days=int(notice_period))
            p = True
            while p:
                if Holidays.objects.filter(company_id=company_id,holiday_date=final_day).exists():
                    final_day = final_day - datetime.timedelta(days=1)
                else:
                    p = False 
            query = Employee.objects.filter(id=employee_id,
                    employeeworkrulerelation__work_rule__work_rule_choices__week_number=get_month_weeks(
                        final_day)[final_day.day]).annotate(
                            work_week_details =
                                db_models.expressions.Func(
                                    db_models.Value('tuesday'), "employeeworkrulerelation__work_rule__work_rule_choices__tuesday",
                                    db_models.Value('wednesday'), "employeeworkrulerelation__work_rule__work_rule_choices__wednesday",
                                    db_models.Value('thursday'), "employeeworkrulerelation__work_rule__work_rule_choices__thursday",
                                    db_models.Value('friday'), "employeeworkrulerelation__work_rule__work_rule_choices__friday",
                                    db_models.Value('saturday'), "employeeworkrulerelation__work_rule__work_rule_choices__saturday",
                                    db_models.Value('sunday'), "employeeworkrulerelation__work_rule__work_rule_choices__sunday",
                                    db_models.Value('monday'), "employeeworkrulerelation__work_rule__work_rule_choices__monday",
                                function="jsonb_build_object",
                                    output_field=db_models.JSONField()
                                )).values('work_week_details')
            if not query.exists():
                msg = "Please assign work week"
                return Response(
                    error_response(msg,msg, 400),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            wd = query.first()['work_week_details']
            final_termination_date = get_terminations_date(wd,final_day).date().strftime("%d/%m/%Y")
            result = {'last_working_day':final_termination_date}  
            return Response(
                    success_response(result, "Last Working Day Fetched Successfully", 200),
                    status=status.HTTP_200_OK
                )
        except Exception as e:
                return Response(
                    error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                    status=status.HTTP_400_BAD_REQUEST,
                )
class ExperienceAPIView(APIView):
    model = EmployeeExperienceDetails
    serializer_class = PastExperienceDetailserializer
    pagination_class = CustomPagePagination

    def get(self,request):
        employee_id = request.query_params.get('employee_id')
        paginator = self.pagination_class()
        q_filter =db_models.Q(employee_id=employee_id, is_deleted=False)
        query = self.model.objects.filter(q_filter).values('id','employee','company_name','designation','from_date','to_date','experience','company_url').order_by('-id')
        page = paginator.paginate_queryset(query, request)
        return Response(
                success_response(
                    paginator.get_paginated_response(page), "Successfully fetched Saving declaration Data", 200
                ),
                status=status.HTTP_200_OK
            )

    def post(self, request):
        request_data = request.data
        # from_date = datetime.datetime.strptime(request_data.get('from_date'),"%d-%m-%Y")
        # to_date = datetime.datetime.strptime(request_data.get('to_date'),"%d-%m-%Y")
        # experience = round((to_date-from_date).days / 365.25 , 1)
        # request_data['experience'] = experience
        serializer = PastExperienceDetailserializer(data=request_data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request, *args, **kwargs):
        request_data = request.data
        emp_id = request_data.get('id')
        # from_date = datetime.datetime.strptime(request_data.get('from_date'),"%d-%m-%Y")
        # to_date = datetime.datetime.strptime(request_data.get('to_date'),"%d-%m-%Y")
        # experiences = round((to_date-from_date).days / 365.25 , 1)       
        # request_data['experience'] = experiences
        obj = get_object_or_404(self.model, id=emp_id)
        serializer=PastExperienceDetailserializer(obj, data=request_data, context={'obj_id':emp_id},partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    
    def delete(self, request,*args, **kwargs):
        id = kwargs.get('employee_id')
        try:
            obj = self.model.objects.get(id=id)
            obj.is_deleted = True
            obj.save()           
            return response.Response(
            {
                'message': 'Employee Experience Deleted Successfully'
            },
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(str(e), 'Some thing went wrong', 404),
                status=status.HTTP_404_NOT_FOUND
            )
        
""" 
class HealthInsuranceAPIView(APIView):
    model = HealthInsurence
    serializer_class = HealthInsuranceSerializer
    pagination_class = CustomPagePagination

    def get(self, request, *args, **kwargs):
        employee_id = request.query_params.get('employee_id')
        paginator = self.pagination_class()
        q_filter = db_models.Q(employee_id=employee_id, is_deleted=False)
        query = self.model.objects.filter(q_filter).values('id','employee','health_insurence','insurence_date','insurence_file','nominee_name','nominee_relationship','nominee_date_of_birth').order_by('-id')
        page = paginator.paginate_queryset(query, request)
        return Response(
                success_response(
                    paginator.get_paginated_response(page), "Successfully fetched health insurence Data", 200
                ),
                status=status.HTTP_200_OK
            )

    def post(self,request):
        
            request_data = request.data
            serializer = HealthInsuranceSerializer(data=request_data)
            if serializer.is_valid(raise_exception=True):
               serializer.save()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    def patch(self, request, *args, **kwargs):
        
           request_data = request.data
           emp_id = request_data.get('id')
           obj = get_object_or_404(self.model, id=emp_id)
           serializer = HealthInsuranceSerializer(obj, data=request_data, partial=True)
           if serializer.is_valid(raise_exception=True):
              serializer.save()
           return Response(serializer.data, status=status.HTTP_201_CREATED)
    def delete(self, request,*args, **kwargs):
        id = kwargs.get('employee_id')
        try:
            obj = self.model.objects.get(id=id)
            obj.is_deleted = True
            obj.save()           
            return response.Response(
            {
                'message': 'health insurence Deleted Successfully'
            },
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(str(e), 'Some thing went wrong', 404),
                status=status.HTTP_404_NOT_FOUND
            )
"""

class OnboardingEmployeeCreateView(APIView):

    model = Employee
    serializer_class = dir_serializers.OnboardingEmployeeSerialzer
    permission_classes = [ATSAddEmployeePermission]

    def post(self, request, *args, **kwargs):
        domain = f"{self.request.scheme}://{self.request.get_host()}/"
        request_dataed = self.request.data
        if type(request_dataed) != dict:
            request_data = request_dataed.dict()
        else:
            request_data = request_dataed
        
        ctc = request_data.pop('ctc',[])
        work_details = request_data.pop('work_details',[])
        attendance_rule = request_data.pop('attendance_rule',[])
        reporting_manager = request_data.pop('reporting_manager',[])
        salary_details = request_data.pop('salary_details',[])
        
        converted_data = {
                 'reporting_manager':reporting_manager
        }
        if work_details and isinstance(work_details,str):
            work_details = literal_eval(work_details) 
            request_data['work_details'] = work_details

        if attendance_rule and isinstance(attendance_rule,str):
            attendance_rule = literal_eval(attendance_rule) 
            converted_data['attendance_rule'] = attendance_rule

        if salary_details and isinstance(salary_details,str):
            salary_details = literal_eval(salary_details) 
            converted_data['salary_details'] = salary_details

        #handling Employee Added from status
        added_from = 'HRMS'
        ats_key = request.headers.get('X-ATS-TOKEN','')
        if ats_key == "ATS@123":
            added_from = 'ATS'
        
        user_info = self.request.user.username
        serializer = self.serializer_class(data=request_data, context={'extra_data':converted_data, 'domain':domain, 
                                                                       'logged_in_user': user_info, 'ctc':ctc, 'added_from':added_from})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        
        # add employee into ATS
        employee = Employee.objects.filter(id=serializer.data.get('id')).first()
        payload = {
            'company_id':employee.company.id,
            'emp_code': employee.work_details.employee_number,
            'emp_first_name': employee.first_name ,
            'emp_middle_name': employee.middle_name if employee.middle_name else 'Null',
            'emp_last_name': employee.last_name,
            'dept_id': employee.work_details.department_id if employee.work_details.department_id else 'Null',
            'designation_id': employee.work_details.designation_id if employee.work_details.designation_id else 'Null',
            'pernonal_email': employee.personal_email if employee.personal_email else 'Null',
            'office_email':employee.official_email
        }
        add_employee_ats(payload)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED) 
    
    
    def patch(self, request, *args, **kwargs):
        domain = f"{self.request.scheme}://{self.request.get_host()}/"
        emp_id = kwargs.get("employee_id")
        emp_obj = get_object_or_404(self.model, id=emp_id)
        request_dataed = self.request.data
        if type(request_dataed) != dict:
            request_data = request_dataed.dict()
        else:
            request_data = request_dataed
        work_details = request_data.pop('work_details',[])
        attendance_rule = request_data.pop('attendance_rule',[])
        reporting_manager = request_data.pop('reporting_manager',[])
        onboarding_status = request_data.pop('onboarding_status',[])
        
        converted_data = {
                 'reporting_manager':reporting_manager, "onboarding_status":onboarding_status
        }
        if work_details and isinstance(work_details,str):
            work_details = literal_eval(work_details) 
            request_data['work_details'] = work_details

        if attendance_rule and isinstance(attendance_rule,str):
            attendance_rule = literal_eval(attendance_rule) 
            converted_data['attendance_rule'] = attendance_rule


        user_info = self.request.user.username
        serializer=self.serializer_class(emp_obj, data=request_data, 
                                         context={'extra_data':converted_data, 'domain':domain, 'logged_in_user': user_info},
                                         partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    
class EmployeeDocumentationWorkView(APIView):
    model = EmployeeDocumentationWork
    parser_classes = [DrfNestedParser]
    serializer_class = EmployeeWorkDocSerializer
    pagination_class = CustomPagePagination
    # detailed_serializer_class = EmployeeDocumentationWorkDetailSerializer
    # queryset = EmployeeDocumentationWork.objects.all()
    
    def get(self, request, *args, **kwargs):
        # MultitenantSetup().create_to_connection(request)
        employee_id = kwargs.get("id")
        employee = Employee.objects.filter(id=employee_id)
        if not employee.exists():
            return Response(
                error_response("Employee Not exists", "Employee Not exists", 404),
                status=status.HTTP_404_NOT_FOUND
            )
        paginator = self.pagination_class()
        q_filter = db_models.Q(employee_id=employee_id, is_deleted=False)
        data = self.model.objects.filter(q_filter).annotate(
                        uploaded_by=db_models.F('created_by__username'),
                        files = ArrayAgg(
                                    db_models.Case(
                                            db_models.When(employee_work_doc_files__isnull=True,
                                                                                            then=db_models.expressions.Func(
                                                                                        db_models.Value(''), db_models.Value(''),
                                                                                        function='jsonb_build_object',
                                                                                    output_field=db_models.JSONField()
                                                                                ),
                                                                            ),
                                            db_models.When(employee_work_doc_files__isnull=False, 
                                            then= db_models.expressions.Func(
                                                                db_models.Value('id'), "employee_work_doc_files__id",
                                                                db_models.Value('doc'), "employee_work_doc_files__work_doc",
                                                                db_models.Value('is_deleted'), "employee_work_doc_files__is_deleted",
                                                                function="jsonb_build_object",
                                                                output_field=db_models.JSONField()
                                                            )
                                        ),default=db_models.Value(None),
                                            output_field=db_models.JSONField(),
                                            # filter = db_models.Q(on_boarding_check_lists__is_deleted=False)
                                    )
                            , distinct=True,
                            filter = db_models.Q(employee_work_doc_files__is_deleted=False))
        ).values(
            "id", "employee", "document_title", "document_description", "created_by", "is_deleted",
            "uploaded_by", "created_at","select_file","files"
        )
        page = paginator.paginate_queryset(list(data), request)
        # MultitenantSetup().go_to_old_connection(request)
        return Response(
            success_response(paginator.get_paginated_response(page), "Successfully Fetched Employee Work Docs Data", 200),
            status=status.HTTP_200_OK
        )
    
    def post(self, request, *args, **kwargs):
        sid =transaction.set_autocommit(autocommit=False)
        try:
            data = request.data
            data = data.dict()
            title = data.get('document_title','')
            employee_id = data.get('employee')
            documents = data.get('files',[])
            if not documents:
                message =  'Work Documents Are Mandatory'
                return Response(
                    error_response(message, message),
                        status=status.HTTP_400_BAD_REQUEST
                )
            work_doc_query = EmployeeDocumentationWork.objects.filter(employee_id=employee_id, document_title=title, is_deleted=False)
            if work_doc_query.exists():
                message =  'Work Documents Title Already Exists'
                return Response(
                    error_response(message, message),
                        status=status.HTTP_400_BAD_REQUEST
                )
            work_serializer = self.serializer_class(data=data)
            if work_serializer.is_valid(raise_exception=True):
                work_serializer.save()
                for obj in documents:
                    doc=obj['doc'][0]
                    EmployeeWorkDocuments.objects.create(document_id=work_serializer.data.get('id'), work_doc=doc)
            transaction.commit()        
            return response.Response(
                    {
                        'message': 'Work Documents Uploaded Successfully'
                    },
                    status=status.HTTP_200_OK
                    )
        except Exception as e:
            transaction.rollback(sid)
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
            
    def patch(self, request, *args, **kwargs):
        sid =transaction.set_autocommit(autocommit=False)
        try:
            data = request.data
            data = data.dict()
            emp_doc_obj = get_object_or_404(self.model, id=self.kwargs.get('id'))
            title = data.get('document_title','')
            employee_id = data.get('employee')
            documents = data.get('files',[])
            # if not documents:
            #     message =  'Work Documents Are Mandatory'
            #     return Response(
            #         error_response(message, message),
            #             status=status.HTTP_400_BAD_REQUEST
            #     )
            work_doc_query = EmployeeDocumentationWork.objects.filter(employee_id=employee_id, document_title=title, is_deleted=False).exclude(id=self.kwargs.get('id'))
            if work_doc_query.exists():
                message = 'Work Documents Title Already Exists'
                return Response(
                    error_response(message, message),
                        status=status.HTTP_400_BAD_REQUEST
                )
            work_serializer = self.serializer_class(
                        instance=emp_doc_obj, data=data, partial=True
                    )
            if work_serializer.is_valid(raise_exception=True):
                work_serializer.save()
                if documents:
                    is_created = False
                    for obj in documents:
                        doc = ''
                        if 'doc' in obj:
                            doc=obj['doc'][0]
                        if 'id' in obj:
                            doc_obj = EmployeeWorkDocuments.objects.filter(id=obj['id'])
                        else:
                            doc_obj, is_created = EmployeeWorkDocuments.objects.get_or_create(document_id=self.kwargs.get('id'), work_doc=doc)
                        if 'is_deleted' in obj and not is_created:
                            is_dltd = True if obj.get('is_deleted','') == 'true' else False
                            doc_obj.update(is_deleted = is_dltd)
                        if doc and not is_created:
                            doc_obj.update(work_doc=doc)
                    
            transaction.commit()        
            return Response(
                    success_response([], f"{title} Documents Uploaded Successfully", 200),
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            transaction.rollback(sid)
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
    def delete(self, request, *args, **kwargs):
        emp_doc_obj = get_object_or_404(self.model, id=self.kwargs.get('id'))
        emp_doc_obj.is_deleted=True
        emp_doc_obj.save()
        return Response(
                    success_response([], f"{emp_doc_obj.document_title} Documents Deleted Successfully", 200),
                    status=status.HTTP_200_OK
                )
class CTCHistoryApi(APIView):
    """
    this class is used to get the ctc history for the report
    """
    pagination_class = CustomPagePagination

    def get(self, request):
        try:
            deps_qs = Departments.objects.all().filter(employeeworkdetails__employee__employee_ctc_history__isnull=False).distinct()
            depts_filters = deps_qs.values('id', 'name')
            
            ctc_emps_qs = CTCHistory.objects.filter(employee__work_details__department__id__in=set(deps_qs.values_list('id', flat=True))).distinct('employee')
            emps_filters = ctc_emps_qs.values('employee_id', 'employee__user__username', 'employee__work_details__department_id', 'employee__work_details__department__name')
            
            months_filters = ctc_emps_qs.values('updated_at__date', 'employee_id', 'employee__user__username')
            
            params = request.query_params
            
            q_filters=Q()
            if 'depts_ids' in params:
                q_filters &= Q(employee__work_details__department_id__in = params.get('depts_ids').split(','))
            
            if 'emps_ids' in params:
                q_filters &= Q(employee_id__in = params.get('emps_ids').split(','))
            
            if 'months' in params:
                q_filters &= Q(updated_at__date__in = params.get('months').split(','))

            if "search_filter" in params:
                q_filters &= (
                    db_models.Q(employee__user__username__icontains = search_filter_decode(params.get("search_filter"))) |
                    db_models.Q(employee__work_details__employee_number__icontains = search_filter_decode(params.get("search_filter"))) |
                    db_models.Q(updated_by__user__username__icontains = search_filter_decode(params.get("search_filter"))) | 
                    db_models.Q(updated_by__work_details__employee_number__icontains = search_filter_decode(params.get("search_filter")))
                )
            
            ctc_qs = CTCHistory.objects.filter(q_filters).order_by('-updated_at').annotate(employee_code = StringAgg('employee__work_details__employee_number', delimiter = ', '),
                                                               employee_name = StringAgg('employee__user__username', delimiter = ', '),
                                                               old_ctc = F('updated_ctc'),
                                                               changed_on= F('updated_at'),
                                                               changed_by = StringAgg('updated_by__user__username', delimiter = ', '),
                                                               )
            
            ctc_data = CTCHistorySerializer(ctc_qs, many=True).data
            
            if 'download' in params and (params['download']=="true"):
                df = pd.DataFrame(ctc_data)
                date_columns = df.select_dtypes(include=['datetime64[ns, UTC]']).columns
                for date_column in date_columns:
                    df[date_column] = df[date_column].dt.date
                file_name = "ctc_history_report.xlsx"
                return excel_converter(df,file_name)

            paginator = self.pagination_class()

            page = paginator.paginate_queryset(list(ctc_data), request)
            result = {"paginated_data":paginator.get_paginated_response(page), 'depts_filters':depts_filters, 'emps_filters':emps_filters, 'months_filters':months_filters}
            return Response(
                result
            )

        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )

class OfferLetterEmailApi(APIView):
    
    model = EmployeePreBoardingDetails
    
    def post(self, request, *args, **kwargs):
        request_data = request.data
        request_data = request_data.dict()
        content = request_data.get('content')
        subject = request_data.get('subject', '')
        pdf_content = request_data.get('pdf_content','')
        pdf = request_data.get('file', None)
        flag = request_data.get('flag', '')
        cc_email = request_data.get('cc', '')
        content = html.unescape(content)
        pdf_content = html.unescape(pdf_content)
        msg = 'Conditional Offer Letter' if flag == 'col' else "Appointment Letter"
        if not flag:
            message = "Please Set Flag As col/al"
            return Response(
            error_response(message,message),
            status=status.HTTP_400_BAD_REQUEST
        )
        emp_obj = Employee.objects.filter(id=kwargs.get('id'))
        if not emp_obj.exists():
            message = "Employee Matching query does not exist"
            return Response(
            error_response(message,message),
            status=status.HTTP_400_BAD_REQUEST
        )
        employee_email = emp_obj.first().user.email
        company_logo  = emp_obj.first().company.company_image.url if emp_obj.first().company.company_image else None 
        # company_logo_1 = f"https://pss.bharatpayroll.com/qxbox{company_logo}"
        company_logo_2 = f"{self.request.scheme}://{self.request.get_host()}/qxbox{company_logo}"
        # hr_query = Employee.objects.filter(is_deleted=False,work_details__employee_status='Active',roles__name='HR',
        #                                         company_id=emp_obj.first().company.id)
        # hr_email = list(hr_query.values_list('official_email',flat=True)) 
        subject = subject if subject else f"{emp_obj.first().user.username}'s Conditional Offer Letter"
        token = PasswordResetTokenGenerator().make_token(emp_obj.first().user)
        end_point = 'alstatus' if flag == 'al' else 'colstatus'
        link = f"{request.scheme}://{request.get_host()}/{end_point}?email={employee_email}&token={token}"
        context={'data': content, "company_logo":company_logo_2, "link":link}

        body = email_render_to_string(
                                template_name="mails/directory_mails/conditional_offer_letter.html", 
                                context = context
                            )
        pdf_obj=None
        if pdf_content:
            pdf_context={'data': pdf_content}
            html_string = render_to_string("mails/directory_mails/offer_letter_pdf_content.html", pdf_context)
            pdf_obj = weasyprint.HTML(string=html_string).write_pdf()
        
        cc_list = [i.strip() for i in cc_email.split(',') if cc_email]
        
        data={
                'subject': subject,
                'body':body,
                'to_email': employee_email,
                'cc':cc_list,
                "content": body
            }
        try:
            # if check_alert_notification("Employee Management",'Reporting Manager Update', email=True):
            # is_email_sent = Util.send_custom_email(data,is_content_html=True, pdf_file_name=f"{emp_obj.first().user.username}'s {msg}.pdf", 
            #                                        pdf_bytes_obj=pdf_obj, pdf_file=pdf)
            is_email_sent, error = Util.ck_editor_email(data, pdf_file_name=f"{emp_obj.first().user.username}'s {msg}.pdf", 
                                                        pdf_bytes_obj=pdf_obj,pdf_file=pdf)
            if not is_email_sent:
                msg = "Email Sent Failed, Please Re-check The SMTP Credentials"
                return Response(
                    error_response(msg, msg),
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                error_response(str(e), "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
        if flag == 'col':
            self.model.objects.filter(employee=emp_obj.first()).update(is_conditional_offer_letter_sent=True, conditional_offer_letter=pdf, 
                           conditional_offer_letter_content=content, conditional_offer_letter_pdf_content=pdf_content)
            if pdf_obj:
                col_obj = self.model.objects.filter(employee=emp_obj.first()).first()
                col_obj.conditional_offer_letter.save(f"{col_obj.employee.user.username}'s {msg}.pdf", ContentFile(pdf_obj), save=True)
        elif flag == 'al':
            self.model.objects.filter(employee=emp_obj.first()).update(is_appointment_letter_sent=True, appointment_letter=pdf, appointment_letter_content=content,
                           appointment_letter_pdf_content=pdf_content)
        return Response(
            success_response([], f"{msg} Sent Successfully", 200),
            status=status.HTTP_200_OK
        )
        
class UpdateOfferLetterStatus(APIView):
    permission_classes = [permissions.AllowAny]
    model = EmployeePreBoardingDetails

    def get(self,request,*args, **kwargs):
        try:    
            #get employee data by status
            email = request.query_params.get('email','')
            token = request.query_params.get('token','')
            
            if email:
                q_filter = db_models.Q(db_models.Q(employee__personal_email=email) | db_models.Q(employee__user__email=email))
                emp_obj = self.model.objects.filter(q_filter)   
            if not emp_obj.exists():
                message = "Employee Matching query does not exist"
                return Response(
                error_response(message,message),
                status=status.HTTP_400_BAD_REQUEST
            )
            
            check_token_expairy = PasswordResetTokenGenerator().check_token(emp_obj.first().employee.user, token)
            # if not check_token_expairy:
            #     return Response(
            #         error_response("Token Expired", "Token Expired"),
            #         status=status.HTTP_400_BAD_REQUEST
            #     )
            data = self.model.objects.filter(q_filter).annotate(
                al_date_of_updated = db_models.functions.Cast(TimestampToStrDateTime(TimestampToIST(db_models.F('al_date_of_update'), 'Asia/Kolkata')), db_models.CharField()),
                col_date_of_updated = db_models.functions.Cast(TimestampToStrDateTime(TimestampToIST(db_models.F('col_date_of_update'), 'Asia/Kolkata')), db_models.CharField()),
                ).values(
                'conditional_offer_letter_content','appointment_letter_content','employee__company__company_name',
                'employee__user__username','employee__user__email','appointment_letter_status','conditional_offer_letter_status',
                "rejection_comments", "col_digital_sign","al_digital_sign",
                "col_date_of_updated", "col_ip_address", "al_date_of_updated", "al_ip_address"
            )
            return Response(
                    success_response(data, "Successfully Fetched Data", 200),
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                error_response(str(e), "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )        
    def post(self, request, *args, **kwargs):
        try:
            request_data = request.data
            request_data = request_data.dict()
            flag = request_data.get('flag', 'col')
            update_status = request_data.get('update_status','')
            token = request_data.get('token','')
            email = request_data.get('email','')
            file = request_data.get('file','')
            sign = request_data.get('sign','')
            comments = request_data.get('comments','')
            ip_address = get_ip_address(request)
            
            emp_obj = self.model.objects.filter(id=kwargs.get('id'))
            if email:
                q_filter = db_models.Q(db_models.Q(employee__personal_email=email) | db_models.Q(employee__user__email=email))
                emp_obj = self.model.objects.filter(q_filter)
            useranme = emp_obj.first().employee.user.username
            if (file == 'undefined' or not file) and flag != 'bgv' and update_status == 'Approved' and not sign:
                message = "Sign Is Mandatory"
                return Response(
                    error_response(message,message),
                    status=status.HTTP_400_BAD_REQUEST
            )

            if not comments and flag != 'bgv' and update_status == 'Rejected' :
                message = "Rejection Comments Are Mandatory"
                return Response(
                    error_response(message,message),
                    status=status.HTTP_400_BAD_REQUEST
            )
                
             
            if not emp_obj.exists():
                message = "Employee Matching query does not exist"
                return Response(
                error_response(message,message),
                status=status.HTTP_400_BAD_REQUEST
            )
            
            if email:
                check_token_expairy = PasswordResetTokenGenerator().check_token(emp_obj.first().employee.user, token)
                if not check_token_expairy:
                    return Response(
                        error_response("Token Expired", "Token Expired"),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            #convert file raw data
            
            file_data = None
            if file:
                format, imgstr = file.split(';base64,') 
                ext = format.split('/')[-1]
                file_data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
            
            if flag == 'col' and update_status:
                emp_obj.update(conditional_offer_letter_status=update_status, col_ip_address=ip_address, col_date_of_update=timezone_now())
                
            elif flag == 'al' and update_status:
                emp_obj.update(appointment_letter_status=update_status, al_ip_address=ip_address, al_date_of_update=timezone_now())
               
            elif flag == 'bgv':
                emp_obj.update(is_bgv_complted=update_status)
                
            if flag == 'col' and update_status == "Approved":
                if file_data:
                    file_name = f"col_digital_sign_{useranme}.png"
                    emp_obj.first().col_digital_sign.save(file_name, file_data, save=True)
                elif sign:
                    emp_obj.update(col_sign=sign)
            elif flag == 'al' and update_status == "Approved":
                if file_data:
                    file_name = f"al_digital_sign_{useranme}.png"
                    emp_obj.first().al_digital_sign.save(file_name, file_data, save=True)
                elif sign:
                    emp_obj.update(al_sign=sign)
            if comments:
                emp_obj.update(rejection_comments=comments)
            
            #Handling Responding status 
            if 'is_responding' in request_data:
                is_responding = eval(request_data.get('is_responding','True'))
                if is_responding:
                    emp_obj.update(is_responding=True)
                elif not is_responding:
                    emp_obj.update(is_responding=False)
                    EmployeeWorkDetails.objects.filter(employee=emp_obj.first().employee).update(employee_status='YetToJoin')
                    
            return Response(
                success_response([], "Successfully Updated The Status", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(str(e), "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
class LetterStatusChoices(APIView):
    permission_classes = [permissions.AllowAny]
    model = StatusChoices
    
    def get(self, request, *args, **kwargs):
        data = [
            {"name": choice[1], 'id':i+1}
            for i,choice in enumerate(StatusChoices.choices)
        ]
        return Response(
                success_response(data, "Successfully Fetched TaskType Choices", 200),
                status=status.HTTP_200_OK
            )
        
class OfferLetterUpdateAtsAPIView(APIView):
    
    model = EmployeePreBoardingDetails
    permission_classes = [ATSAddEmployeePermission]
    
    def post(self, request, *args, **kwargs):
        try:
            request_data = request.data
            request_data = request_data.dict()
            email = request_data.get('email')
            content = request_data.get('content')
            pdf_file = request_data.get('file',None)
            pdf_content = request_data.get('pdf_content','')
            flag = request_data.get('flag', 'col')
            letter_status = request_data.get('status', 'Approved')
            ip_address = request_data.get('ip_address', '')
            date_of_update = request_data.get('date_of_update', '')
            col_digital_sign = request_data.get('col_digital_sign', None)
            col_sign = request_data.get('col_sign', '')
            
            msg = 'Conditional Offer Letter' if flag == 'col' else "Appointment Letter"
            
            if not flag:
                message = "Please Set Flag As col/al"
                return Response(
                error_response(message,message),
                status=status.HTTP_400_BAD_REQUEST
            )
            emp_obj = self.model.objects.filter(employee__user__email=email)
            if not emp_obj.exists():
                message = "Employee Matching query does not exist"
                return Response(
                error_response(message,message),
                status=status.HTTP_400_BAD_REQUEST
            )
                
            if flag == 'col':
                emp_obj.update(is_conditional_offer_letter_sent=True,conditional_offer_letter_content=content, 
                               conditional_offer_letter_status=letter_status, col_ip_address=ip_address, 
                               col_date_of_update=date_of_update, conditional_offer_letter_pdf_content=pdf_content,
                               col_sign=col_sign
                            )
                if col_digital_sign:
                    r1 = requests.get(col_digital_sign)
                    if r1.status_code == 200:
                        emp_obj = emp_obj.first()
                        fil_name = col_digital_sign.split('/')[-1]
                        emp_obj.col_digital_sign.save(fil_name, ContentFile(r1.content), save=True)
                    else:
                        return Response(
                            error_response(r1.status_code, "Some thing went wrong with url"),
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                if pdf_file:
                    r2 = requests.get(pdf_file)
                    if r2.status_code == 200:
                        emp_obj = emp_obj.first()
                        fil_name = pdf_file.split('/')[-1]
                        emp_obj.conditional_offer_letter.save(fil_name, ContentFile(r2.content), save=True)
                    else:
                        return Response(
                            error_response(r2.status_code, "Some thing went wrong with url"),
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
            return Response(
                success_response([], f"{msg} Updated Successfully", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(str(e), "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )

class CompanySMTPSetupAPIView(APIView):
    model = CompanySMTPSetup
    
    def get(self, request, *args, **kwargs):
        try:
            params = request.query_params
            company_id = params.get('company_id','')
            q_filter = db_models.Q()
            if company_id:
                q_filter &= db_models.Q(company_id=company_id)
            query_data = self.model.objects.filter(q_filter).values()
            return Response(
                success_response(query_data, "SMTP data Fetched Successfully", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(str(e), "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
    def post(self, request, *args, **kwargs):
        try:
            request_data = request.data
            company_id = request_data.get('company_id')
            cmp_data = CompanyDetails.objects.filter(id=company_id)
            if not cmp_data.exists():
                message = "Please Provide A Correct Company Id "
                return Response(
                    error_response(message, message),
                    status=status.HTTP_400_BAD_REQUEST
                )
            request_data['company'] = cmp_data.first()
            query_data = self.model.objects.create(**request_data)
            return Response(
                success_response([], "SMTP Data Created Successfully", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(str(e), "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
    def patch(self, request, *args, **kwargs):
        try:
            request_data = request.data
            company_id = kwargs.get('company_id')
            cmp_data = CompanyDetails.objects.filter(id=company_id)
            if not cmp_data.exists():
                message = "Please Provide A Correct Company Id "
                return Response(
                    error_response(message, message),
                    status=status.HTTP_400_BAD_REQUEST
                )
            query_data = self.model.objects.filter(company_id=company_id).update(**request_data)
            return Response(
                success_response([], "SMTP Data Updated Successfully", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(str(e), "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
    def delete(self, request, *args, **kwargs):
        try:
            company_id = kwargs.get('company_id')
            query_data = self.model.objects.filter(company_id=company_id).delete()
            return Response(
                success_response([], "SMTP Data Deleted Successfully", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(str(e), "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )

class EmployeeStatusDetailsAPIView(APIView):
    
    model = EmployeePreBoardingDetails
    permission_classes = [ATSAddEmployeePermission]
    
    def get(self, request, *args, **kwargs):
        try:
            emp_query = self.model.objects.filter(employee__work_details__employee_number__isnull=False, 
                                                  is_conditional_offer_letter_sent=True
                                ).annotate(
                                    al_date_of_updated = db_models.functions.Cast(TimestampToStrDateTime(TimestampToIST(db_models.F('al_date_of_update'), 'Asia/Kolkata')), db_models.CharField()),
                                    col_date_of_updated = db_models.functions.Cast(TimestampToStrDateTime(TimestampToIST(db_models.F('col_date_of_update'), 'Asia/Kolkata')), db_models.CharField()),
                                    first_name = db_models.F('employee__first_name'),
                                    middle_name = db_models.F('employee__middle_name'),
                                    last_name = db_models.F('employee__last_name'),
                                    official_email = db_models.F('employee__official_email'),
                                    personal_email = db_models.F('employee__personal_email')
                                ).values()
            return Response(
                success_response(emp_query, "Data Fetched Successfully", 200),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(str(e), "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )

class CustomWelcomeMessage(APIView):
    model = Employee
    
    def post(self, request, *args, **kwargs):
        request_data = request.data
        content = request_data.get('content')
        subject = request_data.get('subject', '')
        emp_id = request_data.get('emp_id', '')
        cc_email = request_data.get('cc', '')
        bcc_email = request_data.get('bcc', '')
        content = html.unescape(content)
        if not emp_id:
            message = "Please Provide Employee Id"
            return Response(
            error_response(message,message),
            status=status.HTTP_400_BAD_REQUEST
        )
        emp_obj = self.model.objects.filter(id=emp_id)
        if not emp_obj.exists():
            message = "Employee Matching query does not exist"
            return Response(
            error_response(message,message),
            status=status.HTTP_400_BAD_REQUEST
        )
        official_email = emp_obj.first().user.email
        company_logo  = emp_obj.first().company.company_image.url if emp_obj.first().company.company_image else None 
        # company_logo_1 = f"https://pss.bharatpayroll.com/qxbox{company_logo}"
        company_logo_2 = f"{self.request.scheme}://{self.request.get_host()}/qxbox{company_logo}"

        body = email_render_to_string(
                                template_name="mails/directory_mails/custom_welcome_email.html", 
                                context={'data': content, "company_logo":company_logo_2}
                            )
        subject = subject if subject else f"Wellcome To {emp_obj.first().company.company_name}"
        cc_list = [i.strip() for i in cc_email.split(',') if cc_email]
        bcc_list = [i.strip() for i in bcc_email.split(',') if bcc_email]
        data={
                'subject': subject,
                'content':body,
                'to_email': official_email,
                'cc':cc_list,
                'bcc':bcc_list
            }
        try:
            is_mail_sent, data = Util.ck_editor_email(data)
            # if check_alert_notification("Employee Management",'Reporting Manager Update', email=True):
            # is_mail_sent = Util.send_custom_email(data,is_content_html=True)
            if not is_mail_sent:
                msg = "Email Sent Failed, Please Re-check The SMTP Credentials"
                return Response(
                    error_response(msg, msg),
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                error_response(str(e), "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
        EmployeePreBoardingDetails.objects.filter(employee=emp_obj.first()).update(is_welcome_mail_sent=True)
        return Response(
            success_response([], "Email Sent Successfully", 200),
            status=status.HTTP_200_OK
        )

class TestEmail(APIView):
    model = Employee
    
    def post(self, request, *args, **kwargs):
        request_data = request.data
        content = request_data.get('content')
        email = request_data.get('email')
        subject = request_data.get('subject')
        company_id =  request.user.employee_details.first().company.id
        smtp_creds = CompanySMTPSetup.objects.filter(company_id=company_id)
        if not smtp_creds.exists():
            message = "SMTP Credentials Does Not Exist"
            return Response(
            error_response(message,message),
            status=status.HTTP_400_BAD_REQUEST
        )
        smtp_obj = smtp_creds.first()
        company_logo  = smtp_obj.company.company_image.url if smtp_obj.company.company_image else None
        # company_logo_1 = f"https://pss.bharatpayroll.com/qxbox{company_logo}"
        company_logo_2 = f"{self.request.scheme}://{self.request.get_host()}/qxbox{company_logo}"
        body = email_render_to_string(
                                template_name="mails/directory_mails/test_email.html", 
                                context={'data': content, "company_logo":company_logo_2}
                            )
        subject = subject if subject else "Test Email"
        is_sent = False
        try:
            email_creds = {
                    "host":smtp_obj.email_host,
                    "port":smtp_obj.email_port,
                    "username":smtp_obj.email_host_user,
                    "password":smtp_obj.email_host_password,
                    "use_tls":True,
                    "fail_silently":True
                }
            from_email = smtp_obj.from_email
            custom_connection = get_connection(**email_creds)    
            
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_email,
                to=[email],
                # cc=cc,
                connection=custom_connection
            )
            email.content_subtype = 'html'
            is_sent = bool(email.send())
        except Exception as e:
            return Response(
                error_response(str(e), "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
        if not is_sent:
            msg = "Email Sent Failed, Please Re-check The SMTP Credentials"
            return Response(
                error_response(msg, msg),
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            success_response([], "Email Sent Successfully", 200),
            status=status.HTTP_200_OK
        )
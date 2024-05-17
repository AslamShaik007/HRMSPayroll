# from django.contrib.contenttypes.models import ContentType
import logging
from django.db import transaction
from nested_multipart_parser.drf import DrfNestedParser
from django.core.files.images import ImageFile

from django.shortcuts import get_object_or_404

from rest_framework import status, permissions
from rest_framework.generics import DestroyAPIView, RetrieveUpdateAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import viewsets

from core.views import AbstractListAPIView, APIView
from HRMSApp.models import Attachment
from directory.models import Employee
from HRMSApp.serializers import AttachmentSerializer
from investment_declaration.models import (
    DeclarationForms,
    InvestmentDeclaration,
    FormChoices,
    SubFormChoices,
    Attachments,
)
from investment_declaration.serializers import (
    InvestmentDeclarationDetailSerializer,
    InvestmentDeclarationSerializer,
    InvestmentDeclarationStatusChangeSerializer,
    InvestmentDeclarationEnteriesUpdateSerializer,
    FormChoicesSerializer,
)
from core.utils import b64_to_image
from core.utils import excel_converter, timezone_now, success_response, error_response
from core.custom_paginations import CustomPagePagination
from core.whatsapp import WhatsappMessage

from payroll.models import Reimbursement, Regime, HealthEducationCess
from rest_framework import response 
from django.utils import timezone
from django.db.models import Value, F
from django.db.models.functions import  Concat


import pandas as pd
from HRMSApp.utils import Util
from roles.models import Roles
import traceback
from alerts.utils import check_alert_notification
logger = logging.getLogger('django')
from payroll.utils import ctc_to_gross_per_year, calculate_tax_for_regime, get_financial_dates_start_and_end
from dateutil.relativedelta import relativedelta

class FormChoicesRetriveApiView(AbstractListAPIView):
    """
    View to retrieve form choices
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = FormChoicesSerializer
    queryset = FormChoices.objects.all()
    


class InvestmentDeclarationCreateView(APIView):
    parser_classes = [DrfNestedParser]
    model = InvestmentDeclaration
    
    def post(self, request, format=None):
        """
        Default Post Method
        """        
        hr_and_admins = Roles.objects.filter(name__in=["ADMIN","HR"],
                                             roles_employees__company_id = 1, 
                                             roles_employees__work_details__employee_status="Active").values(
                                                                    "roles_employees__official_email","roles_employees__user__username",
                                                                    "roles_employees__work_details__employee_number",
                                                                    "roles_employees__user__phone")
        data = request.data.dict()
        if int(data["endYear"]) - int(data["startYear"]) != 1:
            return Response(
                {"data": {"status": "Enter declaraton for One (1) Year only"}},
                status=status.HTTP_400_BAD_REQUEST,
            )    
        obj=InvestmentDeclaration.objects.filter(employee=data["employee"],
                                                 start_year=data["startYear"],
                                                 end_year=data["endYear"]
                                                 )
        if obj.exists():
            return Response(
                {"data": {"status": "Employee can have only one investment declaration for year"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract the first (and only) dictionary from the list        
        details = data.get("details")
        regime_type = eval(str(data["regimeType"]))
        if details is None:
            print("cmng Without Details")
            emp_obj = Employee.objects.get(id=data["employee"])
            declaration = InvestmentDeclaration.objects.create(
                        employee=emp_obj,
                        regime_type=regime_type,
                        declaration_amount=data["declarationAmount"],
                        status=data["status"],
                        start_year=data["startYear"],
                        end_year=data["endYear"],
                        income_from_previous_employer=data["incomeFromPreviousEmployer"],
                        tds_from_previous_employer=data["tdsFromPreviousEmployer"]
                    )
            if int(data.get("status")) == 20:
                declaration.submitted_date = timezone_now().date()
                declaration.admin_resubmit_status=InvestmentDeclaration.FINAL_APPROVED
                declaration.approval_date=timezone_now().date()
                declaration.final_approved_amount=data["declarationAmount"]
                declaration.save()
                try:
                    employee_name = emp_obj.user.username.title()
                    official_email = emp_obj.official_email
                    emp_code = emp_obj.work_details.employee_number
                    body = f"""
Hello {employee_name} [{emp_code}],

Your savings declaration has been successfully submitted for the year {data["startYear"]}-{data["endYear"]}. This email serves as confirmation of the receipt of your information.

Your savings declaration documents are now available for secure access. Feel free to review them for transparency and accessibility


Thank you for your prompt action.


Best regards,
{emp_obj.company.company_name.title()}.                         
    """
                    content1={
                        'subject':f'Successful Submission of Savings Declaration for year {data["startYear"]}-{data["endYear"]}',
                        'body':body,
                        'to_email':official_email
                    }
                    if check_alert_notification("Saving Declaration",'Form Submission', email=True):  
                        Util.send_email(content1)
                except Exception as e:
                    print("Execption in sending mail to Employee",e)
                    
                # employee Whatsapp notifications
                try:
                    domain = f"{self.request.scheme}://{self.request.get_host()}/"
                    manager_data = {
                            'phone_number': emp_obj.user.phone,
                            'subject': 'Savings Declaration Submission',
                            "body_text1":"Your savings declaration has been successfully submitted",
                            'body_text2': f"For the year {data['startYear']}-{data['endYear']}",
                            'url': f"{domain}savingdeclaration",
                            "company_name":emp_obj.company.company_name.title()
                            }
                    if check_alert_notification("Saving Declaration",'Form Submission', whatsapp=True): 
                        WhatsappMessage.whatsapp_message(manager_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to {emp_obj.user.username} in Submission of Savings Declaration: {e}") 
                    
                # Send Email to HR / Admin for record keeping
                try:
                    for obj in hr_and_admins:
                        empl_name = obj['roles_employees__user__username'].title()
                        email = obj['roles_employees__official_email']
                        emp_code = obj['roles_employees__work_details__employee_number']
                        body = f"""
Dear {empl_name} [{emp_code}],

We would like to inform you that {emp_obj.user.username.title()} has successfully submitted their savings declaration for the year {data["startYear"]}-{data["endYear"]}. Please consider this for record-keeping and verification.

Thank you for your prompt action.


Best regards,
{emp_obj.company.company_name.title()}.                         
"""
                        content2={
                            'subject':f'{emp_obj.user.username.title()} has successfully submitted the saving declaration for the year {data["startYear"]}-{data["endYear"]}',
                            'body':body,
                            'to_email':email
                        }
                        if check_alert_notification("Saving Declaration",'Form Submission', email=True): 
                            Util.send_email(content2)
                        
                        # HR/Admin Whatsapp notifications
                        try:
                            domain = f"{self.request.scheme}://{self.request.get_host()}/"
                            phone = obj['roles_employees__user__phone']
                            manager_data = {
                                    'phone_number': phone,
                                    'subject': 'Savings Declaration Submission',
                                    "body_text1":f"{emp_obj.user.username.title()} has successfully submitted the saving declaration",
                                    'body_text2': f"For the year {data['startYear']}-{data['endYear']}",
                                    'url': f"{domain}savingdeclaration",
                                    "company_name":emp_obj.company.company_name.title()
                                    }
                            if check_alert_notification("Saving Declaration",'Form Submission', whatsapp=True): 
                                WhatsappMessage.whatsapp_message(manager_data)
                        except Exception as e:
                            logger.warning(f"Error while sending Whatsapp notificaton to {empl_name} in Submission of Savings Declaration: {e}")     
                    
                except Exception as e:
                    logger.warning(f"Error while sending email notificaton in Submission of Savings Declaration: {e}")     
                    
            if data.get("attachments"):
                for file in data.get("attachments"):
                    Attachments.objects.create(
                                        investment_declaration=declaration,
                                        attachment=file,
                                    )
            return Response(
                    {"data": {"status": "forms saved successfully"}},
                    status=status.HTTP_200_OK,
                )
        else:
            print("cmng With Details")
            created = None
            try:          
                # Iterate over the details dictionary
                if details:
                    emp_obj = Employee.objects.get(id=data["employee"])
                    declaration_qs = InvestmentDeclaration.objects.filter(
                        employee=emp_obj,
                        regime_type=regime_type,
                        declaration_amount=data["declarationAmount"],
                        status=data["status"],
                        start_year=data["startYear"],
                        end_year=data["endYear"],
                        income_from_previous_employer=data["incomeFromPreviousEmployer"],
                        tds_from_previous_employer=data["tdsFromPreviousEmployer"]
                    )
                    if declaration_qs.exists():
                        declaration = declaration_qs.first()
                    else:
                        declaration = InvestmentDeclaration.objects.create(
                            employee=emp_obj,
                            regime_type=regime_type,
                            declaration_amount=data["declarationAmount"],
                            status=data["status"],
                            start_year=data["startYear"],
                            end_year=data["endYear"],
                            income_from_previous_employer=data["incomeFromPreviousEmployer"],
                            tds_from_previous_employer=data["tdsFromPreviousEmployer"]
                        )
                        if int(data.get("status")) == 20:
                            declaration.submitted_date = timezone_now().date()
                            declaration.save()
                            try:
                                employee_name = emp_obj.user.username.title()
                                official_email = emp_obj.official_email
                                emp_code = emp_obj.work_details.employee_number
                                body = f"""
Hello {employee_name} [{emp_code}],

Your savings declaration has been successfully submitted for the year {data["startYear"]}-{data["endYear"]}. This email serves as confirmation of the receipt of your information.

Your savings declaration documents are now available for secure access. Feel free to review them for transparency and accessibility


Thank you for your prompt action.


Best regards,
{emp_obj.company.company_name.title()}.                         
    """
                                content1={
                                    'subject':f'Successful Submission of Savings Declaration of year {data["startYear"]}-{data["endYear"]}',
                                    'body':body,
                                    'to_email':official_email
                                }
                                if check_alert_notification("Saving Declaration",'Form Submission', email=True): 
                                    Util.send_email(content1)
                            except Exception as e:
                                print("Execption in sending Email to Employee",e)
                                # Send Email to HR / Admin for record keeping
                                
                            # employee Whatsapp notifications
                            try:
                                domain = f"{self.request.scheme}://{self.request.get_host()}/"
                                manager_data = {
                                        'phone_number': emp_obj.user.phone,
                                        'subject': 'Savings Declaration Submission',
                                        "body_text1":"Your savings declaration has been successfully submitted",
                                        'body_text2': f"For the year {data['startYear']}-{data['endYear']}",
                                        'url': f"{domain}savingdeclaration",
                                        "company_name":emp_obj.company.company_name.title()
                                        }
                                if check_alert_notification("Saving Declaration",'Form Submission', whatsapp=True): 
                                    WhatsappMessage.whatsapp_message(manager_data)
                            except Exception as e:
                                logger.warning(f"Error while sending Whatsapp notificaton to {emp_obj.user.username} in Submission of Savings Declaration: {e}")   
                                
                            try:
                                for obj in hr_and_admins:
                                    empl_name = obj['roles_employees__user__username'].title()
                                    email = obj['roles_employees__official_email']
                                    emp_code = obj['roles_employees__work_details__employee_number']
                                    body = f"""
Dear {empl_name} [{emp_code}],

We would like to inform you that {emp_obj.user.username.title()} has successfully submitted their savings declaration for the year {data["startYear"]}-{data["endYear"]}. Please consider this for record-keeping and verification.

Thank you for your prompt action.


Best regards,
{emp_obj.company.company_name.title()}.                         
"""
                                    content2={
                                        'subject':f'{emp_obj.user.username.title()} has successfully submitted the saving declaration for the year {data["startYear"]}-{data["endYear"]}',
                                        'body':body,
                                        'to_email':email
                                    }
                                    if check_alert_notification("Saving Declaration",'Form Submission', email=True): 
                                        Util.send_email(content2)
                                    
                                    # HR/Admin Whatsapp notifications
                                    try:
                                        domain = f"{self.request.scheme}://{self.request.get_host()}/"
                                        phone = obj['roles_employees__user__phone']
                                        manager_data = {
                                                'phone_number': phone,
                                                'subject': 'Savings Declaration Submission',
                                                "body_text1":f"{emp_obj.user.username.title()} has successfully submitted the saving declaration",
                                                'body_text2': f"For the year {data['startYear']}-{data['endYear']}",
                                                'url': f"{domain}savingdeclaration",
                                                "company_name":emp_obj.company.company_name.title()
                                                }
                                        if check_alert_notification("Saving Declaration",'Form Submission', whatsapp=True): 
                                            WhatsappMessage.whatsapp_message(manager_data)
                                    except Exception as e:
                                        logger.warning(f"Error while sending Whatsapp notificaton to {empl_name} in Submission of Savings Declaration: {e}")   
                                
                            except Exception as e:
                                print("Execption in sending Email to HR / Admin",e)
                        if data.get("attachments"):
                            for file in data.get("attachments"):
                                Attachments.objects.create(
                                                    investment_declaration=declaration,
                                                    attachment=file,
                                                )
                    for pf_det in details:
                        if pf_det.get("s_form") is not None:
                            for sf_det in pf_det['s_form']:                        
                                decform = DeclarationForms.objects.create(
                                    parentform_type=FormChoices.objects.get(id=pf_det['p_id']),
                                    subform_type=SubFormChoices.objects.get(id=sf_det['id']),
                                    declaration=declaration,
                                    declared_amount=sf_det.get("declaredAmount",0),
                                    comments_from_employee=sf_det.get("commentsFromEmployee"),
                                    comments_from_employer=sf_det.get("commentsFromEmployer"),
                                )
                                if sf_det.get("attachments"):
                                    for i in sf_det.get("attachments"):
                                        # attach_img = b64_to_image(
                                        #                 image_data=i,                                                        
                                        #                 use_ctime_as_prefix=True,
                                        #             )
                                        # attach_img =  ImageFile(io.BytesIO(i), name=i.name)
                                        Attachments.objects.create(
                                            declaration_form=decform,
                                            attachment=i,
                                        )
                        else:
                            form = DeclarationForms.objects.create(
                                parentform_type=FormChoices.objects.get(id=pf_det['p_id']),
                                declaration=declaration,
                                declared_amount=pf_det.get("declaredAmount",0),
                                comments_from_employee=pf_det.get("commentsFromEmployee"),
                                comments_from_employer=pf_det.get("commentsFromEmployer"),
                            )
                            
                            if pf_det.get("attachments"):                    
                                for file in pf_det["attachments"]:   
                                    # attach_img = b64_to_image(
                                    #                 image_data=file,                                                        
                                    #                 use_ctime_as_prefix=True,
                                    #             )                         
                                    Attachments.objects.create(
                                        declaration_form=form,
                                        attachment=file,
                                    )
                            
                    return Response(
                        {"data": {"status": "forms saved successfully"}},
                        status=status.HTTP_200_OK,
                    )
                                
                return Response(
                    {"data": {"status": "no details found"}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
                
            except Exception as e:
                if created:
                    declaration.delete()
                return Response({"error": str(e),"det":details})

    # # parser_classes = [DrfNestedParser]
    # model = InvestmentDeclaration
    
    # def post(self, request, format=None):
    #     """
    #     Default Post Method
    #     """        
    #     data = request.data
        
    #     if int(data["end_year"]) - int(data["start_year"]) != 1:
    #         return Response(
    #             {"data": {"status": "Enter declaraton for One (1) Year only"}},
    #             status=status.HTTP_400_BAD_REQUEST,
    #         )           
       
    #     if data["admin"]:
    #         emp_ids_list = Employee.objects.filter(id__in=data["employee_ids"]).values_list('id', flat=True)
            
    #         for emp_id in emp_ids_list:                
    #             declaration, _created = InvestmentDeclaration.objects.get_or_create(
    #                                                     employee_id=emp_id,                                                
    #                                                     start_year=data["start_year"],
    #                                                     end_year=data["end_year"],                                                                                                       
    #                                                 )   
                 
    #             declaration.freeze_declared_status = data['freeze_declared_status']
    #             declaration.freeze_final_declared_status = data['freeze_final_declared_status']
    #             declaration.access_to_select_regime = data['access_to_select_regime']
    #             declaration.last_submission_date = data['last_submission_date']                                                         
    #             declaration.save()

    #         return Response(
    #                     {"data": {"status": "forms status changed successfully"}},
    #                     status=status.HTTP_200_OK,
    #                 )      

    


class InvestmentDeclarationRetriveAPIView(AbstractListAPIView):
    """
    View to Retrieve Investment Declaration
    """
    serializer_class = InvestmentDeclarationDetailSerializer
    filterset_fields = ["id","employee__company", "employee", "start_year", "end_year"]
    queryset = InvestmentDeclaration.objects.all().order_by("-id")
    
        
class InvestmentDeclarationUpdateView(APIView):
    """
    View to Update Investment Declaration

    SURESH, 08.05.2023
    """
    model = InvestmentDeclaration
    serializer_class = InvestmentDeclarationSerializer
    detail_serializer_class = InvestmentDeclarationDetailSerializer
    lookup_field = "id"
    queryset = InvestmentDeclaration.objects.all()
    parser_classes = [DrfNestedParser]
    def patch(self, request, **kwargs):
        hr_and_admins = Roles.objects.filter(name__in=["ADMIN","HR"],
                                             roles_employees__company_id = 1, 
                                             roles_employees__work_details__employee_status="Active").values(
                                                                    "roles_employees__official_email","roles_employees__user__username",
                                                                    "roles_employees__work_details__employee_number",
                                                                    "roles_employees__user__phone")
        investment_obj = get_object_or_404(InvestmentDeclaration, id=kwargs['id'])
        data = request.data.dict()      
        
        regime_type = eval(str(data.get('regimeType')))
        
        if not regime_type:
            regime_type = eval(str(investment_obj.regime_type))
        details = data.get("details")
        
        # if details is None:            
        if regime_type == InvestmentDeclaration.NEW_TAX_REGIME:
            investment_obj.declaration_amount = data['declarationAmount']
            if data.get("status"):
                investment_obj.status = data['status']
                if int(data.get("status")) == 20:
                    investment_obj.submitted_date=timezone_now().date()
                    # investment_obj.admin_resubmit_status=InvestmentDeclaration.FINAL_APPROVED
                    investment_obj.admin_resubmit_status=None
                    investment_obj.approval_date=timezone_now().date()
                    investment_obj.final_approved_amount=data['declarationAmount']
                    try:
                        employee_name = investment_obj.employee.user.username.title()
                        official_email = investment_obj.employee.official_email
                        emp_code = investment_obj.employee.work_details.employee_number
                        body = f"""
Hello {employee_name} [{emp_code}],

Your savings declaration has been successfully submitted for the year {data["startYear"]}-{data["endYear"]}. This email serves as confirmation of the receipt of your information.

Your savings declaration documents are now available for secure access. Feel free to review them for transparency and accessibility


Thank you for your prompt action.


Best regards,
{investment_obj.employee.company.company_name.title()}.                         
    """
                        content1={
                            'subject':f'Successful Submission of Savings Declaration for year {data["startYear"]}-{data["endYear"]}',
                            'body':body,
                            'to_email':official_email
                        }
                        if check_alert_notification("Saving Declaration",'Form Submission', email=True): 
                            Util.send_email(content1)
                    except Exception as e:
                        print("Exception in sending Emails",e)
                        
                    # employee Whatsapp notifications
                    try:
                        domain = f"{self.request.scheme}://{self.request.get_host()}/"
                        manager_data = {
                                'phone_number': investment_obj.employee.user.phone,
                                'subject': 'Savings Declaration Submission',
                                "body_text1":"Your savings declaration has been successfully submitted",
                                'body_text2': f"For the year {data['startYear']}-{data['endYear']}",
                                'url': f"{domain}savingdeclaration",
                                "company_name":investment_obj.employee.company.company_name.title()
                                }
                        if check_alert_notification("Saving Declaration",'Form Submission', whatsapp=True): 
                            WhatsappMessage.whatsapp_message(manager_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {investment_obj.employee.user.username} in Submission of Savings Declaration: {e}") 
                        
                    try:
                        # Send Email to HR / Admin for record keeping
                        for obj in hr_and_admins:
                            empl_name = obj['roles_employees__user__username'].title()
                            email = obj['roles_employees__official_email']
                            emp_code = obj['roles_employees__work_details__employee_number']
                            body = f"""
    Dear {empl_name} [{emp_code}],

    We would like to inform you that {investment_obj.employee.user.username.title()} has successfully submitted their savings declaration for the year {data["startYear"]}-{data["endYear"]}. Please consider this for record-keeping and verification.

    Thank you for your prompt action.


    Best regards,
    {investment_obj.employee.company.company_name.title()}.                         
    """
                            content2={
                                'subject':f'{investment_obj.employee.user.username.title()} has successfully submitted the saving declaration for the year {data["startYear"]}-{data["endYear"]}',
                                'body':body,
                                'to_email':email
                            }
                            if check_alert_notification("Saving Declaration",'Form Submission', email=True): 
                                Util.send_email(content2)
                            
                            # HR/Admin Whatsapp notifications
                            try:
                                domain = f"{self.request.scheme}://{self.request.get_host()}/"
                                phone = obj['roles_employees__user__phone']
                                manager_data = {
                                        'phone_number': phone,
                                        'subject': 'Savings Declaration Submission',
                                        "body_text1":f"{investment_obj.employee.user.username.title()} has successfully submitted the saving declaration",
                                        'body_text2': f"For the year {data['startYear']}-{data['endYear']}",
                                        'url': f"{domain}savingdeclaration",
                                        "company_name":investment_obj.employee.company.company_name.title()
                                        }
                                if check_alert_notification("Saving Declaration",'Form Submission', whatsapp=True): 
                                    WhatsappMessage.whatsapp_message(manager_data)
                            except Exception as e:
                                logger.warning(f"Error while sending Whatsapp notificaton to {empl_name} in Submission of Savings Declaration: {e}")  
                            
                    except Exception as e:
                        print("Execption in sending Email to HR / Admin",e)
            investment_obj.income_from_previous_employer = data['incomeFromPreviousEmployer']
            investment_obj.tds_from_previous_employer = data['tdsFromPreviousEmployer']
            investment_obj.final_declared_amount = data.get('finalDeclaredAmount',0)
            if data.get("deletedAttachements"):
                investment_obj.attachments_set.filter(id__in=data['deletedAttachements'].split(",")).delete()
            if data.get('attachments'):
                    for file in data.get("attachments"):
                        Attachments.objects.create(
                            investment_declaration_id=investment_obj.id,
                            attachment=file,
                        )
            investment_obj.regime_type = regime_type
            investment_obj.save()
            return Response(
                {"data": {"status": "saving declaration updated successfully"}},
                status=status.HTTP_200_OK,
            )
        
        elif regime_type in [InvestmentDeclaration.OLD_TAX_REGIME, None]:
            # Initial Savings     
                               
            investment_obj.declaration_amount = data['declarationAmount']
            if data.get("status"):
                investment_obj.status = data['status']
                if int(data.get("status")) == 20:
                    investment_obj.submitted_date=timezone_now().date()
                    try:
                        employee_name = investment_obj.employee.user.username.title()
                        official_email = investment_obj.employee.official_email
                        emp_code = investment_obj.employee.work_details.employee_number
                        body = f"""
    Hello {employee_name} [{emp_code}],

    Your savings declaration has been successfully submitted for the year {data["startYear"]}-{data["endYear"]}. This email serves as confirmation of the receipt of your information.

    Your savings declaration documents are now available for secure access. Feel free to review them for transparency and accessibility

    Thank you for your prompt action.


    Best regards,
    {investment_obj.employee.company.company_name.title()}.                         
        """
                        content1={
                            'subject':f'Successful Submission of Savings Declaration for year {data["startYear"]}-{data["endYear"]}',
                            'body':body,
                            'to_email':official_email
                        }
                        if check_alert_notification("Saving Declaration",'Form Submission', email=True): 
                            Util.send_email(content1)
                    except Exception as e:
                        print("Execption in Sending email to Emp:",e)
                        
                    # employee Whatsapp notifications
                    try:
                        domain = f"{self.request.scheme}://{self.request.get_host()}/"
                        manager_data = {
                                'phone_number': investment_obj.employee.user.phone,
                                'subject': 'Savings Declaration Submission',
                                "body_text1":"Your savings declaration has been successfully submitted",
                                'body_text2': f"For the year {data['startYear']}-{data['endYear']}",
                                'url': f"{domain}savingdeclaration",
                                "company_name":investment_obj.employee.company.company_name.title()
                                }
                        if check_alert_notification("Saving Declaration",'Form Submission', whatsapp=True): 
                            WhatsappMessage.whatsapp_message(manager_data)
                    except Exception as e:
                        logger.warning(f"Error while sending Whatsapp notificaton to {investment_obj.employee.user.username} in Submission of Savings Declaration: {e}") 
                        
                        
                    try:
                        # Send Email to HR / Admin for record keeping
                        for obj in hr_and_admins:
                            empl_name = obj['roles_employees__user__username'].title()
                            email = obj['roles_employees__official_email']
                            emp_code = obj['roles_employees__work_details__employee_number']
                            body = f"""
    Dear {empl_name} [{emp_code}],

    We would like to inform you that {investment_obj.employee.user.username.title()} has successfully submitted their savings declaration for the year {data["startYear"]}-{data["endYear"]}. Please consider this for record-keeping and verification.

    Thank you for your prompt action.


    Best regards,
    {investment_obj.employee.company.company_name.title()}.                         
    """
                            content2={
                                'subject':f'{investment_obj.employee.user.username.title()} has successfully submitted the saving declaration for the year {data["startYear"]}-{data["endYear"]}',
                                'body':body,
                                'to_email':email
                            }
                            if check_alert_notification("Saving Declaration",'Form Submission', email=True): 
                                Util.send_email(content2)
                            
                            # HR/Admin Whatsapp notifications
                            try:
                                domain = f"{self.request.scheme}://{self.request.get_host()}/"
                                phone = obj['roles_employees__user__phone']
                                manager_data = {
                                        'phone_number': phone,
                                        'subject': 'Savings Declaration Submission',
                                        "body_text1":f"{investment_obj.employee.user.username.title()} has successfully submitted the saving declaration",
                                        'body_text2': f"For the year {data['startYear']}-{data['endYear']}",
                                        'url': f"{domain}savingdeclaration",
                                        "company_name":investment_obj.employee.company.company_name.title()
                                        }
                                if check_alert_notification("Saving Declaration",'Form Submission', whatsapp=True): 
                                    WhatsappMessage.whatsapp_message(manager_data)
                            except Exception as e:
                                logger.warning(f"Error while sending Whatsapp notificaton to {empl_name} in Submission of Savings Declaration: {e}")  
                            
                    except Exception as e:
                        print("Execption in sending Email to HR / Admin",e)
                if int(data.get("status")) == 30:
                    investment_obj.admin_resubmit_status=None
            investment_obj.income_from_previous_employer = data['incomeFromPreviousEmployer']
            investment_obj.tds_from_previous_employer = data['tdsFromPreviousEmployer']
            investment_obj.final_declared_amount = data.get('finalDeclaredAmount',0)
            if data.get("deletedAttachements"):
                investment_obj.attachments_set.filter(id__in=data['deletedAttachements'].split(",")).delete()
            if data.get('attachments'):
                    for file in data.get("attachments"):
                        Attachments.objects.create(
                            investment_declaration_id=investment_obj.id,
                            attachment=file,
                        )
            
            for dec_form in details:                
                if 's_form' not in dec_form:
                    declaration_form_qs = investment_obj.declaration_forms.filter(parentform_type_id=dec_form['p_id'])
                    if declaration_form_qs.exists():                        
                        declaration_form_obj = declaration_form_qs.first()
                        declaration_form_obj.declared_amount=dec_form.get('declaredAmount', 0)
                        declaration_form_obj.comments_from_employee=dec_form.get("commentsFromEmployee")
                        declaration_form_obj.comments_from_employer=dec_form.get("commentsFromEmployer")
                        declaration_form_obj.final_declared_amount=dec_form.get("finalDeclaredAmount", 0)
                        declaration_form_obj.save()
                    else:
                        declaration_form_obj = DeclarationForms.objects.create(
                            parentform_type_id=dec_form['p_id'],
                            declaration_id = investment_obj.id,
                            declared_amount=dec_form.get('declaredAmount', 0),
                            comments_from_employee=dec_form.get("commentsFromEmployee"),
                            comments_from_employer=dec_form.get("commentsFromEmployer"),
                            final_declared_amount=dec_form.get("finalDeclaredAmount", 0),
                        )

                    if 'deletedAttachements' in dec_form:
                        declaration_form_obj.attachments_set.filter(id__in=dec_form['deletedAttachements'].split(",")).delete()
                    if 'attachments' in dec_form:
                        for i in dec_form.get("attachments"):
                            Attachments.objects.create(
                                declaration_form_id=declaration_form_obj.id,
                                attachment=i,
                            )
                        
                else:
                    for sub_form in dec_form['s_form']:
                        declaration_form_qs = investment_obj.declaration_forms.filter(parentform_type_id=dec_form['p_id'], subform_type_id=sub_form['id'])
                        if declaration_form_qs.exists():
                            declaration_form_obj = declaration_form_qs.first()
                            declaration_form_obj.declared_amount=sub_form.get('declaredAmount', 0)
                            declaration_form_obj.comments_from_employee=sub_form.get("commentsFromEmployee")
                            declaration_form_obj.comments_from_employer=sub_form.get("commentsFromEmployer")
                            declaration_form_obj.final_declared_amount=sub_form.get("finalDeclaredAmount", 0)
                        else:
                            declaration_form_obj = DeclarationForms.objects.create(
                                parentform_type_id=dec_form['p_id'],
                                subform_type_id=sub_form['id'],
                                declaration_id = investment_obj.id,
                                declared_amount=sub_form.get('declaredAmount', 0),
                                comments_from_employee=sub_form.get("commentsFromEmployee"),
                                comments_from_employer=sub_form.get("commentsFromEmployer"),
                                final_declared_amount=sub_form.get("finalDeclaredAmount", 0),
                            )
                        declaration_form_obj.save()
                        if 'deletedAttachements' in sub_form:
                            declaration_form_obj.attachments_set.filter(id__in=sub_form['deletedAttachements'].split(',')).delete()
                        if 'attachments' in sub_form:
                            for i in sub_form.get("attachments"):
                                Attachments.objects.create(
                                    declaration_form_id=declaration_form_obj.id,
                                    attachment=i,
                                )
            investment_obj.regime_type =regime_type
            investment_obj.save()
            return Response(
                {"data": {"status": "saving declaration updated successfully"}},
                status=status.HTTP_200_OK,
            )


class InvestmentDeclarationStatusUpdateView(UpdateAPIView):
    """
    View to Update Employee/Employer Investment Declaration

    SURESH, 05.05.2023
    """

    serializer_class = InvestmentDeclarationDetailSerializer
    lookup_field = "id"
    queryset = InvestmentDeclaration.objects.all()


class EmployeeReimbursementAPIView(APIView):

    permission_classes = [permissions.IsAuthenticated]
    model = Reimbursement
    pagination_class = CustomPagePagination
    def post(self, request, *args, **kwargs):
        try:
            Reimbursement.objects.create(
                employee_id=request.data.get("emp_id"),
                type=request.data.get("type"),
                other_type=request.data.get("other_type"),
                expense_date=request.data.get("expense_date"),
                detail=request.data.get("detail"),
                employer_comment=request.data.get("employer_comment"),
                support_file=request.data.get("support_file"),
                amount=request.data.get("amount"),
                status = "Pending"
                )
            return Response({"msg":"Employee Reimbursment created Succesfully"},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"msg":str(e)},status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request, *args, **kwargs):
        params = request.query_params
        query={}
        if "status" in params:
            if params.get("status") in ["Approved","Pending","Rejected","Approved_Paid"]:
                query['status'] = params.get('status')
        if "type" in params:
            query['type'] = params.get('type')
        if "from_date" in params:
            query['expense_date__gte'] = params.get('from_date')
        if "to_date" in params:
            query['expense_date__lte'] = params.get('to_date')
        if "employee" in params:
            query['employee'] = params.get('employee') #employee = params.get("employee")
        if "company" in params:
            query['employee__company'] = params.get('company')
        paginator = self.pagination_class()
        qs = Reimbursement.objects.filter(**query, is_deleted=False).annotate(
            employee_number = F('employee__work_details__employee_number'),
            employee_name=Concat(
                "employee__first_name",
                Value(" "),
                "employee__middle_name",
                Value(" "),
                "employee__last_name",
                Value(" "),
            )).values("id","employee_name","employee","employee_number","type","other_type","expense_date","employer_comment",
                      "approval_date","detail","support_file","amount","approved_amount","status","created_at").order_by("-id")
        if ("download" in params) and (params['download']=="true"):
            df = pd.DataFrame(qs)
            df['created_at'] = df['created_at'].dt.tz_localize(None)
            df['created_at'] = df['created_at'].dt.date
            file_name = "reimbursement_report.xlsx"
            df.rename(columns = {'employee_name':'Name', 'employee':'ID','created_at':'Apply Date','detail':'Reason','amount':'Declared Amount',}, inplace = True)
            df = df [['Name', 'ID', 'Apply Date', 'expense_date', 'approval_date', 'type', 'Reason', 'employer_comment', 'Declared Amount', 'approved_amount', 'status']]
            return excel_converter(df,file_name)

        page = paginator.paginate_queryset(qs, request)

        return Response(
            success_response(
                paginator.get_paginated_response(page), "Successfully fetched Saving declaration Data", 200
            ),
            status=status.HTTP_200_OK
        )

    def put(self, request,*args, **kwargs):
        try:
            reimb_obj = Reimbursement.objects.get(id=kwargs.get('id'))
            if request.data.get("type"):
                reimb_obj.type = request.data.get("type")
            if request.data.get("other_type"):
                reimb_obj.other_type = request.data.get("other_type")
            if request.data.get("expense_date"):
                reimb_obj.expense_date = request.data.get("expense_date")
            if request.data.get("detail"):
                reimb_obj.detail = request.data.get("detail")
            if request.data.get("support_file"):
                reimb_obj.support_file = request.data.get("support_file")
            if request.data.get("amount"):
                reimb_obj.amount = request.data.get("amount")
            if request.data.get("approved_amount"):
                reimb_obj.approved_amount = request.data.get("approved_amount")
            if request.data.get("status"):
                reimb_obj.status = request.data.get("status")
            if request.data.get("employer_comment"):
                reimb_obj.employer_comment = request.data.get("employer_comment")
            if request.data.get("status") and (request.data.get("status") in ["Approved","Approved_Paid"]):
                reimb_obj.approval_date = timezone.now().date().strftime("%Y-%m-%d")
            reimb_obj.save()
                
            return Response({"msg":"Employee Reimbursment Updated Successfully"},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"msg":str(e)},status=status.HTTP_400_BAD_REQUEST) 

    def delete(self, request,*args, **kwargs):
        try:
            reimb_obj = Reimbursement.objects.get(id=kwargs.get('id'))
            reimb_obj.is_deleted = True
            reimb_obj.save()            
            return response.Response(
            {
                'message': 'Employee Reimbursement Deleted Successfully'
            },
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(str(e), 'Some thing went wrong', 404),
                status=status.HTTP_404_NOT_FOUND
            )


# class AttachmentListCreateView(AbstractListAPIView):
#     """
#     Investment Declaration Attachment View

#     """

#     serializer_class = AttachmentSerializer
#     queryset = Attachment.objects.filter(
#         content_type=ContentType.objects.get_for_model(DeclarationForms)
#     )
#     filterset_fields = ["object_id"]

#     def post(self, request):
#         """
#         Default Post Method

#         """
#         data = request.data.copy()
#         data["content_type"] = {
#             "app_label": "investment_declaration",
#             "model": "DeclarationForms",
#         }

#         if isinstance(data["object_id"], str):
#             data["object_id"] = int(data["object_id"])

#         objs = []

#         for document in data.pop("documents"):
#             data["document"] = document
#             serializer = self.serializer_class(data=data)
#             if serializer.is_valid(raise_exception=True):
#                 objs.append(serializer.save())

#         return Response(
#             data={
#                 "message": "Attachments Created",
#                 "data": self.serializer_class(objs, many=True).data,
#                 "status": status.HTTP_201_CREATED,
#             },
#             status=status.HTTP_201_CREATED,
#         )


class AttachmentDeleteView(DestroyAPIView):
    lookup_field = "object_id"
    lookup_url_kwarg = "id"
    queryset = Attachment.objects.all()

    # @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        try:
            sid = transaction.set_autocommit(autocommit=False)
            objs = self.get_queryset()
            for obj in objs:
                obj.delete()
            transaction.commit()
            return Response(
                data={
                    "message": f"{objs.count()} attachments deleted !!",
                    "status": status.HTTP_200_OK,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            transaction.rollback(sid)
            return Response(
                data={
                    "error": e,
                    "status": status.HTTP_410_GONE,
                },
                status=status.HTTP_410_GONE,
            )


# class InvestmentDeclarationCreateView(AbstractListCreateAPIView):
#     """
#     View to create Employee Saving Declaration

#     SURESH, 03.05.2023
#     """

#     serializer_class = InvestmentDeclarationSerializer
#     filterset_fields = ["employee__company", "employee", "start_year", "end_year"]
#     queryset = InvestmentDeclaration.objects.all()

# By Uday Shankar

class InvestmentDeclarationUpdateStatusViewSet(UpdateAPIView):
# class InvestmentDeclarationOnlyStatusViewSet(viewsets.ModelViewSet):
    
    """
    UDAY, 05.06.2023
    """
    
    serializer_class = InvestmentDeclarationStatusChangeSerializer
    lookup_field = "id"
    queryset = InvestmentDeclaration.objects.all()
    
    # def getStatus():
    #     queryset = InvestmentDeclaration.objects.all()
    #     serializer = InvestmentDeclarationStatusChangeSerializer(data=queryset)
    #     return Response({"message":serializer}, status=status.HTTP_202_ACCEPTED)
    
    
# @api_view(['PATCH'])
# def InvestmentDeclarationEntriesUpdateView(request,employee_id):
#     """
#     Get detail based on employee id, or Update detail based on object id
#     """
#     try:
#         data = InvestmentDeclaration.objects.get(id=employee_id) 
#         serializer_class = InvestmentDeclarationEnteriesUpdateSerializer(data, data=request.data, partial=True)       
#         if serializer_class.is_valid():     
#             # data = InvestmentDeclaration.objects.filter(id=employee_id).update(status=request.data)        
#             serializer_class.save()
#             return Response({"message":"Status Updated"}, status=status.HTTP_202_ACCEPTED)
#             return Response({"message":"Status not Updated"}, status=status.HTTP_400_BAD_REQUEST)  
#         else:
#             return Response({"message":"No data found."}, status=status.HTTP_400_BAD_REQUEST) 
#     except Exception as e:
#         return Response({"message":"Something went wrong."}, status.HTTP_400_BAD_REQUEST)          


def get_emp_salary_details(employee_obj):

    financial_start, financial_end = get_financial_dates_start_and_end()
    previous_income = previous_tds = employee_ctc = 0

    if hasattr(employee_obj, 'salary_details'):
        employee_salary_obj = employee_obj.salary_details
        previous_income = employee_salary_obj.previous_income
        previous_tds = employee_salary_obj.previous_tds
        employee_ctc = employee_salary_obj.ctc


    emp_gross_yearly = ctc_to_gross_per_year(employee_ctc)
    existing_emp_payrolls = employee_obj.emp_payroll_info.filter(month_year__gte=financial_start, month_year__lte=financial_end,is_processed=True)
    
    days_in_financial_years = (financial_end - financial_start).days + 1
    daily_gross = emp_gross_yearly/days_in_financial_years
    if not existing_emp_payrolls:
        existing_earned_gross = 0
        if employee_obj.date_of_join < financial_start:
            index = financial_start
        else:
            index = employee_obj.date_of_join
        days_left = (financial_end - index).days + 1
        projected_gross = days_left * daily_gross
    else:
        '''
        #not using as to not do by days said by use months
        existing_earned_gross = sum(existing_emp_payrolls.values_list('earned_gross', flat=True))
        last_payroll = existing_emp_payrolls.order_by('month_year').last().month_year + relativedelta(months=1)
        days_left = (financial_end - last_payroll).days + 0.5
        projected_gross = days_left * daily_gross
        '''

        existing_earned_gross = sum(existing_emp_payrolls.values_list('earned_gross', flat=True))
        months_in_year = 12
        existing_months = existing_emp_payrolls.count()
        months_remaining = months_in_year - existing_months
        monthly_gross = emp_gross_yearly / 12
        projected_gross = months_remaining * monthly_gross


    total_gross = float(existing_earned_gross) + projected_gross
    total_income = float(previous_income) + total_gross
    return {"previous_income":round(previous_income), "previous_tds":round(previous_tds), "total_gross":round(total_gross), "total_income":round(total_income)}
class EmployeePreviousSalaryDetails(APIView):
    model = InvestmentDeclaration

    def get(self, request, *args, **kwargs):
        """
        i/p employee id
        o/p previous income, previous tds, total gross, total income
        """
        try:
            emp_id = request.query_params.get('emp_id')
            if not emp_id:
                emp_id = request.user.employee_details.first().id
            emp_obj = Employee.objects.filter(id=emp_id)
            if not emp_obj:
                return  Response("Employee id object does not exist")
            employee_obj = emp_obj.first()
            return Response (get_emp_salary_details(employee_obj))
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )


class DeclarationHra(APIView):
    """
    this class is used to return the hra on conditions
    i/p emp_id, hra_amount
    o/p 3 hra's and min value
    """
    model = InvestmentDeclaration
    def post(self, request):
        try:
            emp_id = request.data.get('emp_id')
            hra_amount = request.data.get('hra_amount') #must give in year
            if hra_amount in ["", None]:
                hra_amount = 0.0
            hra_amount = float(hra_amount)
            emp = Employee.objects.filter(id = emp_id)
            if not emp:
                return Response("employee id does not exist")
            if emp.count() !=1:
                return Response("employees came more than one")
            emp = emp.first()
            if emp.work_details.employee_status != 'Active':
                return Response("employee status is not Active")
            basic_obj = emp.company.pay_salary_comp.filter(component_name="Basic")
            if not basic_obj:
                return Response("Basic payroll salary component not found")
            basic_obj = basic_obj.first()
            hra_obj = emp.company.pay_salary_comp.filter(component_name="HRA")
            if not hra_obj:
                return Response("HRA payroll salary component not found")
            hra_obj = hra_obj.first()
            hras={}
            #case1
            #(Actual rent paid) – (10% of the basic salary)
            emp_ctc = emp.salary_details.ctc
            emp_gross = ctc_to_gross_per_year(emp_ctc)
            basic_amount = emp_gross * (basic_obj.pct_of_basic/100)
            pct_10_basic = basic_amount * (10/100)
            value = hra_amount - pct_10_basic
            if value<0:
                value=0
            hras.update(**{'case1':round(value)})
            #case2
            #Actual HRA offered by the employer
            actual_hra = round(basic_amount * (hra_obj.pct_of_basic/100))
            hras.update(**{"case2":actual_hra})
            #case3
            #40% of the basic salary  ==> 50|40 will be there said to take 40
            val3 = round(basic_amount * (40/100))
            hras.update(**{"case3":val3})

            hras['min_hra'] = min(hras.values())
            return Response(hras)
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "Error in server", 400),
                status=status.HTTP_404_NOT_FOUND)

class RegimeSelect(APIView):
    """
    this class is used to idetify the proper regime
    i/p old_regime_total_tax, new_regime_total_tax
    o/p best suitable with diff
    """
    model = InvestmentDeclaration
    def checks(self, regimes, health_cess):
        if not regimes:
            return Response("No Regimes found")
        elif regimes.count != 2:
            return Response("regimes count is other than 2")
        if not health_cess:
            return Response("No Healthcess found")
        elif health_cess.count != 1:
            return Response("Health Cess is other than 2")


    def post(self, request):
        try:
            taxes = {}
            old_regime_total_tax = request.data.get('old_regime_total_tax')
            if old_regime_total_tax in ["", None]:
                old_regime_total_tax = 0.0
            new_regime_total_tax = request.data.get('new_regime_total_tax')
            if new_regime_total_tax in ["", None]:
                new_regime_total_tax = 0
            old_regime_total_tax = float(old_regime_total_tax)
            new_regime_total_tax = float(new_regime_total_tax)
            regimes = Regime.objects.all()
            health_cess = HealthEducationCess.objects.all()
            self.checks(regimes, health_cess)
            for regime in regimes:
                tax_regime = {
                        int(key): value for key, value in regime.salary_range_tax.items()
                            }
                if regime.regime_name.lower() == "old":
                    if  old_regime_total_tax <= 500000:
                        taxes['old_tax'] = 0
                    else:
                        taxes['old_tax'] = round(calculate_tax_for_regime(old_regime_total_tax, tax_regime, health_cess.first().health_education_cess)['total_tax'])
                elif regime.regime_name.lower() == 'new':
                    if new_regime_total_tax <= 700000:
                        taxes['new_tax'] = 0
                    else:
                        taxes['new_tax'] = round(calculate_tax_for_regime(new_regime_total_tax, tax_regime, health_cess.first().health_education_cess)['total_tax'])
                else:
                    return Response(f"some other regime name came of {regime.regime_name}")
            if taxes['old_tax']>taxes['new_tax']:
                taxes['msg'] = f"You Should opt for New Regime as it will provide you benefit of Rs {round(taxes['old_tax'] - taxes['new_tax'])} over Old Regime"
            elif taxes['old_tax']<taxes['new_tax']:
                taxes['msg'] = f"You Should opt for Old Regime as it will provide you benefit of Rs {round(taxes['new_tax'] - taxes['old_tax'])} over New Regime"
            elif taxes['old_tax']==taxes['new_tax']:
                taxes['msg']='Both are of same taxes'
            else:
                taxes['msg']='some thing comparision wrong'

            return Response(taxes)

        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "Error in server", 400),
                status=status.HTTP_404_NOT_FOUND)

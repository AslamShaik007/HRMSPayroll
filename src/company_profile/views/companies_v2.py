import pandas as pd
import traceback
import json
from deepdiff import DeepDiff
import re
from dateutil.parser import parse

from django.db import models as db_models
from django.contrib.postgres.aggregates import ArrayAgg
from django.conf import settings

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    AuditorDetails,
    BankDetails,
    CompanyDetails,
    CompanyDirectorDetails,
    CustomAddressDetails,
    SecretaryDetails,
    Departments,
    SubDepartments,
    CompanyGrades,
    Designations,
    LoggingRecord,
    EntityTypes
)

from core.utils import success_response, error_response, search_filter_decode, excel_converter, timezone_now, SplitPart, localize_dt, strftime
from core.custom_paginations import CustomPagePagination
from HRMSApp.custom_permissions import IsHrAdminPermission
import datetime
from directory.models import Employee, EmployeeReportingManager
from leave.models import LeaveRules

from HRMSApp.utils import Util
from core.utils import timezone_now, get_domain,email_render_to_string
from HRMSApp.models import Registration
from HRMSProject.multitenant_setup import MultitenantSetup
from alerts.utils import check_alert_notification
import logging
logger = logging.getLogger("django")

class CompanyDetailsAPIViewV2(APIView):
    model = CompanyDetails
    
    def get(self, request, *args, **kwargs):
        MultitenantSetup().create_to_connection(request)
        company_id = kwargs.get("id")
        if not company_id:
            try:
                company_id = request.user.employee_details.first().company_id
            except Exception as e:
                return Response(
                    error_response(e, 'Some thing went wrong', 404),
                    status=status.HTTP_404_NOT_FOUND
                )
        qs = self.model.objects.filter(id=company_id, is_deleted=False)
        if not qs.exists():
            return Response(
                error_response(
                    "", "Company Not exists or deleted", 404
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        company_data = qs.prefetch_related('statutorydetails').annotate(
            company_size = db_models.F('company__company_size')).values(
            'id', 'company_name', 'company_image', 'brand_name', 'web_site','industry_type',
            'domain_name', 'linked_in_page', 'facebook_page', 'twitter_page', 'registered_adress_line1', 'registered_adress_line2', 'registered_country', 
            'registered_state', 'registered_city', 'registered_pincode', 'corporate_adress_line1', 'corporate_adress_line2', 'corporate_country', 
            'corporate_state', 'corporate_city', 'corporate_pincode', 'payslip_watermark', 'watermark_status','company_size','is_brand_name_updated',
            'payslip_signature', 'signature_status', 'decimals', 'round_offs', 'payslip_hr_email', 'payslip_hr_phone'
        )
        statutory_details = qs.first().statutorydetails_set.filter(is_deleted=False).annotate(
            entityType=db_models.expressions.Func(
                db_models.Value("id"), 'entity_type_id',
                db_models.Value("entityType"), 'entity_type__entity_type',
                db_models.Value("value"), db_models.Case(
                    db_models.When(entity_type__entity_type=10, then=db_models.Value('Private Limited Company')) ,   
                    db_models.When(entity_type__entity_type=20, then=db_models.Value('Public Limited Company')) ,   
                    db_models.When(entity_type__entity_type=30, then=db_models.Value('Limited Liability Partnership')) ,   
                    db_models.When(entity_type__entity_type=40, then=db_models.Value('Partnership')) ,   
                    db_models.When(entity_type__entity_type=50, then=db_models.Value('Sole Proprietorship')) ,   
                    db_models.When(entity_type__entity_type=60, then=db_models.Value('Nonprofit Organisation')) ,   
                    db_models.When(entity_type__entity_type=70, then=db_models.Value('Society')) ,   
                    db_models.When(entity_type__entity_type=80, then=db_models.Value('Trust')) ,   
                    db_models.When(entity_type__entity_type=90, then=db_models.Value('Others')) ,
                    default=db_models.Value(""), output_field=db_models.CharField()
                ),
                function='jsonb_build_object',
                output_field=db_models.JSONField()
            )
        ).values(
            "id", "company", "entityType", "tan_number", "date_of_incorp", "pan_number",
            "pan_image_path", "cin_number", "cin_image_path", "gst_number", "gst_image_path", "is_deleted","other_entity_type","tds_circle_code"
        )
        MultitenantSetup().go_to_old_connection(request)
        return Response(
            success_response(
                {
                    "company_data": company_data.first(),
                    "statutory_details": statutory_details,

                },
                "Successfully Fetched Company Details", 200    
            ),
            status=status.HTTP_200_OK
        )

class CompanyBankDetailsV2(APIView):
    model = BankDetails
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        params = request.query_params
        company_id = kwargs.get("id")
        if not company_id:
            try:
                company_id = request.user.employee_details.first().company_id
            except Exception as e:
                return Response(
                    error_response(e, 'Some thing went wrong', 404),
                    status=status.HTTP_404_NOT_FOUND
                )
        q_filters = db_models.Q(company_id=company_id, is_deleted=False)
        if 'id' in params:
            q_filters &= db_models.Q(id=params["id"])
        paginator = self.pagination_class()
        
        data = self.model.objects.filter(q_filters).annotate(
            accountType=db_models.expressions.Func(
                db_models.Value("id"), 'account_type_id',
                db_models.Value("accountType"), 'account_type__account_type',
                db_models.Value("value"), db_models.Case(
                    db_models.When(account_type__account_type=10, then=db_models.Value('Current Account')) ,   
                    db_models.When(account_type__account_type=20, then=db_models.Value('Savings Account')) ,   
                    db_models.When(account_type__account_type=30, then=db_models.Value('Salary Account')) ,   
                    db_models.When(account_type__account_type=40, then=db_models.Value('Fixed Deposit Account')) ,   
                    db_models.When(account_type__account_type=50, then=db_models.Value('Recurring Deposit Account')) ,   
                    db_models.When(account_type__account_type=60, then=db_models.Value('Non-Resident Indian Account')) ,   
                    db_models.When(account_type__account_type=61, then=db_models.Value('Non-Resident Ordinary Account')) ,   
                    db_models.When(account_type__account_type=62, then=db_models.Value('Non-Resident External Account')) ,   
                    db_models.When(account_type__account_type=70, then=db_models.Value('Foreign Currency Non-Resident Account')) ,
                    default=db_models.Value(""), output_field=db_models.CharField()
                ),
                function='jsonb_build_object',
                output_field=db_models.JSONField()
            )    
        ).values(
            "id", "company", "account_title", "bank_name", "city", "branch_name", "ifsc_code",
            "accountType", "account_number", "bic", "is_default", "is_deleted",
        ).order_by('-id')
        page = paginator.paginate_queryset(data, request)

        return Response(
            success_response(
                paginator.get_paginated_response(page),
                "Successfully fetched Bank Details", 200
            ),
            status=status.HTTP_200_OK
        )

class CompanySecretaryDetailsV2(APIView):
    model = SecretaryDetails
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        params = request.query_params
        company_id = kwargs.get("id")
        if not company_id:
            try:
                company_id = request.user.employee_details.first().company_id
            except Exception as e:
                return Response(
                    error_response(e, 'Some thing went wrong', 404),
                    status=status.HTTP_404_NOT_FOUND
                )
        q_filters = db_models.Q(company_id=company_id, is_deleted=False)
        if 'id' in params:
            q_filters &= db_models.Q(id=params["id"])
        paginator = self.pagination_class()
        data = self.model.objects.filter(q_filters).values(
            "id", "company", "secretary_name", "secretary_email", "secretary_phone", "is_deleted"
        ).order_by('-id')
        page = paginator.paginate_queryset(data, request)
        return Response(
            success_response(
                paginator.get_paginated_response(page), "Successfully fetched SecretaryDetails", 200
            ),
            status=status.HTTP_200_OK
        )

class CompanyDirectoryDetailsV2(APIView):
    model = CompanyDirectorDetails
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        params = request.query_params
        company_id = kwargs.get("id")
        if not company_id:
            try:
                company_id = request.user.employee_details.first().company_id
            except Exception as e:
                return Response(
                    error_response(e, 'Some thing went wrong', 404),
                    status=status.HTTP_404_NOT_FOUND
                )
        q_filters = db_models.Q(company_id=company_id, is_deleted=False)
        if 'id' in params:
            q_filters &= db_models.Q(id=params["id"])
        paginator = self.pagination_class()
        data = self.model.objects.filter(q_filters).values(
            "id", "company", "director_name", "director_mail_id", "din_number", "director_phone", "is_deleted"
        ).order_by('-id')
        page = paginator.paginate_queryset(data, request)
        return Response(
            success_response(
                paginator.get_paginated_response(page), "Successfully fetched DirectorDetails", 200
            ),
            status=status.HTTP_200_OK
        )

class CompanyAuditorDetailsV2(APIView):
    model = AuditorDetails
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        params = request.query_params
        company_id = kwargs.get("id")
        if not company_id:
            try:
                company_id = request.user.employee_details.first().company_id
            except Exception as e:
                return Response(
                    error_response(e, 'Some thing went wrong', 404),
                    status=status.HTTP_404_NOT_FOUND
                )
        q_filters = db_models.Q(company_id=company_id, is_deleted=False)
        if 'id' in params:
            q_filters &= db_models.Q(id=params["id"])
        paginator = self.pagination_class()
        data = self.model.objects.filter(q_filters).annotate(
            auditorType=db_models.expressions.Func(
                db_models.Value("id"), 'auditor_type_id',
                db_models.Value("auditorType"), 'auditor_type__auditor_type',
                db_models.Value("value"), db_models.Case(
                    db_models.When(auditor_type__auditor_type=10, then=db_models.Value('Internal')),   
                    db_models.When(auditor_type__auditor_type=20, then=db_models.Value('Statutory')),
                    default=db_models.Value(""), output_field=db_models.CharField()
                ),
                function='jsonb_build_object',
                output_field=db_models.JSONField()
            )    
        ).values(
            "id", "company", "auditor_name", "auditor_email", "auditorType", "auditor_phone", "is_deleted",
        ).order_by('-id')
        page = paginator.paginate_queryset(data, request)
        return Response(
            success_response(
                paginator.get_paginated_response(page), "Successfully fetched AuditorDetails", 200
            ),
            status=status.HTTP_200_OK
        )

class CompanyCustomAddressDetailsV2(APIView):
    model = CustomAddressDetails
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        MultitenantSetup().create_to_connection(request)
        params = request.query_params
        company_id = kwargs.get("id")
        if not company_id:
            try:
                company_id = request.user.employee_details.first().company_id
            except Exception as e:
                return Response(
                    error_response(e, 'Some thing went wrong', 404),
                    status=status.HTTP_404_NOT_FOUND
                )
        q_filters = db_models.Q(company_id=company_id, is_deleted=False)
        if 'id' in params:
            q_filters &= db_models.Q(id=params["id"])
        paginator = self.pagination_class()
        data = self.model.objects.filter(q_filters).values(
            "id", "company", "address_title", "address_line1", "address_line2", "country", "state", "city", "pincode", "is_deleted"
        ).order_by('-id')
        page = paginator.paginate_queryset(list(data), request)
        MultitenantSetup().go_to_old_connection(request)
        return Response(
            success_response(
                paginator.get_paginated_response(page), "Successfully fetched Custom Address", 200
            ),
            status=status.HTTP_200_OK
        )

class CompanyDepartmentDetailsV2(APIView):
    model = Departments
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        company_id = kwargs.get("id")
        if not company_id:
            try:
                company_id = request.user.employee_details.first().company_id
            except Exception as e:
                return Response(
                    error_response(e, 'Some thing went wrong', 404),
                    status=status.HTTP_404_NOT_FOUND
                )
        MultitenantSetup().create_to_connection(request)
        try:
            q_filters = db_models.Q(company_id=company_id, is_deleted=False)
            paginator = self.pagination_class()
            # db_models.Count('sub_departments__department__company__employees__id',
            #                                         filter=db_models.Q(
            #                                             sub_departments__department__company__employees__is_deleted=False,
            #                                             sub_departments__department__company__employees__work_details__sub_department_id=db_models.F('id')
            #                                         )),
            # data = self.model.objects.filter(q_filters).prefetch_related('sub_departments').annotate(
            #     no_of_employees=db_models.Count('company__employees__id', filter=db_models.Q(company__employees__is_deleted=False), distinct=True),
            #     subDepartments=ArrayAgg(
            #         db_models.expressions.Func(
            #             db_models.Value('id'), 'sub_departments__id',
            #             db_models.Value('name'), 'sub_departments__name',
            #             db_models.Value('no_of_employees'), db_models.expressions.Func(db_models.Value("")),
                        
            #             function='jsonb_build_object',
            #             output_field=db_models.JSONField()
            #         ),
            #         distinct=True,
            #         filter=db_models.Q(is_deleted=False, sub_departments__is_deleted=False),
            #     )
            # ).values(
            #     'company', 'id', 'is_deleted', 'name', 'no_of_employees', 'subDepartments'
            # )
            if 'search_filter' in request.query_params:
                q_filters &= db_models.Q(
                    name__icontains=search_filter_decode(request.query_params.get('search_filter'))
                )
            data = self.model.objects.filter(q_filters).prefetch_related('sub_departments').annotate(
                    no_of_employees=db_models.Count('company__employees__id', filter=db_models.Q(
                        company__employees__is_deleted=False, company__employees__work_details__department_id=db_models.F('id')
                    ), distinct=True),
                    subDepartments=ArrayAgg('sub_departments__id', filter=db_models.Q(sub_departments__is_deleted=False), distinct=True)
                ).values('id', 'company', 'name', 'no_of_employees', 'subDepartments').order_by('-id')
            page = paginator.paginate_queryset(data, request)
            data_df = pd.DataFrame(page,
                columns=('id', 'company', 'name', 'no_of_employees', 'subDepartments')
            )
            if len(data_df) > 0:
                data_df.subDepartments = data_df.apply(
                    lambda x: list(SubDepartments.objects.filter(id__in=x['subDepartments']).annotate(
                        no_of_employees=db_models.Count('department__company__employees__id',
                                                        filter=db_models.Q(
                                                            department__company__employees__is_deleted=False,
                                                            department__company__employees__work_details__sub_department_id=db_models.F('id')
                                                        ),
                                                        distinct=True)
                        ).values('id', 'name', 'is_deleted', 'no_of_employees')) if len(x.get('subDepartments', [])) > 0 else list(
                            Departments.objects.filter(
                                id=x['id']
                            ).annotate(
                                no_of_employees=db_models.Count('company__employees__id', filter=db_models.Q(
                                                            company__employees__is_deleted=False,
                                                            company__employees__work_details__department_id=db_models.F('id')
                                                        ),
                                                        distinct=True)
                            ).values('no_of_employees')
                        ), axis=1
                )
            MultitenantSetup().go_to_old_connection(request)
            return Response(
                success_response(
                    paginator.get_paginated_response(data_df.to_dict('records')), "Successfully fetched Departments", 200
                ),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            MultitenantSetup().go_to_old_connection(request)
            return Response(success_response(
                   [], "Successfully fetched Departments", 200
                ),
            )
       


class CompanyDesignationDetailsV2(APIView):
    model = Designations
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        company_id = kwargs.get("id")
        if not company_id:
            try:
                company_id = request.user.employee_details.first().company_id
            except Exception as e:
                return Response(
                    error_response(e, 'Some thing went wrong', 404),
                    status=status.HTTP_404_NOT_FOUND
                )
        q_filters = db_models.Q(company_id=company_id, is_deleted=False)
        paginator = self.pagination_class()
        if 'search_filter' in request.query_params:
            q_filters &= db_models.Q(
                name__icontains=search_filter_decode(request.query_params.get('search_filter'))
            )
        data = self.model.objects.filter(q_filters).annotate(
            no_of_employees=db_models.Count('company__employees__id',
                                            filter=db_models.Q(
                                                company__employees__is_deleted=False,
                                                company__employees__work_details__designation_id=db_models.F('id')
                                                ), distinct=True),
        ).values(
            'company', 'id', 'is_deleted', 'name', 'no_of_employees'
        ).order_by('-id')
        page = paginator.paginate_queryset(data, request)
        return Response(
            success_response(
                paginator.get_paginated_response(page), "Successfully fetched Designations", 200
            ),
            status=status.HTTP_200_OK
        )



class CompanyGradeDetailsV2(APIView):
    model = CompanyGrades
    pagination_class = CustomPagePagination
    
    def get(self, request, *args, **kwargs):
        company_id = kwargs.get("id")
        if not company_id:
            try:
                company_id = request.user.employee_details.first().company_id
            except Exception as e:
                return Response(
                    error_response(e, 'Something went wrong', 404),
                    status=status.HTTP_404_NOT_FOUND
                )
        q_filters = db_models.Q(company_id=company_id, is_deleted=False)
        paginator = self.pagination_class()
        if 'search_filter' in request.query_params:
            q_filters &= db_models.Q(
                grade__icontains=search_filter_decode(request.query_params.get('search_filter'))
            )
        data = self.model.objects.filter(q_filters).annotate(
            no_of_employees=db_models.Count('company__employees__id',
                                            filter=db_models.Q(
                                                company__employees__is_deleted=False,
                                                company__employees__work_details__employee_grade_id=db_models.F('id')
                                                ), distinct=True),
        ).values(
            'company', 'id', 'is_deleted', 'grade', 'no_of_employees'
        ).order_by('id')
        page = paginator.paginate_queryset(data, request)
        return Response(
            success_response(
                paginator.get_paginated_response(page), "Successfully fetched Grades", 200
            ),
            status=status.HTTP_200_OK
        )
class LoggingRecordsAPIViewV2(APIView):

    model = LoggingRecord
    pagination_class = CustomPagePagination
    # permission_classes = [IsHrAdminPermission]

# class tt:
    def clean_list(self,list_data):
        try:
            keys_to_remove = ["id", "is_deleted","created_at", "updated_at", "created_by_id", "updated_by_id","employee_id","company_id"]
            cleaned_list = [{k: v for k, v in item.items() if k not in keys_to_remove} for item in list_data]
            result_string = ', '.join([f"{k}: {v}" for d in cleaned_list for k, v in d.items()])
            return result_string
        except:
            return None
        
        
    def parse_json(self, x):
        try:
            return json.loads(x)
        except:
            return None
    
    def generate_old_new_data(self, changes, key_type):
        try:
            key_val = f'{key_type}_value' 
            op_str = ""
            if 'values_changed' in changes:
                op_str += ", ".join([f"""{i.split("['")[1].split("']")[0]}:  {changes['values_changed'][i][key_val]}""" for i in changes['values_changed']])
            if 'type_changes' in changes:
                tp_changes= ", ".join([f"""{i.split("['")[1].split("']")[0]}:  {changes['type_changes'][i][key_val]}""" for i in changes['type_changes']])
                op_str = op_str+','+tp_changes
            return "Nothing Updated" if re.sub(r'updated_at:[^,]+', '', op_str)=="" else op_str
        except Exception as e:
            return None
    def remove_keys(self,data_string):
        try:
            pairs = [pair.strip() for pair in data_string.split(',')]
            if not ':' in pairs[0]:
                return data_string
            data_dict = {}
            for pair in pairs:
                key, value = pair.split(':', 1)
                data_dict[key.strip()] = value.strip()
            try:
                if 'updated_at' in data_dict:
                    # print("assfdsfdfsd:",data_dict['updated_at'])
                    timestamp_obj = datetime.datetime.strptime(data_dict['updated_at'], "%Y-%m-%d %H:%M:%S.%f%z")
                    # formatted_timestamp = timestamp_obj.strftime("%Y-%m-%d %I:%M:%S %p")
                    timestamp_obj = localize_dt(timestamp_obj, settings.TIME_ZONE)
                    formatted_timestamp = parse(str(timestamp_obj)).strftime('%d-%m-%Y %I:%M %p')
                    # print("formatted_timestamp:",formatted_timestamp)
                    data_dict['updated_at']=formatted_timestamp
            except Exception as e:
                pass 
            if 'updated_by_id' in data_dict:
                del data_dict['updated_by_id']
            # if 'created_at' in data_dict:
            #     del data_dict['created_at']
            modified_data_string = ", ".join([f"{key}: {value}" for key, value in data_dict.items()])
            return modified_data_string
        except Exception as e:
            pass
    
    def get(self, request, *args, **kwargs):
        params = request.query_params
        from_date = params.get("from_date")
        to_date = params.get("to_date")
        try:
            if from_date > to_date:
                return Response(
                        error_response("To Date should be greater than From date", "To Date should be greater than From date", 404),
                        status=status.HTTP_404_NOT_FOUND
                    )
            if not (from_date and to_date):
                return Response(
                        error_response("from date and to date are Required", "from date and to date are Required", 404),
                        status=status.HTTP_404_NOT_FOUND
                    )
            if (datetime.datetime.strptime(to_date, "%Y-%m-%d") - datetime.datetime.strptime(from_date, "%Y-%m-%d")).days > 31:
                return Response(
                        error_response("from date and to date cant be more than month", 404),
                        status=status.HTTP_404_NOT_FOUND
                    )
            q_filter = db_models.Q(created_at__date__range=[from_date, to_date], method__in=["PUT","PATCH","POST","DELETE"])
            paginator = self.pagination_class()
            if "employee_name" in params:
                q_filter &= db_models.Q(user__username__icontains=params.get("employee_name"))
            if "method" in params:
                q_filter &= db_models.Q(method__icontains = params.get("method"))
            if "search_filter" in params:
                q_filter &= (
                db_models.Q(user__username__icontains=search_filter_decode(params.get("search_filter")))
                # db_models.Q(payload__icontains=params.get("search_filter")) |
                # db_models.Q(company_name__icontains=params.get("search_filter")) |
                # db_models.Q(end_point__icontains=params.get("search_filter")) |
                # db_models.Q(method__icontains = params.get("search_filter"))
            )
            if "module_name" in params:
                q_filter &= db_models.Q(end_point__icontains = params.get("module_name"))
            data = self.model.objects.filter(q_filter).annotate(
                changed_data_at=SplitPart(db_models.F('end_point'), db_models.Value(':82'), db_models.Value(2)),
                module_name=db_models.Case(
                    db_models.When(end_point__icontains='api/user/', then=db_models.Value('Login')),
                    db_models.When(end_point__icontains='api/roles/', then=db_models.Value('Settings')),
                    db_models.When(end_point__icontains='api/company/', then=db_models.Value('Company Profile')),
                    db_models.When(end_point__icontains='api/directory/', then=db_models.Value('Employee Management')),
                    db_models.When(end_point__icontains='api/pss_calendar/', then=db_models.Value('Calendar')),
                    db_models.When(end_point__icontains='api/leave/', then=db_models.Value('Leave')),
                    db_models.When(end_point__icontains='api/attendance/', then=db_models.Value('Attendance')),
                    db_models.When(end_point__icontains='api/performance_management/', then=db_models.Value('Performance Review')),
                    db_models.When(end_point__icontains='api/investment_declaration/', then=db_models.Value('Saving Declaration')),
                    db_models.When(end_point__icontains='api/payroll/', then=db_models.Value('Payroll')),
                    default=db_models.Value('-'),
                    output_field=db_models.CharField()
                ),
                action = db_models.Case(
                    db_models.When(method='PUT', then=db_models.Value('Updated')),
                    db_models.When(method ='PATCH', then=db_models.Value('Updated')),
                    db_models.When(method ='POST', then=db_models.Value('Created')),
                    db_models.When(method ='DELETE', then=db_models.Value('Deleted')),
                    default=db_models.Value('-'),
                    output_field=db_models.CharField()
                )
            ).values(
                "id","user__username", "user_name", "end_point","ip_address","payload","old_data",
                "method","error_details","is_success_entry","company_name","module_name","created_at__date","action", "changed_data_at","model_name","created_at"
            ).order_by('-created_at')
            if len(data) == 0:
                return Response(
                    error_response(
                        'No Records Found', 'No Records Found', 404
                    ),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if "is_export" in params:
                data_df = pd.DataFrame(data, columns=["created_at__date","user__username","module_name","action", "model_name","ip_address","payload","old_data","method", "created_at"
                ])
                data_df.created_at = data_df.created_at.apply(lambda obj:strftime(localize_dt(obj), mode="TIME", fmt="%I:%M %p") if obj else obj)
                data_df.old_data = data_df.old_data.apply(lambda x: self.parse_json(x))
                data_df.payload = data_df.payload.apply(lambda x: self.parse_json(x))
                data_df['changes'] = data_df.apply(lambda x: DeepDiff(x['old_data'], x['payload']), axis=1)
                data_df['old_data'] = data_df.apply(lambda obj : self.generate_old_new_data(obj['changes'], 'old') if obj["method"] != "POST" else self.clean_list(obj['old_data']), axis=1)
                data_df['payload'] = data_df.apply(lambda obj : self.generate_old_new_data(obj['changes'], 'new') if obj["method"] != "POST" else self.clean_list(obj['payload']), axis=1)
                # data_df.old_data = data_df.loc[data_df['old_data'] != None]
                # data_df.payload = data_df.loc[data_df['payload'] != None]
                data_df['action'] = data_df.apply(lambda obj: 'logged in' if obj['module_name'] == 'Login' else obj['action'],axis=1)
                data_df['old_data'] = data_df.apply(lambda obj: self.remove_keys(obj["old_data"]) if obj["old_data"] else None,axis=1)
                data_df['payload'] = data_df.apply(lambda obj: self.remove_keys(obj["payload"]) if obj["payload"] else None,axis=1)
                data_df['old_data'] = data_df.apply(lambda obj: 'logged in' if obj['module_name'] == 'Login' else obj['old_data'],axis=1)
                data_df['old_data'] = data_df.apply(lambda obj: ('Check Out' if obj['model_name'] == 'Attendance History' and 'time_out' in obj['payload'] else 'Check In') 
                                                if (obj['payload'] and obj['model_name'] == 'Attendance History') else obj['old_data'],axis=1)
                data_df.old_data = data_df.old_data.fillna('No Records Found')
                columns_to_drop = ['changes','method','created_at']
                data_df.drop(columns=columns_to_drop, axis=1, inplace=True)
                data_df.rename(columns={'user__username':'Host By','module_name':'Field','payload':'New Data','created_at__date':'Date',
                                        'model_name':'Changed Data At','ip_address':'Ip Address','action':'Action','old_data':'Old Data'},inplace=True)
                data_df = data_df.loc[(data_df['New Data'] != 'Nothing Updated') | (data_df['Old Data'] != 'Nothing Updated')]
                file_name = f"export_logging_records_{timezone_now().date()}.xlsx"
                return excel_converter(data_df,file_name)
            # page = paginator.paginate_queryset(data, request)
            # op_output = paginator.get_paginated_response(page)
            data_df = pd.DataFrame(data, columns=["id","user__username", "user_name", "end_point","ip_address","payload","old_data",
                "method","error_details","is_success_entry","company_name","module_name","created_at__date","action", "changed_data_at","model_name","created_at"])
            data_df.created_at = data_df.created_at.apply(lambda obj:strftime(localize_dt(obj), mode="TIME", fmt="%I:%M %p") if obj else obj)
            data_df.old_data = data_df.old_data.apply(lambda x: self.parse_json(x))
            data_df.payload = data_df.payload.apply(lambda x: self.parse_json(x))
            data_df['changes'] = data_df.apply(lambda x: DeepDiff(x['old_data'], x['payload']), axis=1)
            data_df['old_data'] = data_df.apply(lambda obj : self.generate_old_new_data(obj['changes'], 'old') if obj["method"] != "POST" else self.clean_list(obj['old_data']), axis=1)
            data_df['payload'] = data_df.apply(lambda obj : self.generate_old_new_data(obj['changes'], 'new') if obj["method"] != "POST" else self.clean_list(obj['payload']), axis=1)
            # data_df.old_data = data_df.loc[data_df['old_data'] != None]
            # data_df.payload = data_df.loc[data_df['payload'] != None]
            data_df['action'] = data_df.apply(lambda obj: 'logged in' if obj['module_name'] == 'Login' else obj['action'],axis=1)
            data_df['old_data'] = data_df.apply(lambda obj: self.remove_keys(obj["old_data"]) if obj["old_data"] else None,axis=1)
            data_df['payload'] = data_df.apply(lambda obj: self.remove_keys(obj["payload"]) if obj["payload"] else None,axis=1)
            data_df['old_data'] = data_df.apply(lambda obj: 'logged in' if obj['module_name'] == 'Login' else obj['old_data'],axis=1)
            data_df['old_data'] = data_df.apply(lambda obj: ('Check Out' if obj['model_name'] == 'Attendance History' and 'time_out' in obj['payload'] else 'Check In') 
                                                if (obj['payload'] and obj['model_name'] == 'Attendance History') else obj['old_data'],axis=1)
            data_df.drop(['changes'], axis=1, inplace=True)
            data_df = data_df.loc[(data_df['payload'] != 'Nothing Updated') | (data_df['old_data'] != 'Nothing Updated')]
            data_df.old_data = data_df.old_data.fillna('No Records Found')
            data_dict = data_df.to_dict('records')
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(data_dict, request)
            op_output = paginator.get_paginated_response(page)
            return Response(
                success_response(
                    op_output, "Successfully fetched Logging Records", 200
                ),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "Got error while logging records fetch", 400),
                status=status.HTTP_404_NOT_FOUND
            ) 
  
            
class EmployeeMissingInfoListAPIView(APIView):
    
    model = Employee
    pagination_class = CustomPagePagination
    
    def get(self, request):
        params = request.query_params
        current_year = timezone_now().year
        roles = request.user.employee_details.first().roles.values_list('name', flat=True).first()
        user_info = request.user.employee_details.first()
        employee_id = user_info.id
        print("employee_id",employee_id)
        print("role",roles)
        role = user_info.roles.values_list('name', flat=True)
        company_name = CompanyDetails.objects.filter(id= 1).values("company_name").first()
        q_filters=db_models.Q(is_deleted = False,work_details__employee_status__in = ["Active","YetToJoin"],company_id = 1)
        
        if 'EMPLOYEE' in role:
            return Response(
                error_response('You do not have permission to perform this action', 'You do not have permission to perform this action', 400),
                status=status.HTTP_404_NOT_FOUND
            )
        if 'department_id' in params:
            q_filters &= db_models.Q(work_details__department_id__in = params.get('department_id').split(','))

        if "search_filter" in params:
                q_filters &= (
                db_models.Q(user__username__icontains=search_filter_decode(params.get("search_filter")))
            )
        
        if 'MANAGER' in roles:
            emp_ids = EmployeeReportingManager.objects.filter(manager_id=employee_id, is_deleted=False).values_list('employee_id',flat=True)
            q_filters &= db_models.Q(id__in=emp_ids,is_deleted = False)
        if 'TEAM LEAD' in roles:
            emp_ids = EmployeeReportingManager.objects.filter(manager_id=employee_id, is_deleted=False).values_list('employee_id',flat=True)
            q_filters &= db_models.Q(id__in=emp_ids,is_deleted = False)
        paginator = self.pagination_class()
        data = Employee.objects.filter(q_filters &
                        (db_models.Q(employeeworkrulerelation__isnull=True) | db_models.Q(employeeleaverulerelation__isnull=True) | db_models.Q(assignedattendancerules__isnull=True)  | 
                         db_models.Q(official_email__isnull=True) | db_models.Q(work_details__work_location__isnull=True) | db_models.Q(first_name__isnull=True) | 
                         db_models.Q(last_name__isnull=True) | db_models.Q(phone__isnull=True) | db_models.Q(date_of_join__isnull=True) |  db_models.Q(work_details__department__isnull=True) | db_models.Q(work_details__sub_department__isnull=True) |
                         db_models.Q(work_details__designation__isnull=True) | db_models.Q(employee__isnull=True) | db_models.Q(salary_details__ctc__isnull=True) | 
                         db_models.Q(salary_details__account_holder_name__isnull=True) | db_models.Q(salary_details__account_number__isnull=True) |
                         db_models.Q(salary_details__bank_name__isnull=True) | db_models.Q(salary_details__branch_name__isnull=True) | db_models.Q(salary_details__city__isnull=True) |
                         db_models.Q(salary_details__ifsc_code__isnull=True) | db_models.Q(salary_details__account_type__isnull=True) | db_models.Q(emp_compliance_detail__uan_num__isnull=True) |
                        ~db_models.Q(employee_document_ids__document_type__document_type=20, employee_document_ids__is_deleted=False) | ~db_models.Q(employee_document_ids__document_type__document_type=10, employee_document_ids__is_deleted=False)
                        )).annotate(
            work_rule = db_models.Case(
                                    db_models.When(employeeworkrulerelation__isnull=True, then=db_models.Value("Not Assigned")),
                                    default=db_models.Value("Assigned"), output_field=db_models.CharField()
                                ),
            leave_rule = db_models.Case(
                        db_models.When(db_models.Q(employeeleaverulerelation__isnull=False, employeeleaverulerelation__is_deleted=False, employeeleaverulerelation__session_year__session_year=current_year), then=db_models.Value("Assigned")),
                        default=db_models.Value("Not Assigned"), output_field=db_models.CharField()
                    ),
            attendance_rule = db_models.Case(
                        db_models.When(assignedattendancerules__isnull=True, then=db_models.Value("Not Assigned")),
                        default=db_models.Value("Assigned"), output_field=db_models.CharField()
                    ),
            email = db_models.Case(
                        db_models.When(official_email__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            work_location = db_models.Case(
                        db_models.When(work_details__work_location__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            emp_first_name = db_models.Case(
                        db_models.When(first_name__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            emp_last_name = db_models.Case(
                        db_models.When(last_name__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            emp_phone = db_models.Case(
                        db_models.When(phone__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            joined_date = db_models.Case(
                        db_models.When(date_of_join__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            # grade = db_models.Case(
            #             db_models.When(work_details__employee_grade__isnull=True, then=db_models.Value("No")),
            #             default=db_models.Value("Yes"), output_field=db_models.CharField()
            #         ),
            dept = db_models.Case(
                        db_models.When(work_details__department__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            sub_dept = db_models.Case(
                        db_models.When(work_details__sub_department__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            emp_designation = db_models.Case(
                        db_models.When(work_details__designation__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            manager_info = db_models.Case(
                        db_models.When(employee__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            emp_aadhar = db_models.Case(
                        db_models.When(db_models.Q(employee_document_ids__document_type__document_type=20, employee_document_ids__is_deleted=False), then=db_models.Value("Yes")),
                        default=db_models.Value("No"), output_field=db_models.CharField()
                    ),
            emp_pan = db_models.Case(
                        db_models.When(db_models.Q(employee_document_ids__document_type__document_type=10, employee_document_ids__is_deleted=False), then=db_models.Value("Yes")),
                        default=db_models.Value("No"), output_field=db_models.CharField()
                    ),
            salary_ctc = db_models.Case(
                        db_models.When(salary_details__ctc__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            # monthly_ctc = db_models.Case(
            #             db_models.When(salary_details__salary__isnull=True, then=db_models.Value("No")),
            #             default=db_models.Value("Yes"), output_field=db_models.CharField()
            #         ),
            account_name = db_models.Case(
                        db_models.When(salary_details__account_holder_name__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            acc_number = db_models.Case(
                        db_models.When(salary_details__account_number__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            bank_acc_name = db_models.Case(
                        db_models.When(salary_details__bank_name__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            bank_branch_name = db_models.Case(
                        db_models.When(salary_details__branch_name__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            bank_city = db_models.Case(
                        db_models.When(salary_details__city__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            bank_ifsc_code = db_models.Case(
                        db_models.When(salary_details__ifsc_code__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            bank_account_type = db_models.Case(
                        db_models.When(salary_details__account_type__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
            # emp_fixed_salry = db_models.Case(
            #             db_models.When(salary_details__fixed_salary__isnull=True, then=db_models.Value("No")),
            #             default=db_models.Value("Yes"), output_field=db_models.CharField()
            #         ),
            # emp_variable_pay = db_models.Case(
            #             db_models.When(salary_details__variable_pay__isnull=True, then=db_models.Value("No")),
            #             default=db_models.Value("Yes"), output_field=db_models.CharField()
            #         ),

            emp_uan_num = db_models.Case(
                        db_models.When(emp_compliance_detail__uan_num__isnull=True, then=db_models.Value("No")),
                        default=db_models.Value("Yes"), output_field=db_models.CharField()
                    ),
        ).values(
            "company_id","user__username","work_details__employee_number","work_details__department__name","work_rule","leave_rule",
            "attendance_rule","email","work_location","emp_first_name","emp_last_name","emp_phone","joined_date",
            "dept","sub_dept","emp_designation","manager_info","emp_aadhar","emp_pan","salary_ctc","account_name","acc_number","bank_acc_name","bank_branch_name",
            "bank_city","bank_ifsc_code","bank_account_type","emp_uan_num",
        )
        df_data = pd.DataFrame(data, columns =["company_id","user__username","work_details__employee_number","work_details__department__name",
                                               "work_rule","leave_rule","attendance_rule","email","work_location","emp_first_name","emp_last_name",
                                               "emp_phone","joined_date","dept","sub_dept","emp_designation","manager_info","emp_aadhar","emp_pan","salary_ctc",
                                               "account_name","acc_number","bank_acc_name","bank_branch_name","bank_city","bank_ifsc_code",
                                               "bank_account_type","emp_uan_num"
                                                ])
        op_data = df_data.groupby('work_details__employee_number').agg({
                                    'user__username':'first',
                                    'work_details__department__name':'first',
                                    'work_rule':'first',
                                    'leave_rule': list,
                                    'attendance_rule':'first',
                                    'email':'first',
                                    'work_location':'first',
                                    'emp_first_name':'first',
                                    'emp_last_name':'first',
                                    'emp_phone':'first',
                                    'joined_date':'first',
                                    'dept':'first',
                                    'sub_dept':'first',
                                    'emp_designation':'first',
                                    'manager_info':'first',
                                    'emp_aadhar': list,
                                    'emp_pan': list,
                                    'salary_ctc':'first',
                                    'account_name':'first',
                                    'acc_number':'first',
                                    'bank_acc_name':'first',
                                    'bank_branch_name':'first',
                                    'bank_city':'first',
                                    'bank_ifsc_code':'first',
                                    'bank_account_type':'first',
                                    'emp_uan_num':'first',
                                    }).reset_index()
        # op_data = df_data.drop_duplicates().reset_index(drop=True)
        op_data['leave_rule'] = op_data.leave_rule.apply(lambda x: 'Assigned' if 'Assigned' in x else 'Not Assigned')
        op_data['emp_aadhar'] = op_data.emp_aadhar.apply(lambda x: 'Yes' if 'Yes' in x else 'No')
        op_data['emp_pan'] = op_data.emp_pan.apply(lambda x: 'Yes' if 'Yes' in x else 'No')
        op_data.rename(columns={"work_details__employee_number":"EmpId","user__username":"EmployeeName","work_details__department__name":"Department","work_rule":"WorkWeek",
                                "leave_rule":"LeaveRule","attendance_rule":"AttendanceRule","email":"OfficialEmail","emp_first_name":"FirstName","emp_last_name":"LastName",
                                "emp_phone":"PhoneNumber","joined_date":"DOJ","dept":"Depatment","sub_dept":"SubDepartment","emp_designation":"Designation",
                                "manager_info":"ReportingManager","emp_aadhar":"AadhaarCard","emp_pan":"PANCard","salary_ctc":"CTC","account_name":"AccountHolderName","acc_number":"AccountNumber",
                                "acc_number":"AccountNumber","bank_acc_name":"BankName","bank_branch_name":"BranchName","bank_city":"City","bank_ifsc_code":"IFSCCode",
                                "bank_account_type":"AccountType","emp_uan_num":"UANNumber",
                                }, inplace=True)
        if 'export' in params:
            op_data['S.NO'] = range(1, len(op_data) + 1)
            op_data.set_index('S.NO', inplace=True)  
            file_name = f"employee_missing_info_data_{timezone_now().date()}.xlsx"
            return excel_converter(op_data,file_name)
        
        data_dict = op_data.to_dict('records')
        page = paginator.paginate_queryset(data_dict, request)
        op_output = paginator.get_paginated_response(page)
        return Response(
                success_response(
                    op_output, "Successfully fetched Missing Employee Details", 200
                ),
                status=status.HTTP_200_OK
            )
        
                
class DefaultLeaveRulesAPIView(APIView):
    model = LeaveRules
    
    def get(self,request):
        company_id = request.user.employee_details.first().company.id
        q_filters = db_models.Q(is_deleted = False,company_id=company_id,id__in=list(range(1,8)))
        data = self.model.objects.filter(q_filters).values(
            "id","name"
        ).order_by('id')
        return Response(
                success_response(
                    data, "Successfully fetched Default LeaveRules", 200
                ),
                status=status.HTTP_200_OK
            )

class SetupWizardNotificationAPIView(APIView):
    
    model = CompanyDetails
    
    def post(self,request):
        today = timezone_now().date()
        roles = request.user.employee_details.first().roles.values_list('name', flat=True).first()
        user_info = request.user.employee_details.first()
        employee_id = user_info.id
        user_name = request.user.username
        email = request.user.email
        company_name = request.user.employee_details.first().company.company_name.title()
        print(user_name,email,company_name) 
        context = {"name":user_name,
                    "company_name":company_name
                    }
        body = email_render_to_string(
                    template_name="mails/admin_mails/onboard_email_to_admin.html", context=context
                )
        data={
                'subject':"Welcome Aboard! Your HRMS Setup is complete ",
                'body':body,
                'to_email':email
            }
        if check_alert_notification("Company Profile","Setup Wizard", email=True):
            Util.send_email(data,is_content_html=True)
        
        return Response(
            success_response(
                "Successfully send Email", "Successfully send Email", 200
            ),
            status=status.HTTP_200_OK
        )
# from django.db.models.functions import Split  
class CompanySizeUpdateAPIView(APIView):
    model = Employee
    
    def get(self,request):
        company_id = request.user.employee_details.first().company.id
        q_filters = db_models.Q(is_deleted=False,company_id=company_id)
        data = Registration.objects.filter(q_filters).annotate(
            employees_count=db_models.Count("company__employees__id",filter=db_models.Q(is_deleted=False,company__employees__work_details__employee_status__in=["Active","YetToJoin"])),
            ).values(
            "employees_count","company_size"
        )
        df = pd.DataFrame(data,columns=["employees_count","company_size"])
        df['company_size_end'] = df['company_size'].apply(lambda x: int(x.split('-')[1]))
        df['more_employees_to_add'] = df['company_size_end'] - df['employees_count']
        data=df.to_dict('records')
        return Response(
            success_response(
                data, "Successfully fetched company size and employee count", 200
            ),
            status=status.HTTP_200_OK
        )
    def patch(self,request):
        user_info = request.user.employee_details.first()
        company_id = request.user.employee_details.first().company.id
        
        obj = Registration.objects.filter(company_id=company_id).first()
        obj.company_size=request.data.get("company_size")
        obj.save()
        return Response(
            success_response(
                "Successfully Updated company size", "Successfully Updated company size", 200
            ),
            status=status.HTTP_200_OK
        )
        
class ManagerDepartmentDetailsV2(APIView):
    model = Departments
    pagination_class = CustomPagePagination
    def get_manager_deps(self,man_id, filters):
        emp_id = man_id
        my_list = []
        tag = True
        while tag:
            query = EmployeeReportingManager.objects.filter(manager_id__in=emp_id,
                                                            manager__work_details__employee_status='Active',
                                                            is_deleted=False)
            if not query.exists():
                break
            my_list.extend(list(query.values_list('employee_id',flat=True)))
            emp_id = list(query.values_list('employee_id',flat=True))
        return my_list
    
    def get(self, request, *args, **kwargs):
        
        company_id = kwargs.get("id")
        if not company_id:
            try:
                company_id = request.user.employee_details.first().company_id
            except Exception as e:
                return Response(
                    error_response(e, 'Some thing went wrong', 404),
                    status=status.HTTP_404_NOT_FOUND
                )
        q_filters = db_models.Q(company_id=company_id, is_deleted=False)
        paginator = self.pagination_class()
        logger.info(request.user)
        logger.info(request.user.employee_details)
        logger.info(request.user.employee_details.first())
        user_role = request.user.employee_details.first().roles.values_list('name',flat=True).first()
        if user_role == 'MANAGER':
            user_id = request.user.employee_details.first().id
            data = self.get_manager_deps([user_id], q_filters)
            data.append(user_id)
            q_filters &= db_models.Q(employeeworkdetails__employee__id__in=data)
        if 'search_filter' in request.query_params:
            q_filters &= db_models.Q(
                name__icontains=search_filter_decode(request.query_params.get('search_filter'))
            )
        MultitenantSetup().create_to_connection(request)
        data = self.model.objects.filter(q_filters).distinct('id').prefetch_related('sub_departments').values('id', 'company', 'name').order_by('-id')
        page = paginator.paginate_queryset(data, request)
        data_df = pd.DataFrame(page,
            columns=('id', 'company', 'name')
        )
        MultitenantSetup().go_to_old_connection(request)
        return Response(
            success_response(
                paginator.get_paginated_response(data_df.to_dict('records')), "Successfully fetched Departments", 200
            ),
            status=status.HTTP_200_OK
        )      

import traceback
import pandas as pd

from django.db.models import Value, F, When, CharField, Case, Q, Func, Count, BooleanField
from django.db.models.functions import  Concat
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db import models as db_models

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InvestmentDeclaration, Attachments, DeclarationForms
from directory.models import Employee
from payroll.models import Reimbursement

from core.utils import success_response, error_response, search_filter_decode, timezone_now
from core.custom_paginations import CustomPagePagination
from core.utils import excel_converter



class InvestmentDeclarationGetAPIViewV2(APIView):

    model = InvestmentDeclaration
    pagination_class = CustomPagePagination

    def get(self, request, *args, **kwargs):
        params = request.query_params
        try:
            def get_financial_year():
                today = timezone_now()
                if today.month >= 4:  
                    return today.year
                else:
                    return today.year - 1
            q_filters = db_models.Q(is_deleted = False)
            if "id" in params:
                q_filters &= db_models.Q(id=params.get("id"))
            if "company" in params:
                q_filters &= db_models.Q(employee__company = params.get("company"))
            if "employee" in params:
                q_filters &= db_models.Q(employee = params.get("employee"))
            if "start_year" in params:
                q_filters &= db_models.Q(start_year = params.get("start_year"))
            if "end_year" in params:
                q_filters &= db_models.Q(end_year = params.get("end_year"))
            if "status" in params:
                q_filters &= db_models.Q(status = params.get("status"))
            if "exclude" in params:
                q_filters &= ~db_models.Q(admin_resubmit_status__in=[int(st) for st in params.get("exclude").split(",")])
            if "admin_resubmit_status" in params:
                q_filters &= db_models.Q(admin_resubmit_status__in = [int(st) for st in params.get("admin_resubmit_status").split(",")])
            if "admin_status" in params:
                q_filters &= db_models.Q(admin_resubmit_status__in = [int(st) for st in params.get("admin_status").split(",")])                
            if "admin_status_ne" in params:
                q_filters &= ~db_models.Q(admin_resubmit_status__in = [int(st) for st in params.get("admin_status_ne").split(",")])
                q_filters &= db_models.Q(status__gt = 10)
            if "regime_type" in params:
                q_filters &= db_models.Q(regime_type = params.get('regime_type'))
            if "search_filter" in params:
                q_filters &= (
                    db_models.Q(employee__user__username__icontains=search_filter_decode(params['search_filter'])) |
                    db_models.Q(employee__official_email__icontains=search_filter_decode(params['search_filter'])) |
                    db_models.Q(employee__work_details__employee_number__icontains=search_filter_decode(params['search_filter']))
                )
            paginator = self.pagination_class()
            invesment_df = pd.DataFrame(InvestmentDeclaration.objects.filter(q_filters).prefetch_related('declaration_forms').annotate(
                employee_data=db_models.Func(
                    db_models.Value('id'), 'employee_id',
                    db_models.Value('name'), Concat(
                    "employee__first_name",
                    Value(" "),
                    "employee__middle_name",
                    Value(" "),
                    "employee__last_name",
                    Value(" "),),
                db_models.Value('employee_number'), "employee__work_details__employee_number",
                db_models.Value('department'), "employee__work_details__department__name",
                db_models.Value('organization'), "employee__company__company_name",
                function='jsonb_build_object',
                output_field=db_models.JSONField()
                ),
                status_display=Case(
                    When(status=10, then=Value("Saved")),
                    When(status=20, then=Value("Submitted")),
                    When(status=30, then=Value("Re Submitted")),
                    When(status=40, then=Value("Cancel")),
                    When(status=50, then=Value("Revoked")),
                    When(status=60, then=Value("Approved")),
                    When(status=70, then=Value("Approve_revoked")),
                    When(status=80, then=Value("Declined")),
                    When(status=90, then=Value("Final_Approved")),
                    default=Value(''),
                    output_field=CharField()
                    ),
                regime_type_display=Case(
                    When(regime_type=10, then=Value("Old Tax Regime")),
                    When(regime_type=20, then=Value("New Tax Regime")),
                    default=Value(''),
                    output_field=CharField()
                    ),
                admin_rstatus_display=Case(
                    When(admin_resubmit_status=10, then=Value("Saved")),
                    When(admin_resubmit_status=30, then=Value("Re Submitted")),
                    When(admin_resubmit_status=50, then=Value("Revoked")),
                    When(admin_resubmit_status=60, then=Value("Approved")),
                    When(admin_resubmit_status=90, then=Value("Final_Approved")),
                    When(admin_resubmit_status=80, then=Value("Declined")),
                    default=Value(''),
                    output_field=CharField()
                    ),
                attachment_data=ArrayAgg(
                    db_models.Func(
                        db_models.Value('id'), 'attachments__id',
                        db_models.Value('name'), 'attachments__attachment',
                        function='jsonb_build_object',
                        output_field=db_models.JSONField()
                    ),
                    filter=db_models.Q(attachments__investment_declaration_id=F('id')),
                    distinct=True
                ),
                submitted_forms=ArrayAgg(
                    db_models.Func(
                        db_models.Value('parentform_type'), 'declaration_forms__parentform_type_id',
                        # filter=db_models.Q(is_deleted=False, declaration='declaration_forms__id'),
                        # filter=db_models.Q(declaration_forms__investment_declaration_id=F('id')),
                        function='jsonb_build_object',
                        output_field=db_models.JSONField()
                        ),
                        distinct=True
                ),
                attachments_count = Count('attachments',distinct=True),
                files_count = Count('declaration_forms__attachments',distinct=True),
                declarationForms=ArrayAgg(
                    'declaration_forms__id',
                    distinct=True
                ),
                is_editable = Case(
                    When(start_year=get_financial_year(), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            ).values(
                'id','employee','employee_data','regime_type','regime_type_display', 'declaration_amount','income_from_previous_employer',
                'tds_from_previous_employer','approved_amount','final_declared_amount','final_approved_amount','savings_after_ctc','status',
                'status_display','admin_resubmit_status','admin_rstatus_display','start_year','end_year','approval_date','submitted_date','updated_at','attachment_data',
                'attachments_count','files_count','submitted_forms','declarationForms',
                'freeze_declared_status','freeze_final_declared_status','last_submission_date','access_to_select_regime','is_editable'
            ).order_by("-id"),
            columns=[
                'id','employee','employee_data','regime_type','regime_type_display', 'declaration_amount','income_from_previous_employer',
                'tds_from_previous_employer','approved_amount','final_declared_amount','final_approved_amount','savings_after_ctc','status',
                'status_display','admin_resubmit_status','admin_rstatus_display','start_year','end_year','approval_date','submitted_date','updated_at','attachment_data',
                'attachments_count','files_count','submitted_forms','declarationForms',
                'freeze_declared_status','freeze_final_declared_status','last_submission_date','access_to_select_regime','is_editable'
                ])
            invesment_df.declarationForms = invesment_df.declarationForms.apply(lambda x: list(DeclarationForms.objects.filter(id__in=x).annotate(
                attachments_data=ArrayAgg(db_models.expressions.Func(
                    db_models.Value('id'), 'attachments__id',
                    db_models.Value('name'), 'attachments__attachment',
                    function='jsonb_build_object',
                    output_field=db_models.JSONField()
                ),filter = Q(attachments__id__isnull = False))
            ).values('id', 'parentform_type','subform_type','declared_amount','approved_amount','final_declared_amount',
                    'final_approved_amount','comments_from_employee','comments_from_employer','attachments_data')))
            invesment_df = invesment_df.fillna('')
            if ("download" in params) and (params['download']=="true"):
                invesment_df['updated_at'] = invesment_df['updated_at'].dt.tz_localize(None)
                invesment_df['updated_at'] = invesment_df['updated_at'].dt.date
                invesment_df['Year'] = invesment_df['start_year'].astype(str) + "-" +  invesment_df['end_year'].astype(str)
                invesment_df['Employee name'] = invesment_df['employee_data'].apply(lambda x: x.get('name'))
                invesment_df.rename(columns = {'regime_type_display':'Regime', 'updated_at':'Submitted Date',
                              'status_display':'Employee Status','admin_rstatus_display':'Employer status'}, inplace = True)
                invesment_df = invesment_df[['Year','Employee name','Regime','declaration_amount','approved_amount','final_declared_amount','final_approved_amount', 'Submitted Date', 'approval_date', 'Employee Status','Employer status']]
                file_name = "declaration_setup_report.xlsx"
                return excel_converter(invesment_df,file_name)
            json_data = invesment_df.to_dict('records')
            page = paginator.paginate_queryset(json_data, request)
            return Response(
                success_response(
                    paginator.get_paginated_response(page), "Successfully fetched Saving declaration Data", 200
                ),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
class SavingDeclarationSalDOJAPIView(APIView):

    model = Employee
    pagination_class = CustomPagePagination
    def get(self, request):
        params = request.query_params
        if "employee" not in params:
            return Response(
                        error_response("Employee ID required", "Employee ID required", 404),
                        status=status.HTTP_404_NOT_FOUND
                    )
        curr_year = timezone_now().year
        curr_month = timezone_now().month
        if curr_month < 4:
            fin_start_date = curr_year -1
            fin_end_date = curr_year
        else:
            fin_start_date = curr_year
            fin_end_date = curr_year + 1
        qs = Employee.objects.filter(id=params.get("employee"),is_deleted = False).annotate(
            name=Concat(
                        "first_name",
                        Value(" "),
                        "middle_name",
                        Value(" "),
                        "last_name",
                        Value(" "),
                    ),
            ctc = F("salary_details__ctc"),
            regime_type = ArrayAgg(
                        db_models.expressions.Func(
                            db_models.Value('id'),db_models.F('investmentdeclaration__id'),
                            db_models.Value('type'), db_models.Case(
                                *[db_models.When(investmentdeclaration__regime_type=i[0], then=db_models.Value(i[1])) for i in InvestmentDeclaration.REGIME_CHOICES],
                                default=db_models.Value(''), output_field=db_models.CharField()),
                            db_models.Value('start_year'),db_models.F('investmentdeclaration__start_year'),
                            db_models.Value('end_year'),db_models.F('investmentdeclaration__end_year'),
                            db_models.Value('income_from_previous_employer'),db_models.F('investmentdeclaration__income_from_previous_employer'),
                            db_models.Value('tds_from_previous_employer'),db_models.F('investmentdeclaration__tds_from_previous_employer'),
                            function="jsonb_build_object",
                            output_field=db_models.JSONField()
                        ),
                            distinct=True,
                            filter = db_models.Q(
                                        investmentdeclaration__start_year=fin_start_date, 
                                        investmentdeclaration__end_year=fin_end_date
                                    )
                        ),
        ).values("id","name","date_of_join","ctc","regime_type")
        return Response(
                success_response(
                    qs, "Successfully fetched Employee Data", 200
                ),
                status=status.HTTP_200_OK
            ) 

class EmployeeReimbursementAPIViewV2(APIView):
    
    model = Reimbursement
    pagination_class = CustomPagePagination
    def get(self, request, *args, **kwargs):
        params = request.query_params
        try:
            q_filters = db_models.Q(is_deleted = False)
            if "id" in params:
                q_filters &= db_models.Q(id = params.get("id"))
            if "employee" in params:
                q_filters &= db_models.Q(employee = params.get("employee"))
            if "company" in params:
                q_filters &= db_models.Q(employee__company = params.get("company"))
            if "status" in params:
                if params.get("status") in ["Approved","Pending","Rejected","Approved_Paid"]:
                    q_filters &= db_models.Q(status=params.get("status"))
            if "type" in params:
                q_filters &= db_models.Q(type = params.get("type"))
            if "from_date" in params:
                q_filters &= db_models.Q(expense_date__gte = params.get("from_date"))
            if "to_date" in params:
                q_filters &= db_models.Q(expense_date__lte = params.get("to_date"))
            if "search_filter" in params:
                q_filters &= (
                    db_models.Q(employee__user__username__icontains=search_filter_decode(params['search_filter'])) |
                    db_models.Q(employee__official_email__icontains=search_filter_decode(params['search_filter'])) |
                    db_models.Q(employee__work_details__employee_number__icontains=search_filter_decode(params['search_filter']))
                )
            paginator = self.pagination_class()
            qs = Reimbursement.objects.filter(q_filters).annotate(
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

            page = paginator.paginate_queryset(qs, request)

            return Response(
                success_response(
                    paginator.get_paginated_response(page), "Successfully fetched Saving declaration Data", 200
                ),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
            
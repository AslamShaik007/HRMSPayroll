from calendar import monthrange
import datetime, logging, math
from django.utils import timezone

from django.conf import settings

from nested_multipart_parser.drf import DrfNestedParser
from django.shortcuts import get_object_or_404
import json
from investment_declaration.serializers import (
    InvestmentDeclarationDetailSerializer,
    InvestmentDeclarationSerializer
)
from dateutil.relativedelta import relativedelta
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import MultiPartParser, JSONParser

from django.http import JsonResponse
from attendance.models import AttendanceRuleSettings, EmployeeMonthlyAttendanceRecords

from core.custom_paginations import CustomLimitOffsetPagination
from core.views import (
    AbstractAPIView,
    AbstractListAPIView,
    AbstractListCreateAPIView,
    AbstractRetrieveUpdateAPIView,
)
from directory.models import Employee, EmployeeDocuments, EmployeeSalaryDetails, EmployeeWorkDetails, DocumentsTypes, RelationshipTypes
from company_profile.models import Departments, StatutoryDetails, SubDepartments, Designations
from HRMSApp.models import CompanyDetails, User
from investment_declaration.models import InvestmentDeclaration

from payroll.payroll_filters import ActiveEmployeeFilter
from payroll.salary_compute_utils import get_all_salary_details, import_employees_task
from payroll.serializers import EmployeesListSerializer, EmployeeGratuitySerializer, EmployeeMonthlyAttendanceRecordsSerializer, IciciBankReportSerializer, EsiResignationSerializer

from payroll.utils import get_payroll_month_employee, get_payroll_month_year, calculate_tax_for_regime, filters_data_ae_func, filters_data_year_func, get_current_financial_year_start_and_end, get_leaves_lop_for_employee, get_pay_cycle_start_and_end_date, get_pay_cycle_start_and_end_day, trim_all_columns, filters_data_func, ctc_to_gross_per_year, get_paycyclestart_and_paycycle_end

from .models import (
    EmployeeComplianceNumbers,          
    EpfSetup,
    Esi,
    HealthEducationCess,
    PaySalaryComponents,
    ProfessionTax,
    PayrollInformation,
    Regime,
    ReminderDates,    
    TaxDetails,        
    StatesTaxConfig,
    PayslipTemplateFields,
    EPFEmployees,
    EmployeePayrollOnHold,
    EsiResignationDetails,
)
from .serializers import (
    CompanyNameImgSerializer,     
    EmployeeSerializer,    
    EpfSerializer,
    EsiSerializer,    
    PaySalaryComponentsSerializer,
    ProfessionTaxSerializer,
    EmployeeBulkImportSerializer,    
    TaxDetailsSerializer,    
    EmployeeMissingInfoSerializer,
    EmpTdsReportSerializerV2,
    MissingEmployeeInfoSerializer,
    PayslipTemplateFieldsSerializer,
    PayslipFieldsSerializer,
    EPFEmployeesSerializer,
)

import pandas as pd
from django.http import HttpResponse
import numpy as np
from django.db.models.functions import Concat, Extract, Round, Coalesce, TruncMonth, Trim, JSONObject, Cast, TruncYear
from core.utils import success_response, error_response, excel_converter, timezone_now

logger = logging.getLogger("django")
import os

from django.db.models import Func, Count, Case, When, F, Sum, Value,Q, Min, Max, Window

from django.db import models
from core.custom_paginations import CustomPagePagination
from django.db import models as db_models
import traceback

from django.contrib.postgres.aggregates import ArrayAgg, StringAgg

from HRMSApp.utils import Util
import dateutil.parser as parser
from num2words import num2words
from payroll.utils import get_financial_year_start_and_end
from HRMSApp.models import CompanyCustomizedConfigurations
from django.core.exceptions import ObjectDoesNotExist
from payroll import services
from alerts.utils import check_alert_notification
import decimal
from datetime import date
##############################
# API Views
###########################

class CnameCimg(AbstractListAPIView):
    """
    this class is getting the company and company image in payroll base api
    """

    serializer_class = CompanyNameImgSerializer
    lookup_field = "id"
    lookup_url_kwarg = "company_id"
    queryset = CompanyDetails.objects.all()

    def filter_queryset(self, queryset):
        filter_queryset = {self.lookup_field: self.kwargs[self.lookup_url_kwarg]}
        return queryset.filter(**filter_queryset)


class EpfDetailsRetriveView(AbstractListAPIView):
    """
    this class is getting the epf details based on the company
    """

    serializer_class = EpfSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = EpfSetup.objects.all()

    def filter_queryset(self, queryset):
        filter_queryset = {self.lookup_field: self.kwargs[self.lookup_url_kwarg]}
        return queryset.filter(**filter_queryset)


class EpfDetailsRetrieveUpdateView(AbstractRetrieveUpdateAPIView):
    """
    this class is getting and updating the epf details based of epf_id
    """
    serializer_class = EpfSerializer
    lookup_field = "id"
    queryset = EpfSetup.objects.all()


class EsiDetailsRetriveView(AbstractListAPIView):
    """
    this class is getting the esi details based on the company
    """

    serializer_class = EsiSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = Esi.objects.all()

    def filter_queryset(self, queryset):
        filter_queryset = {self.lookup_field: self.kwargs[self.lookup_url_kwarg]}
        return queryset.filter(**filter_queryset)


class EsiDetailsRetrieveUpdateView(AbstractRetrieveUpdateAPIView):
    """
    this class is getting and updating the esi details based of esi_id
    """

    serializer_class = EsiSerializer
    lookup_field = "id"
    queryset = Esi.objects.all()



@api_view(['GET', 'PATCH'])
def ProfessionTaxsRetrieveUpdateView(request,**kwargs):
    """
    Get detail based on company id, or Update detail based on object id
    """
    if request.method == 'GET':
        snippets = ProfessionTax.objects.filter(company__id=kwargs['company_id'])
        serializer = ProfessionTaxSerializer(snippets, many=True)
        return Response(serializer.data)

    elif request.method == 'PATCH':        
        pt_inst = ProfessionTax.objects.get(id=kwargs['id'])            
        serializer = ProfessionTaxSerializer(pt_inst, data=request.data, partial=True)        
        if serializer.is_valid():
            serializer.save()
            return Response({"message":"Updated"}, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET','PATCH'])
def BankDetailsRetrieveView(request,**kwargs):
    """
        Get Bank detail based on EmployeeSalaryDetails id
    """
    if request.method == 'GET':
        snippets = EmployeeSalaryDetails.objects.filter(employee__id=kwargs['id']).annotate(emp_id = F('employee__work_details__employee_number'),emp_name = Trim(Concat(F('employee__first_name'),Value(" "),F('employee__middle_name'),Value(" "),F('employee__last_name'),))).values(            
            'emp_id',
            'employee__work_details__department__name',
            'employee__work_details__designation__name',
            'emp_name',
            'employee__emp_compliance_detail__pf_num',
            'employee__emp_compliance_detail__uan_num',
            'employee__emp_compliance_detail__esi_num',
            'employee__emp_compliance_detail__nominee_name',
            'employee__emp_compliance_detail__nominee_rel',
            'employee__emp_compliance_detail__nominee_dob',
            "bank_name",
            "account_number",
            "ifsc_code",
            "branch_name",
            "account_type",
            "account_holder_name",
            "ctc")
        # EmployeeSalaryDetails.objects.all().values('employee__emp_compliance_detail__pf_num')
        # Employee
        # serializer = EmployeeBankDetailsSerializer(snippets, many=True)
        return JsonResponse(list(snippets),safe=False)
    
    if request.method == 'PATCH':
        try:
            esd_obj = EmployeeSalaryDetails.objects.get(employee__id=kwargs['id'])            
            # print(esd_obj)
            esd_obj.bank_name = request.data.get('bank_name')
            esd_obj.account_number = request.data.get('account_number')
            esd_obj.ifsc_code = request.data.get('ifsc_code')
            esd_obj.branch_name = request.data.get('branch_name')
            # if request.data.get('bank_name'):
            #     esd_obj.fund_transfer_type = 'FT' if 'ICICI' in request.data.get('bank_name').upper() else 'NEFT'
            # esd_obj.branch_name = request.data.get('branch_name')
            
            # esd_obj.branch_name = request.data.get('branch_name')
            # esd_obj.branch_name = request.data.get('branch_name')
            # esd_obj.branch_name = request.data.get('branch_name')
            # esd_obj.branch_name = request.data.get('branch_name')
            esd_obj.save()
            
            emko_obj = EmployeeComplianceNumbers.objects.get(employee__id=kwargs['id'])
            emko_obj.pf_num = request.data.get('pf_num')
            emko_obj.uan_num = request.data.get('uan_num')
            emko_obj.esi_num = request.data.get('esi_num')
            emko_obj.nominee_name = request.data.get('nominee_name')
            emko_obj.nominee_rel = request.data.get('nominee_rel')
            if request.data.get('nominee_dob'):
                emko_obj.nominee_dob = request.data.get('nominee_dob',None)
            emko_obj.save()


            return Response({"message":"Updated"}, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response({"error":str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def CheckRunPayroll(request,**kwargs):
    """
        Get company id and check if all details to run payroll are completed for all active employees
        1. Bank details (bank name, bank account, ifsc, branch)
        2. Salary details (yearly ctc)
        3. LOP setup (either from hrms or payroll)
        4. tax config state selected to company
    """
    if request.method == 'GET':

        # curr_plan, plan_from = (plan_type.plan_type, "existing db") if (plan_type := PlanDetail.objects.first()) else (PlanDetail.PlanType.premium.value, "not existing db") #needs to top as exception direct
        # app_plan = {"current_plan":curr_plan, "plan_data_from":plan_from}

        epf_config = True
        cmp_id =  request.user.employee_details.first().company.id
        epf_obj = EpfSetup.objects.get(company_id=cmp_id)       
        if not epf_obj.epf_number:
            epf_config = False
        
        esi_config = True
        esi_obj = Esi.objects.get(company_id=cmp_id)       
        if not esi_obj.esi_no:
            esi_config = False        

        pt_config = ProfessionTax.objects.filter(company_id=cmp_id)
        if not pt_config:
            telangana_state =  StatesTaxConfig.objects.get(state='Telangana')
            pt_config = ProfessionTax.objects.create(company_id=cmp_id,state_id = telangana_state.id)
        
        pt_config_staus = True
        # if not pt_config.state:
        #     pt_config_staus = False

        leaves_month_year = get_payroll_month_year(request.user.employee_details.first().company)['payroll_month'] 
        leaves_month_year = leaves_month_year - relativedelta(months=1)
      
        # ars_obj = AttendanceRuleSettings.objects.get(company__id=kwargs['company_id'])

        # pay_cycle_end_day = ars_obj.attendance_input_cycle_to

        # payroll_data = PayrollInformation.objects.filter(is_processed=True).order_by('month_year').last()        

        # if payroll_data:

        #     pend_date = payroll_data.month_year.replace(day=pay_cycle_end_day) + relativedelta(months=1)

        # else:

        #     pend_date = ars_obj.attendance_paycycle_end_date


        pend_date = get_payroll_month_year(company = cmp_id, company_obj=False)['payroll_end_date']

        emp_inst = Employee.objects.filter(

                                        company=kwargs['company_id'],
                                        date_of_join__lte=pend_date,      
                                        payroll_status=True
                                    )        
        salary = True
        lop = True
        bank = True
        gender = True
        department = True
        if emp_inst.count() < 1:
            salary = False
            lop = False
            bank = False        
            gender = False
            department = False
        try:
            for emp in emp_inst: 

                if not emp.work_details.department.name:
                    department = False
                    break

                # print(emp.salary_details.fixed_salary)
                if (not (emp.salary_details.ctc and (emp.salary_details.ctc > 0))) and (not (emp.salary_details.fixed_salary and (emp.salary_details.fixed_salary > 0))):
                    salary = False                    
                    break      

                # try: 
                #     lop_obj = EmployeeLops.objects.get(employee__id=emp.id,lop_month_year=leaves_month_year.strftime("%Y-%m-01"))
                #     if not lop_obj.is_final:
                #         lop = False                    
                #         break
                # except:
                # try:                                      
                emar_obj = EmployeeMonthlyAttendanceRecords.objects.filter(
                    employee_id=emp.id,
                    year = int(leaves_month_year.strftime('%Y')),
                    month = int(leaves_month_year.strftime('%m'))
                ).values('is_hr_updated')

                if emar_obj:                    
                    if not emar_obj[0]['is_hr_updated']: 
                        lop = False
                        break
                else:
                    lop = False
                    break
                # except:                                
                #     lop = False                    
                #     break                                
                # except:
                #     # print("hi")
                #     lop = False
                #     break                    
                
                if not (
                    emp.salary_details.bank_name 
                    and emp.salary_details.ifsc_code 
                    and emp.salary_details.account_number
                    and emp.salary_details.branch_name
                ):
                    bank = False                    
                    break
                if not emp.gender:
                    gender = False
                    break
            
            return Response({"esi_config":esi_config,"epf_config":epf_config,"pt_config_status":pt_config_staus,"department":department,"bank":bank,"lop":lop,"salary":salary,"gender":gender,"exception_data":{"is_exception":False, "error":""}},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"esi_config":False,"epf_config":False,"pt_config_status":False,"department":False,"bank":False,"lop":False,"salary":False,"gender":False, "exception_data":{"is_exception":True,"error":str(e)}}, status=status.HTTP_200_OK)


class PaySalaryComponentListCreateView(AbstractListCreateAPIView):
    """
    this class is getting and creating the paysalarycomponent details based on company
    """

    serializer_class = PaySalaryComponentsSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = PaySalaryComponents.objects.all()

    def filter_queryset(self, queryset):
        filter_queryset = {self.lookup_field: self.kwargs[self.lookup_url_kwarg]}
        return queryset.filter(**filter_queryset)


class PaySalaryComponentRetrieveUpdateView(AbstractRetrieveUpdateAPIView):
    """
    this class is getting and updating the company paysalarycomponent based on psc_id
    """

    serializer_class = PaySalaryComponentsSerializer
    lookup_field = "id"
    queryset = PaySalaryComponents.objects.all()



class EmployeeViewSalary(APIView):            

    def get(self,request,*args, **kwargs):
        try:          
            esd_obj = EmployeeSalaryDetails.objects.filter(employee_id=self.kwargs["id"]).values(
                'id',
                'ctc',
                'employee__company__id',
                'employee__id',
                'employee__company__esi_comp__employer_contribution_pct',
                'monthly_incentive',
                'arrears',
                'special_deductions',
                'advance_deductions',
                'fixed_salary',
                'variable_pay'
                )[0]                        

            salary_info = {}
            salary_info['custom'] = {}
            salary_info['esd_id'] = esd_obj['id']
            
            employer_esi_val = esd_obj['employee__company__esi_comp__employer_contribution_pct']
            
            emp_ctc = esd_obj['ctc'] if esd_obj['ctc'] else 0
            salary_info['ctc'] = emp_ctc    

            salary_info['variable_pay'] = esd_obj['variable_pay'] if esd_obj['variable_pay'] else 0    
            salary_info['fixed_salary'] = esd_obj['fixed_salary'] if esd_obj['fixed_salary'] else 0    
       
            emp_gross_year = ctc_to_gross_per_year(emp_ctc,employer_esi_val)
            emp_gross_monthly = emp_gross_year / 12
                
            for component in PaySalaryComponents.objects.filter(is_active=True):
                
                if component.component_name=="Basic":
                    basic = round(emp_gross_monthly * (component.pct_of_basic/100), 2)
                    salary_info[component.component_name] = basic

                elif component.component_name=="Conveyance":
                    conveyance = component.flat_amount
                    salary_info[component.component_name] = conveyance

                elif component.component_name=="HRA":
                    hra = round(basic * (component.pct_of_basic/100), 2)            
                    salary_info[component.component_name] = hra
                else:
                    if component.calculation_type == 1:  # 1 is flat amount
                        value = component.flat_amount
                    elif component.calculation_type == 2:  # 2 is percentage
                        value = round(basic * (component.pct_of_basic/100),2)                    
                    else:  # 0 is empty which happens in threshold_base_amount i.e., cuttings
                        value = component.threshold_base_amount
                                    
                    if not component.is_default:  
                        if component.is_active:
                            if salary_info['custom'].get(component.earning_type):
                                salary_info['custom'][component.earning_type][component.component_name] = value
                            else:
                                salary_info['custom'][component.earning_type] = {component.component_name:value}
                    else:
                        salary_info[component.component_name] = value
                        
            sp_allowance = round(emp_gross_monthly - basic - hra - conveyance, 2)
            
            salary_info['sp_allowance'] = sp_allowance
            salary_info['gross_per_month'] = round(emp_gross_monthly,2)
            salary_info['gross_per_year'] = round((emp_gross_monthly * 12),2)
            salary_info['monthly_ctc'] = round((emp_ctc / 12),2)            

            employee_hec = HealthEducationCess.objects.last()

            """
            this must be decreased from declation approved amount
            """
            list_regimes = []
            
            leaves_month_year = get_payroll_month_year(request.user.employee_details.first().company)['pay_cycle_end_date']

            month_of_payroll_running = int(leaves_month_year.strftime('%m'))

            year_of_payroll_running = int(leaves_month_year.strftime('%Y'))

            financial_year_start, financial_year_end, cur_month, cur_year = get_current_financial_year_start_and_end(month_of_payroll_running,year_of_payroll_running)
            
            regime_type = 20 # New Tax Regime
            try:
                idc_obj = InvestmentDeclaration.objects.get(employee__id=esd_obj['employee__id'],
                                                                start_year=financial_year_start,
                                                                end_year=financial_year_end,
                                                                status=60
                                                            )
                fin_approved_amount = idc_obj.final_approved_amount
                regime_type = idc_obj.regime_type
            except:
                fin_approved_amount = 50000


            list_regimes.append(
                {"final_approved_amount": 0, "after_saving_salary": 0}
            )
            
            all_regimes = Regime.objects.all()
            tax_values= []

            salary_info['regime'] = "new" if regime_type == 20 else "old"

            for regimes in all_regimes:
                
                emp_tax_value = emp_gross_year            
                if regimes.regime_name == "new":                
                    list_regimes[0]['final_approved_amount'] = 50000
                    emp_tax_value = list_regimes[0]['after_saving_salary'] =  float(emp_gross_year) - float(50000)                
                    if emp_tax_value <= 700000:
                        emp_tax_value = 0   
                else:                
                    list_regimes[0]['final_approved_amount'] = fin_approved_amount
                    emp_tax_value = list_regimes[0]['after_saving_salary'] =  float(emp_gross_year) - float(list_regimes[0]['final_approved_amount'])

                each_regime = {
                    int(key): value for key, value in regimes.salary_range_tax.items()
                }

            
                total_tds_data = calculate_tax_for_regime(
                    income=emp_tax_value,
                    tax_regime=each_regime,
                    health_cess=employee_hec.health_education_cess,
                )
        
                if regimes.regime_name == salary_info['regime']:
                    salary_info['monthly_tds'] = int(math.ceil((round(total_tds_data["total_tax"] / 12)) / 10.0)) * 10                


                tax_values.append(total_tds_data['total_tax'])
                total_tds_data.update(
                    {"regime_name": regimes.regime_name, "health_cess": employee_hec.health_education_cess}
                )
                list_regimes.append(total_tds_data)
            

            salary_info['tds_details'] = list_regimes            
            salary_info['monthlyIncentive'] = esd_obj['monthly_incentive']
            salary_info['arrears'] = esd_obj['arrears']
            salary_info['specialDeductions'] = esd_obj['special_deductions']
            salary_info['advanceDeductions'] = esd_obj['advance_deductions']

         
            return Response({"data":salary_info}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
    
    def patch(self,request,*args, **kwargs):
        try:
            emp_obj = EmployeeSalaryDetails.objects.get(employee_id=self.kwargs["id"])
            emp_obj.ctc = eval(str(request.data.get('ctc', emp_obj.ctc)))
            emp_obj.monthly_incentive = eval(str(request.data.get('monthly_incentive', emp_obj.monthly_incentive)))
            emp_obj.arrears = eval(str(request.data.get('arrears', emp_obj.arrears)))
            emp_obj.advance_deductions = eval(str(request.data.get('advance_deductions', emp_obj.advance_deductions)))
            emp_obj.special_deductions = eval(str(request.data.get('special_deductions', emp_obj.special_deductions)))
            emp_obj.fixed_salary = eval(str(request.data.get('fixed_salary', emp_obj.fixed_salary)))
            emp_obj.variable_pay = eval(str(request.data.get('variable_pay', emp_obj.variable_pay)))
            emp_obj.save()                        
            return Response({"msg":"Update the details"}, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )



class ActiveEmployees(AbstractListAPIView):
    """
    this class is getting all the employees info in employees landing page and getting the
        obj id's of bank_details, salary_details, tds, lopSetup, payslips, saving declarations

    """

    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.all().select_related('company')
    filterset_class = ActiveEmployeeFilter
    pagination_class = CustomLimitOffsetPagination

    def get_queryset(self):        

        pend_date = get_payroll_month_year(company = self.kwargs[self.lookup_url_kwarg], company_obj=False)['payroll_end_date']
        
        payroll_status = True
        if 'payroll-status' in self.request.query_params:
            payroll_status = eval(self.request.query_params['payroll-status'])
        filter_queryset = {
                            'payroll_status': payroll_status,
                            self.lookup_field: self.kwargs[self.lookup_url_kwarg], 
                            'date_of_join__lte':pend_date                         
                           }
        # logger.info(filter_queryset)
        emp_qs = super().get_queryset().filter(**filter_queryset)
        emp_qs = emp_qs.annotate(department = StringAgg(
                                        Case(
                                            When(Q(work_details__department__name__in = [None, 'na', '', 'null', 'None'])|Q(work_details__department__name__isnull=True),
                                            then = Value('NA')),
                                            default = F('work_details__department__name'),
                                            output_field=db_models.CharField(),    
                                             ),
                                             delimiter=', ', distinct=True),
                        emp_number = StringAgg(
                                        Case(
                                            When(Q(work_details__employee_number__in = [None, 'na', '', 'null', 'None'])|Q(work_details__employee_number__isnull=True),
                                            then = Value('NA')),
                                            default = F('work_details__employee_number'),
                                            output_field=db_models.CharField(),    
                                             ),
                                             delimiter=', ', distinct=True),
                        )
        return emp_qs


class DepartmentEmployees(AbstractAPIView):
    """
    this class is used to get the employees based on department ids
    """
    def get(self, request, *args, **kwargs):
        try:
            params = request.query_params
            q_filters = db_models.Q()
            if "dept_ids" in params:
                q_filters &= db_models.Q(work_details__department_id__in = request.query_params.get('dept_ids').split(','))
        
            # ars_obj = AttendanceRuleSettings.objects.get(company__id=request.user.employee_details.first().company.id)
            # pay_cycle_end_day = ars_obj.attendance_input_cycle_to

            # payroll_data = PayrollInformation.objects.filter(is_processed=True).order_by('month_year').last()
        
            # if payroll_data:
            #     pend_date = payroll_data.month_year.replace(day=pay_cycle_end_day) + relativedelta(months=1)
            # else:
            #     pend_date = ars_obj.attendance_paycycle_end_date

            pend_date = get_payroll_month_year(company = request.user.employee_details.first().company)['payroll_end_date']

            q_filters &= db_models.Q(date_of_join__lte = pend_date)

            filters_data = Employee.objects.filter((Q(payroll_status=True) | Q(payroll_status__isnull=True)) & Q(company=request.user.employee_details.first().company.id) & Q(q_filters)).annotate(emp_name=Concat(
                                            F('first_name'),
                                            Value(' '),
                                            F('middle_name') ,
                                            Value(' '),
                                                F('last_name'))).values('work_details__department_id', 'work_details__department__name', 'emp_name', 'id')
            return Response(filters_data)

        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

class EmployeeLop(AbstractAPIView):
    """
    this class is used to get the lop and leave details of the month which emp needs to run 
    """

    lookup_url_kwarg = "emp_id"

    def get(self, request, *args, **kwargs):

        leaves_month_year = get_payroll_month_year(request.user.employee_details.first().company)['payroll_month']
        month_year = leaves_month_year
        leaves_month_year = leaves_month_year - relativedelta(months=1)                     

        context = get_leaves_lop_for_employee(
                        int(leaves_month_year.strftime('%Y')),
                        int(leaves_month_year.strftime('%m')),
                        self.kwargs[self.lookup_url_kwarg]
                        )

        context['month_year'] = month_year
        return Response(context)
        
        # except Exception as e:         
        #     payroll_lop_obj = EmployeeLops.objects.filter(
        #         employee_id=self.kwargs[self.lookup_url_kwarg],
        #         lop_month_year=leaves_month_year,
        #     )  # this must return obj only not qs
            

        #     if payroll_lop_obj:                        
        #         payroll_lop_obj = payroll_lop_obj.annotate(
        #             is_from=Value(f"payroll_exception {str(e)}", output_field=CharField())
        #         )
        #         payroll_lop_data = EmployeeLopsSerializer(payroll_lop_obj, many=True).data
        #         return Response(payroll_lop_data)
        #     else:
        #         context = {
        #             "employee": self.kwargs[self.lookup_url_kwarg],                
        #             "isFrom": f"exception coming {str(e)}",
        #             "totalLeavesCount": None,
        #             "totalLopCount": None
        #         } 
            
        #     return Response(context)            

    def post(self, request, *args, **kwargs):
        """
        this method is used to update the lop's
        this will store in payroll not in hrms
        """
        data = request.data
        
        # leaves_month_year = datetime.datetime.strptime(data['month_year'], '%d-%m-%Y').strftime('%Y-%m-01')    
        
        emar_obj, updated = EmployeeMonthlyAttendanceRecords.objects.update_or_create(
                employee_id=self.kwargs[self.lookup_url_kwarg],
                year = int(datetime.datetime.strptime(data['month_year'], '%d-%m-%Y').strftime('%Y')),
                month = int(datetime.datetime.strptime(data['month_year'], '%d-%m-%Y').strftime('%m')),                
                defaults={
                    "leaves_count": float(data["total_leaves"]),
                    "updated_hr_lop_count": float(data["lop_days"]),
                    "is_hr_updated":True
                }
            )
        
        # payroll_obj, created = EmployeeLops.objects.update_or_create(
        #     employee_id=self.kwargs[self.lookup_url_kwarg],            
        #     lop_month_year=leaves_month_year,

        #     defaults={
        #         "total_leaves_count": data["total_leaves"],
        #         "total_lop_count": data["lop_days"],
        #     },
        # )  # this must br only one object w.r.t month,year of that employee.
        # payroll_obj.is_from = "payroll_updated"
        # payroll_obj.is_final = True
        # payroll_obj.save()
        # payroll_lops_data = EmployeeLopsSerializer(payroll_obj).data
        # print(emar_obj.__dict__)
        payroll_lops_data = {
                    "employee": emar_obj.employee.id,                                         
                    "totalLeavesCount": emar_obj.leaves_count + emar_obj.lop_count,
                    "totalLopCount": emar_obj.updated_hr_lop_count
                }   
        return Response(payroll_lops_data)

class EmployeeAllLops(AbstractAPIView):
    """
    this class is used to get lops of employee current payroll running
    """
    def get(self, request):
        company_obj = request.user.employee_details.first().company
        company_id = company_obj.id

        leaves_month_year = get_payroll_month_year(company_obj)['payroll_month']
        month_year = leaves_month_year
        leaves_month_year = leaves_month_year - relativedelta(months=1)       

        # ars_obj = AttendanceRuleSettings.objects.get(company__id=company_id)
        # pay_cycle_end_day = ars_obj.attendance_input_cycle_to
        # payroll_data = PayrollInformation.objects.filter(is_processed=True).order_by('month_year').last()
       
        # if payroll_data:
        #     pend_date = payroll_data.month_year.replace(day=pay_cycle_end_day) + relativedelta(months=1)
        # else:
        #     pend_date = ars_obj.attendance_paycycle_end_date

        pend_date = get_payroll_month_year(company = company_obj)['payroll_end_date']
        emp_objs = Employee.objects.filter(company_id=company_id, payroll_status=True, date_of_join__lte=pend_date)
        emp_lop_lst = []
        for emp_obj in emp_objs:    #NEED TO CHANGE THE LOOP
            context = get_leaves_lop_for_employee(
                            int(leaves_month_year.strftime('%Y')),
                            int(leaves_month_year.strftime('%m')),
                            emp_obj.id
                            )
            context['month_year'] = month_year
            context['emp_name'] = emp_obj.first_name + emp_obj.middle_name + emp_obj.last_name
            context['department']=context['emp_code']=context['designation']=""
            if hasattr(emp_obj, 'work_details') and hasattr(emp_obj.work_details, 'department') and hasattr(emp_obj.work_details.department, 'name'):
                context['department'] = emp_obj.work_details.department.name
            if hasattr(emp_obj, 'work_details') and hasattr(emp_obj.work_details, 'designation') and hasattr(emp_obj.work_details.designation, 'name'):
                context['designation'] = emp_obj.work_details.designation.name
            if hasattr(emp_obj, 'work_details') and hasattr(emp_obj.work_details, 'employee_number'):
                context['emp_code'] = emp_obj.work_details.employee_number
            emp_lop_lst.append(context)
        return Response(emp_lop_lst)

class EmployeeBulkImport(AbstractAPIView):
    """
    this class is used to upload the bulk user from excel as per payroll reqs
    """
    serializer_class = EmployeeBulkImportSerializer
    def post(self,request):        
        try:
            file = request.FILES["file"]
            df = pd.read_excel(file, keep_default_na=False, skiprows=[1])
            if 'Errors' in df:
                df = df.drop('Errors',axis=1)
            specific_row_df = pd.read_excel(file, header=None, skiprows=1, nrows=1)
            if specific_row_df.shape[1] == 30:                
                specific_row_df = specific_row_df.iloc[:, :-1]
            
            un_trimmed_df_columns = df.columns.tolist()
            df = trim_all_columns(df)
            df.columns=df.columns.str.replace(' ','_')

            df['Dob'] = pd.to_datetime(df['Dob'], errors='coerce')
            df['Dob'] = df['Dob'].dt.strftime('%d-%m-%Y')

            df['Married_date'] = pd.to_datetime(df['Married_date'], errors='coerce')
            df['Married_date'] = df['Married_date'].dt.strftime('%d-%m-%Y')

            df['Joining_date'] = pd.to_datetime(df['Joining_date'], errors='coerce')
            df['Joining_date'] = df['Joining_date'].dt.strftime('%d-%m-%Y')

            cmp_obj = CompanyDetails.objects.get(id=request.data.get("company"))            
            df['company']=cmp_obj.id

            df = df.replace(np.nan,None,regex=True)    

            # non_matching_rows_dict, not_null_rows = check_if_required_columns_has_null_value(df)

            # print(non_matching_rows_dict)

            # not_null_rows_df = df.iloc[list(not_null_rows)]

            dict_data = df.to_dict(orient="records")
            
            errors=[]
            error_rows_list=[] 
                                 
            from concurrent.futures import wait, ThreadPoolExecutor, as_completed

            with ThreadPoolExecutor(4) as exe:
                futures = [exe.submit(import_employees_task, emp_data, request) for emp_data in dict_data]
                # wait for all download tasks to complete
                _, _ = wait(futures)
             
                print('Done', flush=True)
            
            # for each_employee in dict_data: #looping as if one record is improper we need to skip so,
            for r in as_completed(futures):
                res = r.result()
                # print(ft['errors'])
                if res:
                    errors.append(res['errors'])    
                    error_rows_list.append(res['error_rows_list'])    

            
            error_df = pd.DataFrame(error_rows_list)                         
            error_df = error_df.drop('company',axis=1)           
            first_part = error_df.iloc[:0]
            second_part = error_df.iloc[0:]             
            new_row_df = pd.DataFrame([specific_row_df.iloc[0].tolist()+[""]], columns=error_df.columns)

            new_df = pd.concat([first_part,new_row_df , second_part], ignore_index=True)
     
            new_df.columns = un_trimmed_df_columns + ["Errors"]
            excel_filename = str(cmp_obj.id) + "_" + "error_file.xlsx"
            excel_filepath = os.path.join(settings.MEDIA_ROOT,excel_filename)

            new_df.to_excel(excel_filepath, index=False)

            return Response({"msg":"excel data uploaded","records_failed":len(error_rows_list),"errors list":errors,'excel_file':excel_filename},status=status.HTTP_200_OK)
        except Exception as e:  
            return Response({"msg":str(e)},status=status.HTTP_400_BAD_REQUEST)



class EmployeeBulkLops(AbstractAPIView):
    """
    this class is used to get and patch the lops and leaveencashment in EmployeeMonthlyAttendanceRecords using EXCEL
    """
    serializer_class = EmployeeMonthlyAttendanceRecordsSerializer
    
    def post(self, request):
        try:
            type= request.data.get("type")
            request_company = request.user.employee_details.first().company
            if type == "upload":
                file = request.FILES["file"]
                df = pd.read_excel(file, keep_default_na=False, skiprows=0)
                df = trim_all_columns(df) #for strip    
                df.rename(columns={"Employee Email":"employee", "Leave":"leaves_count", "Lop":"lop_count", "Leaves Encashed":"leaves_encash_count"}, inplace = True)
                df[['Month', 'year']] = df['Month and year'].str.split('-', expand=True)
                df['year'] = pd.to_numeric(df['year'])
                df['month'] = pd.to_numeric(df['Month'])
                df['updated_hr_lop_count'] = df['lop_count']
                dict_data = df.to_dict(orient="records")
                ser_data = self.serializer_class(data=dict_data, many=True)
                if ser_data.is_valid():
                    ser_data.save()
                    return Response(success_response(msg="file uploaded sucessfully", result = []))
                else:
                    return Response(error_response(err=str(ser_data.errors)))

            elif type =="download":
                pay_cycle_end_date = get_payroll_month_year(request_company)['payroll_month']
            
                emps_df = pd.DataFrame(list(Employee.objects.filter
                                        (company_id=request_company, date_of_join__lte=pay_cycle_end_date, payroll_status=True).annotate(Emp_Email =  Trim(F('official_email')), Emp_Number=F('work_details__employee_number'), Employee_Name = F('user__username')).values('id', 'Emp_Email','Emp_Number', 'Employee_Name')))
                              
                emps_df["Month and year"] = pay_cycle_end_date.strftime('%m-%Y')
                emps_df["Leave"]=0
                emps_df["Lop"]=0
                emps_df.rename(columns = {'Emp_Email':'Employee Email', 'Emp_Number':'Employee Number', 'Employee_Name': "Employee Name"}, inplace = True) 
                emps_df["Leaves Encashed"] = 0
                del emps_df["id"]
                file_name = f"lops_for_{str(pay_cycle_end_date)}.xlsx"
                return excel_converter(emps_df,file_name)
            
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )


class PayScheduleView(APIView):
    renderer_classes = [JSONRenderer]    

    def get(self,request,*args,**kwargs):
        try:
            context = {}                 
            try:    
                attnd_obj = AttendanceRuleSettings.objects.get(company__id=self.kwargs["cmp_id"])
                context["payroll_cycle"] = attnd_obj.attendance_paycycle_end_date
                context["attendance_input_cycle_from"] = attnd_obj.attendance_input_cycle_from
                context["attendance_input_cycle_to"] = attnd_obj.attendance_input_cycle_to
            except:
                context["attendance_input_cycle_from"] = None
                context["attendance_input_cycle_to"] = None

            return JsonResponse(context)
        except Exception as e:
            print("error in PayScheduleView get request"+str(e))
    
    def patch(self,request,*args,**kwargs):
        try:        
            # pay_schedule_obj = AttendanceRuleSettings.objects.get(on_company__id=self.kwargs["cmp_id"])            
            # pay_schedule_obj.save()
            payroll_cycle = request.data.get('payroll_cycle')            
            start_day = request.data.get('start_day')            
            end_day = request.data.get('end_day')   
            attedance_obj, _created = AttendanceRuleSettings.objects.get_or_create(company__id=self.kwargs["cmp_id"])
            attedance_obj.attendance_paycycle_end_date = datetime.datetime.strptime(payroll_cycle,'%Y-%m-%d')
            attedance_obj.attendance_input_cycle_from = int(start_day)
            attedance_obj.attendance_input_cycle_to = int(end_day)
            attedance_obj.save()

            return JsonResponse({"msg":"Success"})            
        except Exception as e:
            return JsonResponse({"msg":"exception occured at server"+str(e)})


class TaxDetailsView(APIView):            

    def get(self,request,*args, **kwargs):
        try:          
            tax_obj = TaxDetails.objects.get(on_company__id=self.kwargs["cmp_id"])         
            ser_data = TaxDetailsSerializer(instance=tax_obj).data                         
            return JsonResponse({"data":ser_data})
        except Exception as e:
            print("error in TaxDetailsView get request"+str(e))
    
    def patch(self,request,*args, **kwargs):
        try:            
            tax_det_obj, _created = TaxDetails.objects.get_or_create(on_company__id=self.kwargs["cmp_id"])
            ser_data = TaxDetailsSerializer(instance=tax_det_obj, data=request.data, partial=True)        
            if ser_data.is_valid():
                ser_data.save()
                return JsonResponse({"data":ser_data.data})
            return JsonResponse({"data":ser_data.errors})
            
        except Exception as e:
            return JsonResponse({"msg":"expection occured at server"+str(e)})



class DepartmentListCreateAPIView(AbstractAPIView):
    """
    this class is used to listcreate dept, subdept and designation based on employee
    """


    def get(self, request, *args, **kwargs):
        try:
            # desig_obj = Designations.objects.filter(company__id=self.kwargs["cmp_id"]).annotate(emp_count=Count("employeeworkdetails__employee"))
            # serializer = DesignationSerializer(desig_obj, many=True)
            # return JsonResponse({"data":serializer.data})
            dept_data = Departments.objects.filter(company__id=self.kwargs["cmp_id"]).annotate(sub_depts=ArrayAgg('sub_departments__name',filter=db_models.Q(sub_departments__name__isnull=False), distinct=True), sub_depts_id = ArrayAgg('sub_departments__id', filter=db_models.Q(sub_departments__name__isnull=False), distinct=True), desigs = ArrayAgg('employeeworkdetails__designation__name', filter=db_models.Q(employeeworkdetails__designation__name__isnull=False), distinct=True), desigs_id = ArrayAgg('employeeworkdetails__designation__id', filter=db_models.Q(employeeworkdetails__designation__name__isnull=False))).annotate(emp_ids = ArrayAgg(F('employeeworkdetails__employee'),filter=db_models.Q(employeeworkdetails__employee__isnull=False))).annotate(emp_count=db_models.Func(F('emp_ids'), function='CARDINALITY', output_field=db_models.IntegerField())).values('id','name','sub_depts','sub_depts_id', 'desigs','desigs_id', 'emp_ids' ,'emp_count')
            return Response(
                        success_response(
                            result=dept_data, msg= "Successfully fetched the department data"
                        ),status=status.HTTP_200_OK) 
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request, *args, **kwargs):
        '''
        keeping old code for refernve in standalone.
        try:                                  
            dept_name = request.data.get("dept_name")
            sub_dept_name = request.data.get("sub_dept_name")
            cmp_id = request.data.get("cmp_id")            
            dep_obj, _dep_created = Departments.objects.get_or_create(
                                                name=dept_name,
                                                company=CompanyDetails.objects.get(id=cmp_id)
                                            )              
            sub_dep_obj, _sdep_created = SubDepartments.objects.get_or_create(
                name = sub_dept_name,
                department = dep_obj
            )            
            designation_data = request.data.getlist('desigs[]')                    
            for designation_name in designation_data:                                
                Designations.objects.get_or_create(
                                                name=designation_name, 
                                                company=CompanyDetails.objects.get(id=cmp_id),                                          
                                            )                                    
            return JsonResponse({"status":"department saved"}, status=status.HTTP_200_OK)            
        except Exception as e:            
            return JsonResponse({"exception":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        '''
        try:
            dept_name = request.data.get("dept_name")
            sub_dept_names = request.data.get("sub_dept_names")
            designation_names = request.data.get('designations') 
            cmp_id = request.data.get("cmp_id")

            if dept_name:

                dep_obj, _dep_created = Departments.objects.get_or_create(
                                                    name = dept_name,
                                                    company_id = cmp_id)
            if dept_name and sub_dept_names:                                         
                for sub_department in sub_dept_names:
                    sub_dep_obj, _sdep_created = SubDepartments.objects.get_or_create(
                        name = sub_department,
                        department_id = dep_obj.id
                    )
            if designation_names:
                for designation_name in designation_names:
                    Designations.objects.get_or_create(
                        name = designation_name, company_id = cmp_id
                    )
            return Response(
                    success_response(
                        result="data saved", msg= "Successfully submitted data"
                    ),
                status=status.HTTP_200_OK
                )

        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

    def patch(self,request, *args, **kwargs):
        try:
            if request.data['dept_id']:
                department_obj = Departments.objects.get(id=request.data['dept_id'])
                department_obj.name = request.data['dept_name']
                department_obj.save()
            if request.data['desig_id']:
                designation_obj = Designations.objects.get(id=request.data['desig_id'])
                designation_obj.name = request.data['desig_name']
                designation_obj.save()
            if request.data['sub_dept_id']:
                sub_department_obj = SubDepartments.objects.get(id=request.data['sub_dept_id'])
                sub_department_obj.name =request.data['sub_dept_name']
                sub_department_obj.save()
            return JsonResponse({"data":"sucess"},status=status.HTTP_200_OK)
        except Exception as e:            
            return JsonResponse({"msg":"error occured from server "+str(e)},status=status.HTTP_400_BAD_REQUEST)

    def delete(self,request, *args, **kwargs):
        try:
            Departments.objects.get(id=request.data['dept_id']).delete()
            return JsonResponse({"data":"success"},status=status.HTTP_200_OK)

        except Exception as e:
            return JsonResponse({"msg":"error occured from server "+str(e)},status=status.HTTP_400_BAD_REQUEST)   


class EmployeesList(AbstractListAPIView):
    """
    this class lists all the departments 
    i/p's opt company_name, emp_name, 
    """
    serializer_class = EmployeesListSerializer
    queryset = Employee.objects.filter(user__is_superuser=False)
    filterset_class = ActiveEmployeeFilter

    def get_queryset(self):
        filter_queryset = {"company_id": self.request.session.get("cmp_id")}
        return super().get_queryset().filter(**filter_queryset)


class EmployeeUpdateStatus(AbstractAPIView):
    def post(self, request):
        try:
            emp_ids = request.data.get("emp_ids")
            emp_status = request.data.get("status")            
            if emp_status == "False":
                status = False
            else:
                status = True
          
            updated_emp_ids=Employee.objects.filter(id__in=emp_ids).update(payroll_status=status)
            for empid in emp_ids:
                ed = User.objects.get(employee__id=empid)
                # print(ed,ed.user.is_active,status)
                ed.is_active=status
                ed.save()
          
            return Response({"msg":"updated"})          
        except Exception as e:
            print(e)
            return Response({"error":str(e)})


class AddEmployee(AbstractAPIView):
    """
    this class is used to add the employee from payroll when it's standalone
    """

    serializer_class = EmployeeBulkImportSerializer
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        try:
            # print("start", request.FILES)
            request.data._mutable=True
            cmp_id = CompanyDetails.objects.get(company_name=request.data.get("company_name")).id
            request.data['company']=cmp_id
            # request.data['employee_image']= request.Files["employee_image"]
            # print("ttt", request.data)
            ser_data = self.serializer_class(data = request.data)
            if ser_data.is_valid():
                ser_data.save()
                return Response({"msg":"created"},status=status.HTTP_201_CREATED)
            else:
                return Response({"msg":"not valid data","errors":str(ser_data.errors)},status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error in server":str(e)},status=status.HTTP_400_BAD_REQUEST)


class CheckPayrollExecuted(APIView):
  
    def get(self, request, *args, **kwargs):        
        if PayrollInformation.objects.filter(employee__company__id=request.query_params.get('cmp_id'),is_processed=True).count() > 0:
            run = True            
            return Response({"run":run},status=status.HTTP_200_OK)
        
        return Response({"run":False},status=status.HTTP_200_OK)


class CheckPayrollMaster(AbstractAPIView):

    def get(self, request, *args, **kwargs):
        # organization_details = True
        # epf_status = False
        # esi_status = False
        # pt_status = False
        # td_status = False
        # salary_components = True #will be True only as salary components presently we are not giving feasability to delete
        # try:
        #     company_obj = CompanyDetails.objects.get(id = request.query_params.get('cmp_id'))
        #     if (not company_obj.registered_city) or (not company_obj.registered_state) or (not company_obj.registered_pincode):
        #         organization_details = False

        #     epf_obj = EpfSetup.objects.get(company__id=request.query_params.get('cmp_id'))
        #     if epf_obj.epf_number:
        #         epf_status = True
            
        #     esi_obj = Esi.objects.get(company__id=request.query_params.get('cmp_id'))
        #     if esi_obj.esi_no:
        #         esi_status = True
            
        #     pt_obj = ProfessionTax.objects.get(company__id=request.query_params.get('cmp_id'))
        #     if pt_obj.state:
        #         pt_status = True

        #     td_obj = StatutoryDetails.objects.get(company__id=request.query_params.get('cmp_id'))
        #     if td_obj.pan_number and td_obj.tan_number and td_obj.tds_circle_code:
        #         td_status = True        

        #     exception_error = ""
        # except Exception as e:
        #     exception_error : str(e)
        #     organization_details= False
        #     epf_status = False
        #     esi_status = False
        #     pt_status = False
        #     td_status = False

        # return Response({"organization_details":organization_details, "td_status":td_status, "epf_status":epf_status,"esi_status":esi_status,"pt_status":pt_status, "salary_components":salary_components, "exception_error":exception_error})


        """
        this class is used to check the payroll can be run or not based on company employees
        """
    
        try:
            organization_details = td_status = epf_status = esi_status = pt_status = salary_components = department_details = bank_details = salary_details = lop = gender =  True
            cmp_obj = request.user.employee_details.first().company
            if not (cmp_obj.registered_city or cmp_obj.registered_state or cmp_obj.registered_pincode):
                organization_details = False
            if not (cmp_obj.statutorydetails_set.first().pan_number or cmp_obj.statutorydetails_set.first().tan_number or cmp_obj.statutorydetails_set.first().tds_circle_code):
                td_status = False
            if not cmp_obj.epf_comp.epf_number:
                epf_status = False
            if not cmp_obj.esi_comp.esi_no:
                esi_status = False
            if not cmp_obj.pt_comp.state:
                pt_status = False
            emp_insts = cmp_obj.employees.filter(payroll_status = True)
            for emp in emp_insts:             
                if not (
                    (hasattr(emp, 'work_details')) and
                    (hasattr(emp.work_details, 'department')) and
                    (hasattr(emp.work_details.department, 'name'))):
                    department_details = False
                    break
                
                if not (
                    (hasattr(emp, 'salary_details')) and 
                    (hasattr(emp.salary_details, 'bank_name')) and  
                    (hasattr(emp.salary_details, 'ifsc_code')) and 
                    (hasattr(emp.salary_details, 'account_number')) and
                    (hasattr(emp.salary_details, 'branch_name'))
                ):
                    bank_details = False                    
                    break
                
                if (not (emp.salary_details.ctc and (emp.salary_details.ctc > 0))) or (not emp.salary_details.fixed_salary and emp.salary_details.fixed_salary>0):
                    salary_details = False                    
                    break      
                
                lop_exists = get_payroll_month_employee(emp, is_emp_obj=True).get("lop_exists")
                if not lop_exists:
                    lop = False
                    break
                
                if not emp.gender:
                    gender = False
                    break

            return Response({"organization_details":organization_details, "td_status":td_status, "epf_status":epf_status, "esi_status":esi_status, "pt_status":pt_status, "salary_components":salary_components, "department_details":department_details, "bank_details":bank_details, "salary_details":salary_details, "lop":lop, "gender":gender})
        
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
                )


# APIs consumed by Mobile APP            

# @api_view(['GET'])
# def GetAvailablePaySlipsMonths(request):

#     if request.method == 'GET':
#         context = {}
#         payroll_dates = list(PayrollInformation.objects.filter(employee__id=request.query_params.get('emp_id'),is_processed=True).values_list("month_year",flat=True))

#         if payroll_dates: 
#             context['success'] = True
#             context['message'] = "Data fetched successfully"
#         else:
#             context['success'] = False
#             context['message'] = "Payslips not available"

#         context['data'] = list(payroll_dates)
        
#         return Response(context)

# class GetAvailablePaySlipsMonths(APIView):
#     """
#     this class is used to get the payslip data from employee_id
#     """
    
#     pagination_class = CustomPagePagination

#     def get(self,  request):
#         try:
#             emp_id = request.query_params.get('emp_id')
#             payroll_data = PayrollInformation.objects.filter(employee__id=emp_id,is_processed=True).annotate(emp_id=Value(emp_id,output_field=models.IntegerField()),full_name = models.functions.Concat(
#                 models.F('employee__first_name'), models.Value(' '), models.F('employee__middle_name'), models.Value(' '), models.F('employee__last_name'), output_field=models.CharField()
#             ),month = models.F('month_year')).values('emp_id','full_name', 'month')
#             paginator = self.pagination_class()
#             page = paginator.paginate_queryset(payroll_data, request)
#             return Response(success_response(result=paginator.get_paginated_response(page), msg="payslip details fetched successfully"), status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response(
#                     error_response(e, 'Some thing went wrong', 404),
#                     status=status.HTTP_404_NOT_FOUND
#                 )

# @api_view(['GET'])
# def GetPayslipsInfo(request):

#     if request.method == 'GET':
#         context = {}
#         payroll_data = PayrollInformation.objects.filter(employee__id=request.query_params.get('emp_id'),month_year=request.query_params.get('date'),is_processed=True).values()

#         emp_obj = Employee.objects.get(id=request.query_params.get('emp_id'))
#         if payroll_data: 
#             context['success'] = True
#             context['message'] = "Data fetched successfully"
#         else:
#             context['success'] = False
#             context['message'] = "Payslip information not available"
        
#         to_str = lambda s: s or ""        
        
#         payroll_data[0]["employeeDetails"] = {"fname":emp_obj.first_name,
#                                               "lname":emp_obj.last_name,
#                                               "mname":emp_obj.middle_name,
#                                               "designation":to_str(emp_obj.work_details.designation.name),
#                                               "empId":to_str(emp_obj.work_details.employee_number),
#                                               "jdate":emp_obj.date_of_join
#                                               }
#         payroll_data[0]['employerDetails'] =     {                                
#                                                 "name":emp_obj.company.company_name,
#                                                 "address":{
#                                                     "line1":to_str(emp_obj.company.registered_adress_line1),
#                                                     "line2":to_str(emp_obj.company.registered_adress_line2),
#                                                     "country":to_str(emp_obj.company.registered_country),
#                                                     "state":to_str(emp_obj.company.registered_state),
#                                                     "city":to_str(emp_obj.company.registered_city),
#                                                     "pincode":to_str(emp_obj.company.registered_pincode) 
#                                                 }                                                                                                 
#                                             }                                            
#         context['data'] = payroll_data
#         return Response(context)


@api_view(['GET'])
def GetPaySlipList(request):

    if request.method == 'GET':
        context = {}
        payroll_dates = PayrollInformation.objects.filter(employee__id=request.query_params.get('emp_id'),is_processed=True).values("id","month_year","employee")                    
        emp_obj = Employee.objects.get(id=request.query_params.get('emp_id'))

        context['data'] = []
            
        if payroll_dates: 
            context['success'] = True
            context['message'] = "Data fetched successfully"
            for pdate in payroll_dates:
                context['data'].append(
                    {
                        "p_id": pdate['id'],
                        "employee_id":request.query_params.get('emp_id'),                        
                        "name":emp_obj.name,
                        # "monthYear": pdate['month_year'],
                        # "payPeriod": pdate['month_year'].strftime('%b %Y'),
                        "month": pdate['month_year'].strftime('%b %Y'),
                        # "netPay": pdate['net_pay'],
                        # "paidDays": pdate['paid_days']
                    }
                )
        else:
            context['success'] = False
            context['message'] = "Salary slips not available"

        return Response(context)



@api_view(['GET'])
def GetPaySlipDetail(request):

    if request.method == 'GET':
        context = {}
        data = {}
        payroll_data = PayrollInformation.objects.get(id=request.query_params.get('p_id'),is_processed=True)

        emp_obj = Employee.objects.get(id=payroll_data.employee.id)
        if payroll_data: 
            context['success'] = True
            context['message'] = "Data fetched successfully"
        else:
            context['success'] = False
            context['message'] = "Payslip information not available"
        
        to_str = lambda s: s or ""        
        
        empd_obj = EmployeeDocuments.objects.get(employee=emp_obj,document_type__document_type=10)
        pan_number = empd_obj.document_number            

        data["employee_details"] = {"name":emp_obj.name,                                              
                                              "location":to_str(emp_obj.work_details.work_location),
                                              "department":to_str(emp_obj.work_details.department.name),
                                              "account_number":to_str(emp_obj.salary_details.account_number),
                                              "PAN":to_str(pan_number),                                              
                                              "UAN":to_str(emp_obj.emp_compliance_detail.uan_num),
                                              "ESI":to_str(emp_obj.emp_compliance_detail.esi_num),
                                              "total_working_days":payroll_data.working_days,
                                              "loss_of_pay_days":payroll_data.lop,
                                              "designation":to_str(emp_obj.work_details.designation.name),
                                              "annual_ctc":emp_obj.salary_details.ctc,
                                              "date_of_joining":emp_obj.date_of_join
                                              }    


        if emp_obj.employee_image:
            data['employee_details']['logo'] = emp_obj.employee_image.url

        
        data['id'] = payroll_data.id
        data['total_earnings'] = payroll_data.net_salary
        data['total_deductions'] = payroll_data.total_deduction    

        data['pay_period'] = payroll_data.month_year.strftime('%b') + "-" + payroll_data.month_year.strftime('%Y')
     
        data['earnings'] = [ 
                                {"description":"Basic Salary","amount":payroll_data.s_basic}, 
                                {"description":"HRA","amount":payroll_data.s_hra} ,
                                {"description":"Conveyance Allowance","amount":payroll_data.s_conv} ,
                                {"description":"Special Allowance","amount":payroll_data.s_special_allow} ,
                                {"description":"Monthly Incentive","amount":payroll_data.monthly_incentive} ,
                                {"description":"Arrears","amount":payroll_data.arrears}                                
                            ]
        
        data['deductions'] = [
                                {"description":"Provident Fund","amount":payroll_data.employee_pf}, 
                                {"description":"Professional Tax","amount":payroll_data.employee_esi}, 
                                {"description":"Gross Deductions","amount":payroll_data.profession_tax}, 
                                {"description":"LOP Deductions","amount":payroll_data.lop_deduction}, 
                                {"description":"TDS Deductions","amount":payroll_data.monthly_tds}, 
                                {"description":"Special Deductions","amount":payroll_data.special_deductions}, 
                                {"description":"Advance Deductions","amount":payroll_data.advance_deduction}                                
        ]
        
    
        context['data'] = data
        
        return Response(context)



@api_view(['GET'])
def GetTaxDetails(request):

    if request.method == 'GET':
        context = {}
        try:
            emp_salary_info = EmployeeSalaryDetails.objects.get(employee_salary_details__employee__id=request.query_params.get('emp_id'))

            context['success'] = True
            context['message'] = "Tax details fetched successfully" 
            salary_break_up = emp_salary_info.employee_salary_breakup            
            context['data'] = {}
        
            if salary_break_up['regime'] == "new":
                context['data']["taxableAmount"] = salary_break_up['tds_details'][1]['total_tax']
                context['data']["optedRegime"] = "newRegime"
            else:
                context['data']["taxableAmount"] = salary_break_up['tds_details'][2]['total_tax']
                context['data']["optedRegime"] = "oldRegime"
        
            context['data']["finalApprovedAmount"] = salary_break_up['tds_details'][0]['final_approved_amount']
            context['data']["afterSavingSalary"] = salary_break_up['tds_details'][0]['after_saving_salary']
            context['data']["grossPerYear"] = salary_break_up['gross_per_year']
        
            context['data']["oldRegime"] = [
                                                {
                                                    "description":"0 to 2.5 lakhs / 0%",
                                                    "amount": 0                                                     
                                                    },                                                     
                                                    {
                                                    "description":"2.5 to 5 lakhs / 5%",
                                                    "amount": salary_break_up['tds_details'][2]['salary_cuttings'].get(0.05) or 0  
                                                    },
                                                    {
                                                    "description":"5 to 10 lakhs / 20%",
                                                    "amount": salary_break_up['tds_details'][2]['salary_cuttings'].get(0.2) or 0                                          
                                                    },
                                                    {
                                                    "description":"10 and above / 30%",
                                                    "amount": salary_break_up['tds_details'][2]['salary_cuttings'].get(0.3) or 0                                         
                                                    },
                                                    {
                                                    "description":"Sum of above",
                                                    "amount": salary_break_up['tds_details'][2]['salary_cuttings_sum']
                                                    },
                                                    {
                                                    "description":"Health & Education cess 4%",
                                                    "amount": salary_break_up['tds_details'][2]['health_cess_cuttings']
                                                    },
                                                    {
                                                    "description":"Total Tax",
                                                    "amount": salary_break_up['tds_details'][2]['total_tax']
                                                    }
                                            ]
            
            context['data']["newRegime"] = [
                                                    {
                                                     "description":"0 to 3 lakhs / 0%",
                                                     "amount": 0                                                     
                                                     },                                                     
                                                     {
                                                     "description":"3 lakhs to 6 lakhs / 5%",
                                                     "amount": salary_break_up['tds_details'][1]['salary_cuttings'].get(0.3) or 0                                          
                                                     },
                                                     {
                                                     "description":"6 lakhs to 9 lakhs / 10%",
                                                     "amount": salary_break_up['tds_details'][1]['salary_cuttings'].get(0.1) or 0  
                                                     },
                                                     {
                                                     "description":"9 lakhs to 12 lakhs / 15%",
                                                     "amount": salary_break_up['tds_details'][1]['salary_cuttings'].get(0.15) or 0                                           
                                                     },
                                                     {
                                                     "description":"12 lakhs to 15 lakhs / 20%",
                                                     "amount": salary_break_up['tds_details'][1]['salary_cuttings'].get(0.2) or 0                                          
                                                     },
                                                     {
                                                     "description":"15 lakhs and above / 30%",
                                                     "amount": salary_break_up['tds_details'][1]['salary_cuttings'].get(0.3) or 0                                      
                                                     },
                                                     {
                                                     "description":"Sum of above",
                                                     "amount": salary_break_up['tds_details'][1]['salary_cuttings_sum']
                                                     },
                                                     {
                                                     "description":"Health & Education cess 4%",
                                                     "amount": salary_break_up['tds_details'][1]['health_cess_cuttings']
                                                     },
                                                     {
                                                     "description":"Total Tax",
                                                     "amount": salary_break_up['tds_details'][1]['total_tax']
                                                     }
                                                ]                       

        except Exception as e:                       
            context['success'] = False
            context['message'] = "Tax details not available"
            context['data'] = []        

        return Response(context)
    

@api_view(['GET'])
def GetPayrollSummary(request):

    if request.method == 'GET':
        context = {}
        data = {}
        payroll_data = PayrollInformation.objects.get(employee__id=request.query_params.get('emp_id'),month_year__year=int(request.query_params.get('year')),month_year__month=int(request.query_params.get('month')),is_processed=True)
        
        if payroll_data: 
            context['success'] = True
            context['message'] = "Data fetched successfully"
        else:
            context['success'] = False
            context['message'] = "Payslip information not available"
            
        data['earnings'] = [ 
                                {"description":"Basic Salary","amount":payroll_data.s_basic}, 
                                {"description":"HRA","amount":payroll_data.s_hra} ,
                                {"description":"Conveyance Allowance","amount":payroll_data.s_conv} ,
                                {"description":"Special Allowance","amount":payroll_data.s_special_allow} ,
                                {"description":"Monthly Incentive","amount":payroll_data.monthly_incentive} ,
                                {"description":"Arrears","amount":payroll_data.arrears}                                
                            ]
        
        data['deductions'] = [
                                {"description":"Provident Fund","amount":payroll_data.employee_pf}, 
                                {"description":"Professional Tax","amount":payroll_data.employee_esi}, 
                                {"description":"Gross Deductions","amount":payroll_data.profession_tax}, 
                                {"description":"LOP Deductions","amount":payroll_data.lop_deduction}, 
                                {"description":"TDS Deductions","amount":payroll_data.monthly_tds}, 
                                {"description":"Special Deductions","amount":payroll_data.special_deductions}, 
                                {"description":"Advance Deductions","amount":payroll_data.advance_deduction}                                
        ]
        
    
        context['data'] = data
        
        return Response(context)


# By Uday Shankar Start
        ...


@api_view(['GET'])
def GetEmpCount(request):
    
    emp_details = Employee.objects.filter(company__id=request.query_params.get('company_id'),payroll_status=True).count()
    return Response(emp_details)


@api_view(['GET'])
def GetPayDay(request):

    # for getting the day
    ars_obj = AttendanceRuleSettings.objects.get(company__id=request.query_params.get('company_id'))
    now = timezone.now()
    
    pay_day = ars_obj.attendance_input_cycle_to
    pay_day = datetime.date(now.year, now.month, pay_day)
    pay_day = pay_day.strftime("%B %d, %Y")
        
    return Response(pay_day)


@api_view(['GET'])
def GetNoOfPayslipPerMonth(request):
    
    # subquery = list(PayrollInformation.objects.filter(employee__company=request.session['company']).order_by('-month_year')[:6:].values_list('month_year',flat=True))
    month_count_dict = {}
    subquery = list(PayrollInformation.objects.filter(employee__company__id=request.query_params.get('company_id'),is_processed=True).order_by('-month_year').values_list('month_year',flat=True))
    for date in subquery:
        month = str(date.strftime('%B %Y'))
        if month not in month_count_dict:
            month_count_dict[month] = 0
        month_count_dict[month] += 1
    # print(dict(month_count_dict))
    
    # print(subquery)
    # print(request.query_params.get('company_id'))
                    
    return Response(month_count_dict)

@api_view(['GET'])
def GetEmpPayrollAnalytics(request):

    allData = {
        "processed":0,
        "not_processed":0,
        "month_year":""
    } 
    payroll_info_objs = PayrollInformation.objects.filter(employee__company__id=request.query_params.get('company_id'))
    if not payroll_info_objs:
        return Response(allData)
    latest_month_year = payroll_info_objs.order_by('-month_year').values('month_year').first()['month_year']

    payroll_counts = payroll_info_objs.filter(month_year=latest_month_year).aggregate(
        processed=Count(Case(When(is_processed=True, then=1), output_field=models.IntegerField())),
        not_processed=Count(Case(When(is_processed=False, then=1), output_field=models.IntegerField()))
    )

    allData['processed'] = payroll_counts['processed']
    allData['not_processed'] = payroll_counts['not_processed']
    allData['month_year'] = str(latest_month_year.strftime('%B'))
                
    return Response(allData)

@api_view(['GET'])
def GetDepartmentCount(request):

    all_departments = Departments.objects.filter(company__id=request.query_params.get('company_id')).count()
    return Response(all_departments)


@api_view(['GET'])
def GetNetSalaryCount(request):

    total_ctc = EmployeeSalaryDetails.objects.filter(employee__company__id=request.query_params.get('company_id'), employee__payroll_status=True).aggregate(Sum('ctc'))
    return Response(total_ctc)


@api_view(['GET'])
def GetEmpCountBySalaryRange(request):
    
    # employees = Employee.objects.filter(employee__company=request.session['company'], payroll_status="active")
    
    employees = Employee.objects.filter(company__id=request.query_params.get('company_id') ,payroll_status=True, is_deleted=False,salary_details__isnull=False)

    salary_ranges = {
        'Less_than_10k': 0,
        'ud_10k_to_20k': 0,
        'More_than_20k': 0
    }

    for employee in employees:
        salary = employee.salary_details.ctc if employee.salary_details.ctc else 0
        if salary < 10000:
            salary_ranges['Less_than_10k'] += 1
        elif salary <= 20000:
            salary_ranges['ud_10k_to_20k'] += 1
        else:
            salary_ranges['More_than_20k'] += 1

    # Print the dictionary with counts
    # print(salary_ranges) 
      
    return Response(salary_ranges)


@api_view(['GET'])
def GetActiveInactiveEmp(request):

    if request.query_params.get('company_id'):
        active_emp      = Employee.objects.filter(company__id=request.query_params.get('company_id'), payroll_status=True).count()
        inactive_emp    = Employee.objects.filter(company__id=request.query_params.get('company_id'), payroll_status=False).count()
        allActIn        = {'activeEmp':active_emp, 'inactiveEmp':inactive_emp}
    else:
        allActIn        = {'activeEmp':0, 'inactiveEmp':0}  
          
    return Response(allActIn)


@api_view(['GET'])
def getCompliancePaidReport(request):
    
    if request.query_params.get('company_id'):
    
        allData = PayrollInformation.objects.filter(employee__company__id=request.query_params.get('company_id'),is_processed=True).annotate(month=TruncMonth('month_year')).values('month').annotate(
            total=Sum('monthly_tds')+Sum('employer_pf')+Sum('employer_esi')).order_by('month')
        
        months_all = []
        count_all  = []
        
        ud = 1
        for i in allData:
            if ud <=6:
                months_all.append(datetime.datetime.strptime(str(i['month']), '%Y-%m-%d').date().strftime("%B"))
                count_all.append(int(i['total']))
            ud += 1
        
        if months_all and count_all:    
            months_all_str = ','.join([str(elem) for elem in months_all])    
            count_all_str = ','.join([str(elem) if elem != 0 else "0" for elem in count_all])    
        else:
            months_all_str = ''    
            count_all_str = 0  
    else:
        months_all_str = ''    
        count_all_str = 0          
            
    return_data = {'monthsAllStr':months_all_str, 'countAllStr':count_all_str}    
    
    return Response(return_data)


@api_view(['GET'])
def getRepVarianceReportUd(request):
    
    if request.query_params.get('company_id'):
        # Total Variance Report
    # if request.session.get("cmp_id", None):
        attribute = request.query_params.get("attribute")        
        timeline = request.query_params.get("timeline")        
        
        query_filters = Q(is_deleted=False) & Q(is_processed=True)
        query_filters &= Q(employee__company__id=request.query_params.get('company_id'))
        # query_filters &= Q(employee__user__is_superuser=False)
        
        now = timezone.now()
        
        if timeline == "current financial year":    
            from_date = datetime.datetime.strptime("01-04-"+str(now.year), '%d-%m-%Y').strftime('%Y-%m-01')                
            query_filters &= Q(month_year__gte=from_date)        
        elif timeline == "Last 3 months":                
            from_date = (datetime.date.today() - relativedelta(months=3)).strftime('%Y-%m-01')                
            # from_date = (datetime.date.today()).strftime('%Y-%m-01')                
            query_filters &= Q(month_year__gte=from_date)
        if "FY-" in timeline:            
            year = timeline.split("-")
            end_yr = int(year[1])            
            from_date = datetime.datetime.strptime("01-04-"+(end_yr-1), '%d-%m-%Y').strftime('%Y-%m-01')                
            to_date = datetime.datetime.strptime("01-04-"+end_yr, '%d-%m-%Y').strftime('%Y-%m-01')                
            query_filters &= Q(month_year__gte=from_date)
            query_filters &= Q(month_year__lte=to_date)
        else:
            timeline = "current financial year"
            from_date = datetime.datetime.strptime("01-04-"+str(now.year), '%d-%m-%Y').strftime('%Y-%m-01')                


        if attribute == "salary disbursed":
            all_emp_obj = PayrollInformation.objects.filter(query_filters).values('month_year').annotate(total=Sum('net_pay')).order_by('-month_year')

        elif attribute == "TDS/PF/PT/ESI":
            all_emp_obj = PayrollInformation.objects.filter(query_filters).values('month_year').annotate(total=Sum('monthly_tds')+Sum('total_esi_contribution')+Sum('total_epf_contribution')+Sum('profession_tax')).order_by('-month_year')
        else:
            # attribute = "salary disbursed"
            # all_emp_obj = PayrollInformation.objects.filter(query_filters).values('month_year').annotate(total=Sum('net_pay')).order_by('-month_year')
            ...    
        context = {
            "salary_inst":all_emp_obj, 
            "attribute" :attribute.capitalize(),
            "timeline" :timeline.capitalize()
        }
    else: 
        
       context = {
            "salary_inst":"", 
            "attribute" :"",
            "timeline" :""
        }

    return Response(context)    



class InvestmentDeclarationUpdateViewAdmin(APIView):
    """
    View to Update Investment Declaration
    """
    model = InvestmentDeclaration
    serializer_class = InvestmentDeclarationSerializer
    detail_serializer_class = InvestmentDeclarationDetailSerializer
    lookup_field = "id"
    queryset = InvestmentDeclaration.objects.all()
    parser_classes = [DrfNestedParser]
    def patch(self, request, **kwargs):
        investment_obj = get_object_or_404(InvestmentDeclaration, id=kwargs['id'])
        data = request.data.dict()
        
        details = data.get("details")
              
        # Initial Savings             
        if data.get('status'):
            investment_obj.status = data['status']
               
        if data.get('approvalDate'):
            investment_obj.approval_date = data['approvalDate']
        
        if data.get('approvedAmount'):
            investment_obj.approved_amount = data['approvedAmount']                   
        if data.get('finalApprovedAmount'):
            investment_obj.final_approved_amount = data['finalApprovedAmount']                   
        
        if data.get('adminResubmitStatus'):
            investment_obj.admin_resubmit_status = data['adminResubmitStatus']
            if data.get('adminResubmitStatus') == 50:
                investment_obj.approved_amount = 0            

        if isinstance(details, str):
            details = json.loads(details)
        for dec_form in details:                
            if 's_form' not in dec_form:
                declaration_form_qs = investment_obj.declaration_forms.filter(parentform_type_id=dec_form['p_id'])                  
                declaration_form_obj = declaration_form_qs.first()
                if data.get('approvedAmount'):
                    declaration_form_obj.approved_amount=dec_form.get('approvedAmount', 0)                    
                if data.get('adminResubmitStatus'):
                    if data.get('adminResubmitStatus') == 50:
                        declaration_form_obj.approved_amount = 0
                declaration_form_obj.final_approved_amount=dec_form.get('finalApprovedAmount', 0)                    
                declaration_form_obj.comments_from_employer=dec_form.get("commentsFromEmployer")
                declaration_form_obj.save()
                                                    
            else:
                for sub_form in dec_form['s_form']:
                    declaration_form_qs = investment_obj.declaration_forms.filter(parentform_type_id=dec_form['p_id'], subform_type_id=sub_form['id'])                        
                    declaration_form_obj = declaration_form_qs.first()
                    if data.get('approvedAmount'):
                        declaration_form_obj.approved_amount=sub_form.get('approvedAmount', 0)                        
                    if data.get('adminResubmitStatus'):
                        if data.get('adminResubmitStatus') == 50:
                            declaration_form_obj.approved_amount = 0
                    declaration_form_obj.final_approved_amount=sub_form.get('finalApprovedAmount', 0)                        
                    declaration_form_obj.comments_from_employer=sub_form.get("commentsFromEmployer")
                    
                    declaration_form_obj.save()

        if int(data.get('adminResubmitStatus')) == 80:
                declaration_form_obj.declined_date=timezone_now().date()
                try:
                    empl_name = investment_obj.employee.user.username.title()
                    official_email = investment_obj.employee.official_email
                    emp_code = investment_obj.employee.work_details.employee_number
                    start_year = investment_obj.start_year
                    end_year = investment_obj.end_year
                    body = f"""
    Dear {empl_name} [{emp_code}],

    We regret to inform you, your savings declaration has been rejected. Please resubmit the form as per the comments provided.
    
    Best regards,
    {investment_obj.employee.company.company_name.title()}.                         
    """
                    data={
                        'subject':'Saving declaration rejected for the year %s-%s' % (start_year, end_year),
                        'body':body,
                        'to_email':official_email
                    }
                    if check_alert_notification("Saving Declaration",'Form Rejected', email=True): 
                        Util.send_email(data)
                except Exception as e:
                    print("Execption in sending Email to employee",e)
        
        elif int(data.get('adminResubmitStatus')) == 60:
                declaration_form_obj.approved_date=timezone_now().date()
                try:
                    empl_name = investment_obj.employee.user.username.title()
                    official_email = investment_obj.employee.official_email
                    emp_code = investment_obj.employee.work_details.employee_number
                    start_year = investment_obj.start_year
                    end_year = investment_obj.end_year
                    body2 = f"""
    Dear {empl_name} [{emp_code}],

    We are pleased to inform you that your savings declaration has been reviewed and approved. Thank you for your cooperation.

    Thank you for your understanding.

    Best regards,
    {investment_obj.employee.company.company_name.title()}.                         
    """
                    data={
                        'subject':'Saving declaration approval confirmation %s-%s' % (start_year, end_year),
                        'body':body2,
                        'to_email':official_email
                    }
                    if check_alert_notification("Saving Declaration",'Form Approved', email=True): 
                        Util.send_email(data)
                except Exception as e:
                    print("Execption in sending Email to Employee",e)

        elif int(data.get('adminResubmitStatus')) == 50:
                declaration_form_obj.revoked_date=timezone_now().date()
                try:
                    empl_name = investment_obj.employee.user.username.title()
                    official_email = investment_obj.employee.official_email
                    emp_code = investment_obj.employee.work_details.employee_number
                    start_year = investment_obj.start_year
                    end_year = investment_obj.end_year
                    body3 = f"""
    Dear {empl_name} [{emp_code}],

    An issue has been identified in your savings declaration requiring attention. Please address this promptly for compliance.

    Best regards,
    {investment_obj.employee.company.company_name.title()}.                         
    """
                    data={
                        'subject':' Action Required: Compliance Issue in Savings Declaration %s-%s' % (start_year, end_year),
                        'body':body3,
                        'to_email':official_email
                    }
                    if check_alert_notification("Saving Declaration",'Form Decline/Revoked', email=True): 
                        Util.send_email(data)
                except Exception as e:
                    print("Execption in sending Email to Employee",e)

        investment_obj.save()
        return Response(
            {"data": {"status": "saving declaration updated successfully"}},
            status=status.HTTP_200_OK,
        )



class InvestmentDeclarationUpdateResubmit(APIView):
    """
    View to Update Investment Declaration
    """
    model = InvestmentDeclaration
    serializer_class = InvestmentDeclarationSerializer
    detail_serializer_class = InvestmentDeclarationDetailSerializer
    lookup_field = "id"
    queryset = InvestmentDeclaration.objects.all()

    def patch(self, request, **kwargs):
        investment_obj = get_object_or_404(InvestmentDeclaration, id=request.query_params.get("id"))
        data = request.data        
        
        investment_obj.admin_resubmit_status = 30

        if data.get('last_submission_date'):
            investment_obj.last_submission_date = data['last_submission_date']                       
       
        investment_obj.save()
        return Response(
            {"data": {"status": "saving declaration updated successfully"}},
            status=status.HTTP_200_OK,
        )


class ThirdPartyData(APIView):
    """
    this class is used to generate the text data for government sending
    """

    def get(self, request, *args, **kwargs):
        try:
            filters_data = set(request.user.employee_details.first().company.employees.all().filter(emp_payroll_info__is_processed=True).values_list('emp_payroll_info__month_year', flat=True))
            # request_employee = request.user.employee_details.first()
            company_id = request.query_params.get("company_id")
            # print(company_id)
            # print(request.query_params.get('month_year'))
            type = request.query_params.get("type",None)
            query_filters=Q(employee__company_id = company_id)  & ~Q(employee__emp_compliance_detail__uan_num__isnull=True)

            if request.query_params.get('month_year') and (request.query_params.get('month_year') not in ["null","undefined"]):
                
                query_filters &= Q(month_year = request.query_params.get('month_year'))
            
            query_filters &= Q(is_processed=True)
            
            # if request.query_params.getlist('employees') and (request.query_params.getlist('employees') not in ["null","undefined"]):
            #     query_filters &= Q(employee__in = request.query_params.getlist('employees'))
            # print(query_filters)

            qs = PayrollInformation.objects.filter(query_filters).annotate(
                uan=(F('employee__emp_compliance_detail__uan_num')),
                emp_name=Concat("employee__first_name",                                
                                 Case(
                                    When(employee__middle_name__isnull=False, then=Value(' ')),
                                    default=Value(''),
                                    output_field=models.CharField(),
                                ),
                                "employee__middle_name",
                                 Case(
                                    When(employee__last_name__isnull=False, then=Value(' ')),
                                    default=Value(''),
                                    output_field=models.CharField(),
                                ),                             
                                "employee__last_name"
                                ),
                
                net_salary1=Cast('net_salary', output_field=models.IntegerField()),
                pf_basic1=Cast('pf_basic', output_field=models.IntegerField()),
                employee_pf1 = Cast('employee_pf', output_field=models.IntegerField()),
                eps_contribution1 = Cast('eps_contribution', output_field=models.IntegerField()),
                edli_contribution1 = Cast('edli_contribution', output_field=models.IntegerField()),
                ).values('uan','net_salary1','pf_basic1','employee_pf1','emp_name','eps_contribution1','edli_contribution1','lop')
            if type == "json":
                df = pd.DataFrame(qs)
                df.rename(columns = {'net_salary1':'net_salary','pf_basic1':'pf_basic','employee_pf1':'employee_pf','eps_contribution1':'eps_contribution','edli_contribution1':'edli_contribution'}, inplace = True)
                df = df.to_dict(orient='records')

                data = {'filters_data':filters_data, 'qs':df}
                return Response(success_response(data, "Successfully Fetched Payroll Info Details"))
            
            df = pd.DataFrame(qs)
            df['emp_name'] = df['emp_name'].str.replace('  ', ' ')
            df['formatted_string'] = (
            df['uan'] + "#~#" + df['emp_name'] + "#~#" +
            # df['net_salary'].astype(int).astype(str) + "#~#" +
            # df['pf_basic'].astype(int).astype(str) + "#~#" +
            # # df['pf_basic'].astype(int).astype(str) + "#~#" +
            # # df['pf_basic'].astype(int).astype(str) + "#~#" +
            # df['employee_pf'].astype(int).astype(str) + "#~#" +
            # df['eps_contribution'].astype(int).astype(str) + "#~#" +
            # df['edli_contribution'].astype(int).astype(str) + "#~#" +
            # df['lop'].astype(int).astype(str) + "#~#0"
            
            df['net_salary1'].apply(lambda x: str(x) if x is not None else '0')  + "#~#" +
            df['pf_basic1'].apply(lambda x: str(x) if x is not None else '0')  + "#~#" +
            df['pf_basic1'].apply(lambda x: str(x) if x is not None else '0')  + "#~#" +
            df['pf_basic1'].apply(lambda x: str(x) if x is not None else '0')  + "#~#" +
            df['employee_pf1'].apply(lambda x: str(x) if x is not None else '0')  + "#~#" +
            df['eps_contribution1'].apply(lambda x: str(x) if x is not None else '0')  + "#~#" +
            df['edli_contribution1'].apply(lambda x: str(x) if x is not None else '0')  + "#~#" +
            df['lop'].apply(lambda x: str(int(x)) if x is not None else '0')  + "#~#0"
            )

            df['eps_contribution1'] = df['eps_contribution1'].apply(lambda x: str(x) if x is not None else '0')
            df['edli_contribution1'] = df['edli_contribution1'].apply(lambda x: str(x) if x is not None else '0')


            # Create the text file content
            text_content = "\n".join(df['formatted_string'])

            # Create an HttpResponse with the text content and appropriate headers
            response = HttpResponse(text_content, content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename="formatted_data.txt"'
            response['status'] = '200'
            return response
        except Exception as e:
            return Response(error_response(err=str(e), message="Some thing went wrong"))

class ThirdPartyDataV2(APIView):
    """
    this class is used to generate the text data for government sending
    """

    def pf_func(self, row, change_uans, payroll_epf_status):
        if (payroll_epf_status == 'customized') and (row['uan'] in change_uans):
            return '0'
        else:
            return str(row['pf_basic1'])
    
    def eps_func(self, row, change_uans, payroll_epf_status):
        if (payroll_epf_status == 'customized') and (row['uan'] in change_uans):
            return '0'
        else:
            return str(row['eps_contribution1'])
    
    def edli_func(self, row, change_uans, payroll_epf_status):
        if (payroll_epf_status == 'customized') and (row['uan'] in change_uans):
            return str(eval(str(row['eps_contribution1']))+eval(str(row['edli_contribution1'])))
        else:
            return str(row['edli_contribution1'])

    def get(self, request, *args, **kwargs):
        try:
            company_obj = request.user.employee_details.first().company
            filters_data = set(company_obj.employees.all().filter(emp_payroll_info__is_processed=True).values_list('emp_payroll_info__month_year', flat=True))
            filters_data = sorted(filters_data, reverse=True)

            company_id = request.query_params.get("company_id")
            type = request.query_params.get("type",None)
            query_filters=Q(employee__company_id = company_id)  & ~Q(employee__emp_compliance_detail__uan_num__isnull=True)
            month_year = 'all'
            if request.query_params.get('month_year') and (request.query_params.get('month_year') not in ["null","undefined"]):
                month_year = request.query_params.get('month_year')
                query_filters &= Q(month_year = month_year)
            query_filters &= Q(is_processed=True)
            payroll_epf_status = request.query_params.get("payroll_epf_status", "default") 
            
            # if request.query_params.getlist('employees') and (request.query_params.getlist('employees') not in ["null","undefined"]):
            #     query_filters &= Q(employee__in = request.query_params.getlist('employees')) #USE LATER FOR DOWLOADING SELECTED EMPLOYEES.

            qs = PayrollInformation.objects.filter(query_filters).annotate(
                uan=Case(
                        When(employee__emp_compliance_detail__uan_num="null", then=Value("")),
                        default=F('employee__emp_compliance_detail__uan_num'),
                        output_field=models.CharField()  # Adjust the field type if needed
                    ),
                emp_name=Concat("employee__first_name",                                
                                 Case(
                                    When(employee__middle_name__isnull=False, then=Value(' ')),
                                    default=Value(''),
                                    output_field=models.CharField(),
                                ),
                                "employee__middle_name",
                                 Case(
                                    When(employee__last_name__isnull=False, then=Value(' ')),
                                    default=Value(''),
                                    output_field=models.CharField(),
                                ),                             
                                "employee__last_name"
                                ),
                
                net_salary1=Cast('net_salary', output_field=models.IntegerField()),
                pf_basic1=Cast('pf_basic', output_field=models.IntegerField()),
                employee_pf1 = Cast('employee_pf', output_field=models.IntegerField()),
                eps_contribution1 = Cast('eps_contribution', output_field=models.IntegerField()),
                edli_contribution1 = Cast('edli_contribution', output_field=models.IntegerField()),
                ).values('uan','net_salary1','pf_basic1','employee_pf1','emp_name','eps_contribution1','edli_contribution1','lop')
            
            df = pd.DataFrame(qs)
            if type == "json":
                df.rename(columns = {'net_salary1':'net_salary','pf_basic1':'pf_basic','employee_pf1':'employee_pf','eps_contribution1':'eps_contribution','edli_contribution1':'edli_contribution'}, inplace = True)
                df = df.fillna(0)
                df = df.to_dict(orient='records')
                data = {'filters_data':filters_data, 'qs':df}
                return Response(success_response(data, "Successfully Fetched Payroll Info Details"))
            
            change_uans = set()
            if payroll_epf_status == 'customized':
                epf_employees = EPFEmployees.objects.first()
                if epf_employees:
                    change_uans = set(epf_employees.emps.values_list('emp_compliance_detail__uan_num', flat=True))
                else:
                    return Response("No epf customized employees found")
            df['emp_name'] = df['emp_name'].str.replace('  ', ' ')

            df['custom_pf_basic'] = df.apply(lambda row: self.pf_func(row, change_uans, payroll_epf_status), axis=1)
            df['custom_eps_contribution'] = df.apply(lambda row: self.eps_func(row, change_uans, payroll_epf_status), axis=1)
            df['custom_edli_contribution'] = df.apply(lambda row: self.edli_func(row, change_uans, payroll_epf_status), axis=1)
            
            df['formatted_string'] = (
            df['uan'] + "#~#" + df['emp_name'] + "#~#" +
            df['net_salary1'].apply(lambda x: str(x) if x is not None else '0')  + "#~#" +
            df['pf_basic1'].apply(lambda x: str(x) if x is not None else '0')  + "#~#" +
            df['custom_pf_basic']  + "#~#" +
            df['pf_basic1'].apply(lambda x: str(x) if x is not None else '0')  + "#~#" +
            df['employee_pf1'].apply(lambda x: str(x) if x is not None else '0')  + "#~#" +
            df['custom_eps_contribution'] + "#~#" +
            df['custom_edli_contribution']  + "#~#" +
            df['lop'].apply(lambda x: str(int(x)) if x is not None else '0')  + "#~#0"
            )
            text_content = "\n".join(df['formatted_string'])
            response = HttpResponse(text_content, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{company_obj.company_name}_{month_year}_pf_with_{payroll_epf_status}.txt"'
            response['status'] = '200'
            return response
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
class StateProfessionalTax(APIView):
    """
    this class is used to get the state tax config using state name
    """
    def get(self, request):
        try:
            state_name = request.query_params.get("state_name")
            statetaxdata = StatesTaxConfig.objects.filter(state=state_name).values()           
            return Response(success_response(statetaxdata,f"states taxes for{state_name}"))
        except Exception as e:
            return Response(error_response(err=str(e), message="Some thing went wrong"))

#   ?? Need fix emploee lops
class LeaveReport(APIView):
    """
    this class is used for leaves report used in payroll standalone
    """
    pagination_class = CustomPagePagination

    #fix needed if not selected month and year presently if selected month and year it will work proper.
    def get(self, request):
        try:
            cmp_obj = request.user.employee_details.first().company

            # filters_data = cmp_obj.employees.filter(montly_attendance__year__isnull=False).annotate(emp_name = Trim('user__username'), emp_id = F('id'), month_year = Trim(Concat(F('montly_attendance__year'),Value('-'), F('montly_attendance__month'),Value('-'), Value('01'), output_field =db_models.CharField()))).values('emp_name', 'emp_id', 'work_details__department_id', 'work_details__department__name', 'month_year')
            
            filters_data = filters_data_func(cmp_id = cmp_obj.id)

            params = request.query_params

            q_filters = db_models.Q(employee__company = cmp_obj)
            
            if "dept_ids" in params:
                q_filters &= db_models.Q(employee__work_details__department_id__in = request.query_params.get('dept_ids').split(','))
            if "emp_ids" in params:
                q_filters &= db_models.Q(employee_id__in = request.query_params.get('emp_ids').split(','))
            if "month_years" in params:
                years_lst = []
                months_lst = []
                for month_year in request.query_params.get('month_years').split(','):
                    month_year = parser.parse(month_year) - relativedelta(months=1)
                    years_lst.append(month_year.year),
                    months_lst.append(month_year.month)
                q_filters &= db_models.Q(year__in = years_lst, month__in = months_lst)
            
            emp_lop_qs = EmployeeMonthlyAttendanceRecords.objects.filter(q_filters).annotate(
                emp_id = F('employee__work_details__employee_number'), 
                employee_name = Concat(
                        F('employee__first_name'),
                        Value(" "),
                        F('employee__middle_name'),
                        Value(" "),
                        F('employee__last_name'),
                    ),
                department = F('employee__work_details__department__name'),
                manager = Concat(
                        F('employee__employee__manager__first_name'),
                        Value(" "),
                        F('employee__employee__manager__middle_name'),
                        Value(" "),
                        F('employee__employee__manager__last_name'),
                    )                                
                # days_in_month=ExpressionWrapper(     #the logic to subtract month days with leaces count in orm rather than df using
                #     calendar.monthrange(int(F('year11')), int(F('month11')))[1],
                #     output_field=db_models.IntegerField(),
                # ),
            )                
            
            emp_lop_data = emp_lop_qs.values('emp_id', 'employee_name','department', 'manager', 'year', 'month', 'leaves_count', 'updated_hr_lop_count')
            df = pd.DataFrame(emp_lop_data)

            if not df.empty:
                df['working_days'] = df.apply(lambda row: float(monthrange(row['year'], row['month'])[1]) - float(row['leaves_count']), axis=1)
                df = df[['emp_id', 'employee_name','department', 'manager', 'year','month', 'working_days', 'leaves_count', 'updated_hr_lop_count']]
            if ("download" in params) and (params['download']=="true"):
                df.rename(columns = {'emp_id':'Emp Id','employee_name':'Employee Name','department':'Department','manager':'Manager','year':'Year','month':'Month','working_days':'Working Days','leaves_count':'Leaves Count','updated_hr_lop_count':'Updated HR Lop Count'}, inplace = True)

                file_name = "leaves_lop_report.xlsx"
                return excel_converter(df,file_name)
            emp_lop_data = df.to_dict('records')
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(emp_lop_data, request)
            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data}, msg= "Successfully fetched employees data"
                ),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
        

class GetEmployeeDescription(APIView):               

    def get(self,request):
        try:                      
            empObj = Employee.objects.get(id=request.query_params.get("emp_id"))                                   
            context = {
                "name":empObj.name,
                "emp_id":empObj.work_details.employee_number,
                "department": empObj.work_details.department.name if empObj.work_details.department else "",
                "designation":empObj.work_details.designation.name if empObj.work_details.designation else ""
            }            
            return JsonResponse(context)
        except Exception as e:            
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )


class ManageEmployees(APIView):
    """
    this class is used for manage employees viewing
    """

    pagination_class = CustomPagePagination

    def get(self, request):
        try:
            params = request.query_params            
            print(params)
            q_filters = db_models.Q(company_id=request.query_params.get('company_id'))

            if "departments" in params:
                q_filters &= db_models.Q(work_details__department__name__in = request.query_params.getlist('departments'))

            if "employees" in params:
                print(request.query_params.getlist('employees'))
                q_filters &= db_models.Q(id__in = request.query_params.getlist('employees'))

            if "work_details_status" in params:
                q_filters &= db_models.Q(work_details__employee_status__in = request.query_params.getlist('work_details_status'))
            
            emp_qs = Employee.objects.filter(q_filters).annotate(
                    employee_name = Concat(
                        F('first_name'),
                        Value(" "),
                        F('middle_name'),
                        Value(" "),
                        F('last_name'),
                    ),
                    manager = Concat(
                        F('employee__manager__first_name'),
                        Value(" "),
                        F('employee__manager__middle_name'),
                        Value(" "),
                        F('employee__manager__last_name'),
                    ),
            ).annotate(
                employee_name=Func(F('employee_name'), Value('  '), Value(' '), function='REPLACE'),
                manager=Func(F('manager'), Value('  '), Value(' '), function='REPLACE')
            ).values("id","employee_name","date_of_join",'resignation_info__last_working_day','work_details__employee_status', 'company__company_name', 'work_details__department__name', 'manager', "payroll_status")
            
            df = pd.DataFrame(emp_qs)
            if ("download" in params) and (params['download']=="true"):
                file_name = "manage_employees_report.xlsx"
                return excel_converter(df,file_name)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(emp_qs, request)
            
            filter_qs = Departments.objects.filter(employeeworkdetails__employee__company_id=request.query_params.get('company_id'),employeeworkdetails__employee_status="Active").annotate(
                employee_details=db_models.expressions.Func(
                db_models.Value("employee_name"), Concat(F('employeeworkdetails__employee__first_name'),Value(" "),F('employeeworkdetails__employee__middle_name'),Value(" "),F('employeeworkdetails__employee__last_name')),
                db_models.Value("employee_id"),F('employeeworkdetails__employee__id'),
                function='jsonb_build_object',
                output_field=db_models.JSONField()
                )).values("name", "employee_details")
           
            filters_data = {}
            
            for item in filter_qs:
                name = item['name']
                employee_details = item['employee_details']
                if name not in filters_data:
                    filters_data[name] = [] 
                filters_data[name].append(employee_details)
            
            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data}, msg= "Successfully fetched employees data"
                ),
            status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
    
    def post(self, request):
        
        try:
            """
            this post request for changing the workdetails status(hrms use case)
            """
            ewd_status=["Active", "InActive","YetToJoin"]
            work_details_status = request.POST['work_details_status']
            employee_ids = request.data.getlist('employee_ids')
            if work_details_status not in ewd_status:
                return Response(success_response(result="", msg=f"status must be of {ewd_status}"))
            updated_work_details = EmployeeWorkDetails.objects.filter(employee_id__in = employee_ids)
            updated_work_details.update(employee_status=work_details_status)
            emp_work_details_count = updated_work_details.count()
            return Response(success_response(result=f"status {work_details_status} updated for {emp_work_details_count} employees", msg="updated work details status"))
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

class PayrollOverviewApi(APIView):
    model = PayrollInformation
    pagination_class = CustomPagePagination
    
    def get(self, request):
        """
        this API is to retrive the PayrollOverviewApi info reports
        old:PayrollOverviewApi
        new:PayrollOverviewApiV2
        """

        try:
            params = request.query_params
            q_filters = db_models.Q(employee__company_id=request.query_params.get('company_id'),is_processed=True)
            
            if "dept_id" in params:
                q_filters &= db_models.Q(employee__work_details__department__id__in = request.query_params.getlist('dept_id'))

            if "emp_id" in params:
                q_filters &= db_models.Q(employee__id__in = request.query_params.getlist('emp_id'))

            if "month_year" in params:
                q_filters &= db_models.Q(month_year__in = request.query_params.getlist('month_year'))
        
            payroll_qs = self.model.objects.filter(q_filters).annotate(
                                                    pan_number = StringAgg('employee__employee_document_ids__document_number',delimiter=', ',filter =db_models.Q(employee__employee_document_ids__document_type__document_type = DocumentsTypes.PAN_CARD, employee__employee_document_ids__is_deleted=False), distinct = True),
                                                    user_name = F('employee__user__username'),
                                                    company_name = F('employee__company__company_name'),
                                                    fund_transfer = F('employee__salary_details__fund_transfer_type'),
                                                    ifsc_code = F('employee__salary_details__ifsc_code'),
                                                    employee_number = F('employee__work_details__employee_number'),
                                                    pf_num = F('employee__emp_compliance_detail__pf_num'),
                                                    uan_num = F('employee__emp_compliance_detail__uan_num'),
                                                    esi_num = F('employee__emp_compliance_detail__esi_num'),
                                                    designation_name = F('employee__work_details__designation__name'),
                                                    department_name = F('employee__work_details__department__name'),
                                                    date_of_join = F('employee__date_of_join'),
                                                    date_of_exit = Case(
                                                        When(
                                                            Q(employee__resignation_info__last_working_day__isnull=False),
                                                            then=F('employee__resignation_info__last_working_day')),
                                                            default = None,
                                                            output_field = db_models.DateField()
                                                        ),
                                                    contribution = F('total_employer_contribution'),                                                    
                                                    ).values(
                                                        'month_year', 'month_days', 'user_name', 'company_name', 'fund_transfer', 
                                                             'account_number', 'ifsc_code', 'employee_number','pan_number', 'pf_num',
                                                            'uan_num', 'esi_num', 'designation_name', 'department_name',
                                                            'date_of_join', 'working_days', 'leaves', 'lop', 'paid_days', 's_basic', 's_hra', 's_conv', 's_special_allow', 's_gross',
                                                            'lop_deduction', 'other_deduction', 'earned_gross', 'e_basic','e_hra' ,'e_conv', 'e_special_allow', 'payable_gross', 
                                                            'a_basic', 'a_others', 'arrears', 'monthly_incentive', 'fixed_salary','variable_pay' ,'net_salary', 't_basic', 'pf_basic', 'employee_pf', 'profession_tax',
                                                            'employee_esi', 'monthly_tds', 'advance_deduction', 'total_deduction', 'total_employer_contribution','net_pay', 'employer_pf', 'employer_esi',
                                                            'contribution', 'monthly_ctc', 'yearly_ctc', 'date_of_exit')
                        
            df = pd.DataFrame(payroll_qs)
            df['monthly_gross'] = df['yearly_ctc'].apply(ctc_to_gross_per_year)
            df['monthly_gross'] = (df['monthly_gross'] / 12).round(0)

            if ("download" in params) and (params['download']=="true"):
                df.insert(0, 's no', range(1, len(df)+1))
                new_index = ['s no', 'month_year', 'user_name', 'company_name', 'fund_transfer', 'account_number', 'ifsc_code', 'employee_number', 'pan_number', 'pf_num', 'uan_num',
                              'esi_num', 'designation_name', 'department_name', 'date_of_join', 'date_of_exit', 'month_days', 'working_days', 'leaves', 'lop', 'paid_days', 'monthly_gross', 's_basic', 's_hra', 's_conv', 's_special_allow', 's_gross',
                              'lop_deduction', 'other_deduction', 'earned_gross', 'e_basic','e_hra' ,'e_conv', 'e_special_allow', 'payable_gross', 
                              'a_basic', 'a_others', 'arrears', 'monthly_incentive','fixed_salary','variable_pay', 'net_salary', 't_basic', 'pf_basic', 'employee_pf', 'profession_tax','employee_esi',
                              'monthly_tds', 'advance_deduction', 'total_deduction', 'net_pay', 'employer_pf', 'employer_esi', 'total_employer_contribution', 'monthly_ctc', 'yearly_ctc',
                              ]
                df = df[new_index]

                # df = df.apply(pd.to_numeric, errors="ignore")
                cols = ['leaves', 'lop', 'working_days', 'paid_days', 's_conv', 'lop_deduction', 'other_deduction', 'employee_pf', 'employee_esi', 'employer_pf', 'employer_esi', 's_basic', 's_hra', 's_special_allow', 's_gross', 'earned_gross', 'e_basic','e_hra' ,'e_conv', 'e_special_allow', 'payable_gross', 'profession_tax',
                              'a_basic', 'a_others', 'arrears', 'monthly_incentive','fixed_salary','variable_pay', 'net_salary', 't_basic', 'pf_basic', 'monthly_tds', 'advance_deduction', 'total_deduction', 'net_pay', 'total_employer_contribution', 'monthly_ctc', 'yearly_ctc', 'monthly_gross']

                df[cols] = df[cols].apply(pd.to_numeric, errors='coerce', axis=1)

                sum_row = [df[col].sum() if col in cols else "" for col in df]

                df.loc[len(df.index)] = sum_row

                df.rename(columns = {'month_year_t':'month_year'}, inplace = True)
                df['uan_num'] = df['uan_num'].astype(str)

                df['month_year'] = pd.to_datetime(df.month_year)

                df['month_year'] = df['month_year'].dt.strftime('%b-%Y')

                df['date_of_join'] = pd.to_datetime(df.date_of_join)

                df['date_of_join'] = df['date_of_join'].dt.strftime('%d-%m-%Y')

                file_name = "payroll_overview_report.xlsx"
                return excel_converter(df,file_name)
            data = df.to_dict(orient='records')
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(data, request)

            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id = request.query_params.get('company_id'))}, msg= "Successfully fetched payroll overview data"
                ),
            status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

class EpfSummaryApi(APIView):
    model = PayrollInformation
    pagination_class = CustomPagePagination

    def get(self, request):
        try:    
            params = request.query_params
            q_filters = db_models.Q(employee__company_id=request.query_params.get('company_id'),is_processed=True)
            
            if "dept_id" in params:
                q_filters &= db_models.Q(employee__work_details__department__id__in = request.query_params.getlist('dept_id'))

            if "emp_id" in params:
                q_filters &= db_models.Q(employee__id__in = request.query_params.getlist('emp_id'))

            if "month_year" in params:
                q_filters &= db_models.Q(month_year__in = request.query_params.getlist('month_year'))
            
            epf_qs = self.model.objects.filter(q_filters).annotate(
                user_name = F('employee__user__username'),
                company_name = F('employee__company__company_name'),
                employee_number = F('employee__work_details__employee_number'),
                pf_num = StringAgg(
                    Case(
                        When(Q(employee__emp_compliance_detail__pf_num__in=[None, 'na', '', 'null', 'None'])|Q(employee__emp_compliance_detail__pf_num__isnull=True),
                        then=Value('NA')),
                        default=F('employee__emp_compliance_detail__pf_num'),
                        output_field=db_models.CharField()
                    ),
                    delimiter=', ', distinct=True),
                uan_num = F('employee__emp_compliance_detail__uan_num'),
                esi_num = StringAgg(
                    Case(
                        When(Q(employee__emp_compliance_detail__esi_num__in=[None, 'na', '', 'null', 'None'])|Q(employee__emp_compliance_detail__esi_num__isnull=True),
                        then=Value('NA')),
                        default=F('employee__emp_compliance_detail__esi_num'),
                        output_field=db_models.CharField()
                    ),
                    delimiter=', ', distinct=True),
                designation_name = F('employee__work_details__designation__name'),
                department_name = F('employee__work_details__department__name'),
                ).values('month_year', 'user_name', 'company_name', 'employee_number', 'pf_num', 'uan_num', 'esi_num', 'pf_basic','designation_name', 'department_name', 'earned_gross', 'employer_pf', 'eps_contribution', 'edli_contribution', 'lop', 'total_epf_contribution')
            
            if ("download" in params) and (params['download']=="true"):
                df = pd.DataFrame(epf_qs) 
                org_name = df['company_name'][0]
                df['uan_num'] = df['uan_num'].astype(str)
                
                df['month_year'] = pd.to_datetime(df.month_year)

                df['month_year'] = df['month_year'].dt.strftime('%b-%Y')

                month_year = df['month_year'][0]

                df.rename(columns = {'user_name':'Name','employee_number':'EMP ID','pf_num':'PF No','designation_name':'Designation','department_name':'Department','uan_num':'UAN No','earned_gross':'Gross Earnings','pf_basic':'EPF wages','employer_pf':'EPF Contribution','eps_contribution':'EPS Contibution','edli_contribution':'EDLI Contibution',"lop":"No of LOP Days","total_epf_contribution":"Total Contribution"}, inplace = True)

                # 'eps_contribution':'EPS Wages','edli_contribution':'EDLI wages'
                df['EPS Wages'] = df['EPF wages']
                df['EDLI Wages'] = df['EPF wages']
                # df['S. NO'] = df.reset_index().index + 1
                
                BASE_COLUMNS = ['Name','EMP ID','PF No','Designation','Department','UAN No','Gross Earnings','EPF wages','EPS Wages','EDLI Wages','EPF Contribution','EPS Contibution','EDLI Contibution','No of LOP Days','Total Contribution']
                
                df = df[BASE_COLUMNS] 

                num_cols = ['Gross Earnings','EPF wages','EPS Wages','EDLI Wages','EPF Contribution','EPS Contibution','EDLI Contibution','No of LOP Days','Total Contribution']

                df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce', axis=1)             

                sum_row = [df[col].sum() if col in ['Gross Earnings','EPF wages','EPS Wages','EDLI Wages','EPF Contribution','EPS Contibution','EDLI Contibution','No of LOP Days','Total Contribution'] else "" for col in df]

                df.loc[len(df.index)] = sum_row

                headers = pd.MultiIndex.from_tuples([                                
                                ('Organisation', 'Name'),
                                (org_name, 'EMP ID'),
                                (org_name, 'PF No'),
                                (org_name, 'Designation'),
                                (org_name, 'Department'),
                                ('Month', 'UAN No'),
                                (month_year, 'Gross Earnings'),
                                (month_year, 'EPF wages'),
                                (month_year, 'EPS Wages'),
                                ('', 'EDLI Wages'),
                                ('', 'EPF Contribution'),
                                ('', 'EPS Contribution'),
                                ('', 'EDLI Contribution'),
                                ('', 'No of LOP Days'),
                                ('', 'Total Contribution')
                            ])

                # Assign the MultiIndex to the columns of the existing DataFrame
                df.columns = headers
                
                data = df.reset_index(drop=True)
                data.index = data.index + 1

                file_name = "epf_report.xlsx"

                response = HttpResponse(content_type="text/ms-excel")
                response[
                    "Content-Disposition"
                ] = f'attachment; filename="{file_name}"'
                data.to_excel(response, index=True, index_label="S. No",startrow=0)
                return response
            

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(epf_qs, request)

            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id = request.query_params.get('company_id'))}, msg= "Successfully fetched epf data"
                ),
            status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

class EsiSummaryApi(APIView):
    model = PayrollInformation
    pagination_class = CustomPagePagination

    def get(self, request):
        try:    
            params = request.query_params
            q_filters = db_models.Q(employee__company_id=request.query_params.get('company_id'),is_processed=True)
            
            if "dept_id" in params:
                q_filters &= db_models.Q(employee__work_details__department__id__in = request.query_params.getlist('dept_id'))

            if "emp_id" in params:
                q_filters &= db_models.Q(employee__id__in = request.query_params.getlist('emp_id'))

            if "month_year" in params:
                q_filters &= db_models.Q(month_year__in = request.query_params.getlist('month_year'))

            q_filters &= db_models.Q(total_esi_contribution__gt=0)

            esi_qs = self.model.objects.filter(q_filters).annotate(
                user_name = F('employee__user__username'),
                company_name = F('employee__company__company_name'),
                employee_number = F('employee__work_details__employee_number'),
                pf_num = F('employee__emp_compliance_detail__pf_num'),
                uan_num = F('employee__emp_compliance_detail__uan_num'),
                esi_num = StringAgg(
                    Case(
                        When(Q(employee__emp_compliance_detail__esi_num__in=[None, 'na', '', 'null', 'None'])|Q(employee__emp_compliance_detail__esi_num__isnull=True),
                        then=Value('NA')),
                        default=F('employee__emp_compliance_detail__esi_num'),
                        output_field=db_models.CharField()
                    ),
                    delimiter=', ', distinct=True),
                designation_name = F('employee__work_details__designation__name'),
                department_name = F('employee__work_details__department__name'),
                ).values('month_year', 'user_name', 'company_name', 'employee_number', 'pf_num', 'uan_num', 'esi_num', 'designation_name', 'department_name', 'paid_days', 'earned_gross', 'employee_esi', 'employer_esi', 'total_esi_contribution')

            if ("download" in params) and (params['download']=="true"):
                df = pd.DataFrame(esi_qs) 
                org_name = df['company_name'][0]
                df['uan_num'] = df['uan_num'].astype(str)
                
                df['month_year'] = pd.to_datetime(df.month_year)

                df['month_year'] = df['month_year'].dt.strftime('%b-%Y')
                month_year = df['month_year'][0]
              
                # month_year	paid_days	earned_gross	employee_esi	employer_esi	total_esi_contribution	user_name	company_name	employee_number	pf_num	uan_num	esi_num	designation_name	department_name

                df.rename(columns = {'user_name':'Name','employee_number':'EMP ID','designation_name':'Designation','department_name':'Department','esi_num':'ESI No','paid_days':'No. of paid days','earned_gross':'Gross Earnings','employee_esi':'Employee ESI Contribution','employer_esi':'Employer ESI Contribution',"total_esi_contribution":"Total Contribution"}, inplace = True)
             
             
                # df['S. NO'] = df.reset_index().index + 1
                
                BASE_COLUMNS = ['EMP ID','Name','Designation','Department','ESI No','No. of paid days','Gross Earnings','Employee ESI Contribution','Employer ESI Contribution','Total Contribution']
                
                df = df[BASE_COLUMNS]      

                num_cols = ['No. of paid days','Gross Earnings','Employee ESI Contribution','Employer ESI Contribution','Total Contribution']

                df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce', axis=1)          

                sum_row = [df[col].sum() if col in ['Employee ESI Contribution','Employer ESI Contribution','Total Contribution'] else "" for col in df]

                df.loc[len(df.index)] = sum_row

                headers = pd.MultiIndex.from_tuples([                                
                                ('Organisation', 'EMP ID'),
                                (org_name, 'Name'),                                
                                (org_name, 'Designation'),
                                (org_name, 'Department'),
                                ('Month', 'ESI No'),
                                (month_year, 'No. of paid days'),
                                (month_year, 'Gross Earnings'),
                                (month_year, 'Employee ESI Contribution'),
                                ('', 'Employer ESI Contribution'),
                                ('', 'Total Contribution')                               
                            ])

                # Assign the MultiIndex to the columns of the existing DataFrame
                df.columns = headers
                
                data = df.reset_index(drop=True)
                data.index = data.index + 1

                file_name = "esi_report.xlsx"

                response = HttpResponse(content_type="text/ms-excel")
                response[
                    "Content-Disposition"
                ] = f'attachment; filename="{file_name}"'
                data.to_excel(response, index=True, index_label="S. No",startrow=0)
                return response


                # file_name = "esi_report.xlsx"
                # return excel_converter(df,file_name)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(esi_qs, request)

            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id = request.query_params.get('company_id'))}, msg= "Successfully fetched esi data"
                ),
            status=status.HTTP_200_OK
            )    
        
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

class PtSummaryApi(APIView):
    model = PayrollInformation
    pagination_class = CustomPagePagination

    def get(self, request):
        try:    
            params = request.query_params
            q_filters = db_models.Q(employee__company_id=request.query_params.get('company_id'))
            q_filters &= db_models.Q(is_processed=True)            
            
            if "dept_id" in params:
                q_filters &= db_models.Q(employee__work_details__department__id__in = request.query_params.getlist('dept_id'))

            if "emp_id" in params:
                q_filters &= db_models.Q(employee__id__in = request.query_params.getlist('emp_id'))

            if "month_year" in params:
                q_filters &= db_models.Q(month_year__in = request.query_params.getlist('month_year'))

            # pt_qs = PayrollInformation.objects.filter(q_filters).values('month_year', 'employee__user__username', 'employee__company__company_name', 'employee__work_details__employee_number', 'employee__work_details__designation__name', 'employee__work_details__department__name', 'profession_tax')
            pt_qs = PayrollInformation.objects.filter(q_filters).annotate(
                user_name=F('employee__user__username'),
                company_name = F('employee__company__company_name'),
                employee_number = F('employee__work_details__employee_number'),
                designation__name = F('employee__work_details__designation__name'),
                department_name = F('employee__work_details__department__name'),
                ).values('month_year', 'user_name', 'company_name', 'employee_number', 'designation__name', 'employee__work_details__department__name', 'profession_tax')
            
            if ("download" in params) and (params['download']=="true"):
                df = pd.DataFrame(pt_qs) 
                df['month_year'] = pd.to_datetime(df.month_year)

                df['month_year'] = df['month_year'].dt.strftime('%b-%Y')
                df.rename(columns = {'month_year':'Month Year','employee__work_details__department__name':'Department Name','profession_tax':'Profession Tax','user_name':'User Name','company_name':'Company Name','employee_number':'Employee Number','designation_name':'Designation Name'}, inplace = True)

                file_name = "pt_report.xlsx"
                return excel_converter(df,file_name)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(pt_qs, request)

            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id = request.query_params.get('company_id'))}, msg= "Successfully fetched professional tax data"
                ),
            status=status.HTTP_200_OK
            )                                                            
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

class PtSlabApi(APIView):
    """
    old:PtSlabApi
    new:PtSlabApiV2
    """
    model = PayrollInformation
    pagination_class = CustomPagePagination
    
    def get(self, request):
        try:    
            params = request.query_params
            q_filters = db_models.Q(employee__company_id=request.query_params.get('company_id'))
            q_filters &= db_models.Q(is_processed=True)            
            
            if "dept_id" in params:
                q_filters &= db_models.Q(employee__work_details__department__id__in = request.query_params.getlist('dept_id'))

            if "emp_id" in params:
                q_filters &= db_models.Q(employee__id__in = request.query_params.getlist('emp_id'))

            if "month_year" in params:
                q_filters &= db_models.Q(month_year__in = request.query_params.getlist('month_year'))
         
            pt_slab_dict = []
            
            pt_slab_qs = PayrollInformation.objects.filter(q_filters & db_models.Q(earned_gross__lte = 15000) & db_models.Q(earned_gross__gte = 0)).values('profession_tax').annotate(
                                    # min_gross=Round(Min("earned_gross")),
                                    # max_gross=Round(Max("earned_gross")),
                                    total_professional_tax=Round(Sum("profession_tax")),
                                    total_employees=Count("employee")
            ).order_by('profession_tax')
            if(pt_slab_qs):
                for dt in pt_slab_qs:
                    pt_slab_dict.append({
                        "min_gross": 0, 
                        "max_gross":15000,
                        "total_professional_tax":dt['total_professional_tax'],
                        "professional_tax":dt['profession_tax'],
                        "total_employees":dt['total_employees']
                        })   
            else:
                pt_slab_dict.append({
                        "min_gross": 0, 
                        "max_gross":15000,
                        "total_professional_tax":0,
                        "professional_tax":0,
                        "total_employees":0
                        })   
                
            pt_slab_qs = PayrollInformation.objects.filter(q_filters & db_models.Q(earned_gross__lte = 20000) & db_models.Q(earned_gross__gte = 15001)).values('profession_tax').annotate(
                            # min_gross=Round(Min("earned_gross")),
                            # max_gross=Round(Max("earned_gross")),
                            total_professional_tax=Round(Sum("profession_tax")),
                            total_employees=Count("employee")
            ).order_by('profession_tax')
            if(pt_slab_qs):
                for dt in pt_slab_qs:
                    pt_slab_dict.append({
                        "min_gross": 15001, 
                        "max_gross":20000,
                        "total_professional_tax":dt['total_professional_tax'],
                        "professional_tax":dt['profession_tax'],
                        "total_employees":dt['total_employees']
                    }) 
            else:
                pt_slab_dict.append({
                        "min_gross": 15001, 
                        "max_gross":20000,
                        "total_professional_tax":0,
                        "professional_tax":150,
                        "total_employees":0
                        })   


            pt_slab_qs = PayrollInformation.objects.filter(q_filters & db_models.Q(earned_gross__gte = 20001) ).values('profession_tax').annotate(
                            # min_gross=Round(Min("earned_gross")),
                            max_gross=Round(Max("earned_gross")),
                            total_professional_tax=Round(Sum("profession_tax")),
                            total_employees=Count("employee")
            ).order_by('profession_tax')
            if(pt_slab_qs):
                for dt in pt_slab_qs:
                    pt_slab_dict.append({
                        "min_gross": 20001,                
                        "max_gross":"Above",
                        "total_professional_tax":dt['total_professional_tax'],
                        "professional_tax":dt['profession_tax'],
                        "total_employees":dt['total_employees']
                    })   
            else:                
                pt_slab_dict.append({
                    "min_gross": 20001,                
                    "max_gross":"Above",
                    "total_professional_tax":0,
                    "professional_tax":200,
                    "total_employees":0
                })   



            if ("download" in params) and (params['download']=="true"):
                df = pd.DataFrame(pt_slab_dict) 
                df['Gross Salary'] = df['min_gross'].astype(str) + '-' + df['max_gross'].astype(str)
                df.rename(columns = {'total_employees':'No. of Employees',"professional_tax":"Slab","total_professional_tax":"Total"}, inplace = True)

                df['S. No'] = df.reset_index().index + 1
                df = df[['S. No','Gross Salary','No. of Employees','Slab','Total']] 

                sum_row = ["","Total",df['No. of Employees'].sum(),"",df['Total'].sum()]

                df.loc[len(df.index)] = sum_row

                file_name = "pt_slab_report.xlsx"
                return excel_converter(df,file_name)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset([pt_slab_dict], request)

            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id = request.query_params.get('company_id'))}, msg= "Successfully fetched professional tax data"
                ),
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )


class PtSlabApiV2(AbstractAPIView):
    """
    this class is used to get the pt slab info based on earned gross ranges 
    old:PtSlabApi
    new:PtSlabApiV2
    """
    model = PayrollInformation    
    def get(self, request):
        try:    
            params = request.query_params
            q_filters = db_models.Q(employee__company_id=request.query_params.get('company_id'))
            q_filters &= db_models.Q(is_processed=True)            
            
            if "dept_ids" in params:
                q_filters &= db_models.Q(employee__work_details__department_id__in = request.query_params.get('dept_ids').split(','))

            if "emp_ids" in params:
                q_filters &= db_models.Q(employee__id__in = request.query_params.get('emp_ids').split(','))

            if "month_years" in params:
                q_filters &= db_models.Q(month_year__in = request.query_params.get('month_years').split(','))
        
            dct = {
                'case1_emps': Count("employee", filter=db_models.Q(earned_gross__lte=15000, earned_gross__gte=0)),
                'case1_pt_total': Round(Sum('profession_tax', filter=db_models.Q(earned_gross__lte=15000, earned_gross__gte=0))),
                'case2_emps': Count("employee", filter=db_models.Q(earned_gross__lte=20000, earned_gross__gte=15001)),
                'case2_pt_total': Round(Sum('profession_tax', filter=db_models.Q(earned_gross__lte=20000, earned_gross__gte=15001))),
                'case3_emps': Count("employee", filter=db_models.Q(earned_gross__gte=20001)),
                'case3_pt_total': Round(Sum('profession_tax', filter=db_models.Q(earned_gross__gte=20001))),
                }
            payroll_qs = self.model.objects.filter(q_filters).aggregate(**dct)
            payroll_qs.update(**{'case1_monthly_gross':'0-15000', 'case1_slab':0, 'case2_monthly_gross':'15001-20000', 'case2_slab':150, 'case3_monthly_gross':'20000-Above', 'case3_slab':200})

            return Response(
                success_response(
                    result={"data":payroll_qs,"filters_data":filters_data_func(cmp_id = request.query_params.get('company_id'))}, msg= "Successfully fetched professional tax data"
                ),
            status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
class VarianceReportApi(APIView):
    model = PayrollInformation
    pagination_class = CustomPagePagination
    
    def get(self, request):
        try:    
            params = request.query_params
            q_filters = db_models.Q(employee__company_id=request.query_params.get('company_id'),is_deleted=False,is_processed=True)        
            
            attribute = params.get('attribute')

            timeline = params.get('timeline')       

            now = timezone.now()
            
            month_quarter = {1:[4,5,6],2:[7,8,9],3:[10,11,12],4:[1,2,3]}

            if timeline == "current financial year":    
                f_from_date, f_to_date = get_financial_year_start_and_end(now)
                from_date = datetime.datetime.strptime("01-04-"+str(f_from_date), '%d-%m-%Y').strftime('%Y-%m-01')
                to_date =   datetime.datetime.strptime("31-03-"+str(f_to_date), '%d-%m-%Y').strftime('%Y-%m-01')  
                q_filters &= Q(month_year__gte=from_date)   
                q_filters &= Q(month_year__lte=to_date)            

            elif timeline == "current quarter":  
                current_quarter = [k for k,v in month_quarter.items() if now.month in v]
                current_quarter = current_quarter[0]
                if current_quarter  == 1:
                    from_date = datetime.datetime.strptime("01-04-"+str(now.year), '%d-%m-%Y').strftime('%Y-%m-01')  
                if current_quarter  == 2:
                    from_date = datetime.datetime.strptime("01-07-"+str(now.year), '%d-%m-%Y').strftime('%Y-%m-01')  
                if current_quarter  == 3:
                    from_date = datetime.datetime.strptime("01-10-"+str(now.year), '%d-%m-%Y').strftime('%Y-%m-01')  
                if current_quarter  == 4:
                    from_date = datetime.datetime.strptime("01-01-"+str(now.year), '%d-%m-%Y').strftime('%Y-%m-01')  
                q_filters &= Q(month_year__gte=from_date)            
            elif timeline == "last quarter":   
                current_quarter = [k for k,v in month_quarter.items() if now.month in v]
                current_quarter = current_quarter[0]
                if current_quarter  == 1:
                    date_1 = "01-01-"+str(now.year)
                    date_2 = "01-03-"+str(now.year)
                elif current_quarter  == 2:
                    date_1 = "01-04-"+str(now.year)
                    date_2 = "01-06-"+str(now.year)                
                elif current_quarter  == 3:
                    date_1 = "01-07-"+str(now.year)
                    date_2 = "01-09-"+str(now.year)                
                elif current_quarter  == 4:
                    date_1 = "01-10-"+str(now.year)
                    date_2 = "01-12-"+str(now.year)            
                from_date = datetime.datetime.strptime(date_1, '%d-%m-%Y').strftime('%Y-%m-01')  
                to_date = datetime.datetime.strptime(date_2, '%d-%m-%Y').strftime('%Y-%m-01')  
                q_filters &= Q(month_year__gte=from_date)            
                q_filters &= Q(month_year__lte=to_date)            
            elif timeline == "Last 3 months":                
                from_date = (datetime.date.today() - relativedelta(months=3)).strftime('%Y-%m-01')                
                q_filters &= Q(month_year__gte=from_date)
            elif timeline == "Last 6 months":                
                from_date = (datetime.date.today() - relativedelta(months=6)).strftime('%Y-%m-01')                
                q_filters &= Q(month_year__gte=from_date)
            elif timeline == "Last 12 months":                
                from_date = (datetime.date.today() - relativedelta(months=12)).strftime('%Y-%m-01')                
                q_filters &= Q(month_year__gte=from_date)
            elif "FY-" in timeline:        
                end_yr = timeline.split("-")        
                end_yr = int(end_yr[1])
                from_date = datetime.datetime.strptime("01-04-"+str(end_yr-1), '%d-%m-%Y').strftime('%Y-%m-01')                
                to_date = datetime.datetime.strptime("01-04-"+str(end_yr), '%d-%m-%Y').strftime('%Y-%m-01')                
                q_filters &= Q(month_year__gte=from_date)
                q_filters &= Q(month_year__lt=to_date)
          
     
            if attribute == "salary disbursed":
                all_emp_obj = PayrollInformation.objects.filter(q_filters).values('month_year').annotate(total=Coalesce(Sum('net_pay'),  0, output_field=db_models.IntegerField())).order_by('-month_year')

            elif attribute == "TDS/PF/PT/ESI":
                all_emp_obj = PayrollInformation.objects.filter(q_filters).values('month_year').annotate(tds_total=Sum('monthly_tds'),esi_total=Sum('total_esi_contribution'), epf_total=Sum('total_epf_contribution'), pt_total=Sum('profession_tax')).order_by('-month_year')                      
            if ("download" in params) and (params['download']=="true"):
                df = pd.DataFrame(all_emp_obj)
                df.rename(columns = {'month_year':'Month Year','total':'Total'}, inplace = True)

                file_name = "variance_report.xlsx"
                return excel_converter(df,file_name)
            
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(all_emp_obj, request)

            filters_data = {"attribute":['salary disbursed', 'TDS/PF/PT/ESI'], "timeline":["current financial year", "current quarter", "last quarter", "Last 3 months", "Last 6 months", "Last 12 months", "FY-"+str(now.year-1)]}

            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data}, msg= "Successfully fetched variance report data"
                ),
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )


class SalaryInfoReportApi(APIView):
    model = PayrollInformation
    pagination_class = CustomPagePagination
    
    def get(self, request):
        try:    
            params = request.query_params
            q_filters = db_models.Q(employee__company_id=request.query_params.get('company_id'),is_deleted=False,is_processed=True)                        

            year = params.get('year')
            if year:                   
                q_filters &= Q(month_year__year=year)                           
           
            all_emp_obj = PayrollInformation.objects.filter(q_filters).annotate(year=TruncYear('month_year')).values('year').annotate(total=Sum('net_pay')).order_by('-year')
    


            if ("download" in params) and (params['download']=="true"):
                df = pd.DataFrame(all_emp_obj)
                df.rename(columns = {'year':'Year','total':'Total'}, inplace = True)

                file_name = "pt_slab_report.xlsx"
                return excel_converter(df,file_name)
            
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(all_emp_obj, request)

            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_year_func(cmp_id = request.query_params.get('company_id'), only_years=True)}, msg= "Successfully fetched professional tax data"
                ),
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )


class EmployeeReportsApi(APIView):
    model = Employee
    pagination_class = CustomPagePagination
    
    def get(self, request):
        try:    
            params = request.query_params

            # ars_obj = AttendanceRuleSettings.objects.get(company__id=request.query_params.get('company_id'))
            # pay_cycle_end_day = ars_obj.attendance_input_cycle_to

            # payroll_data = PayrollInformation.objects.filter(is_processed=True).order_by('month_year').last()
        
            # if payroll_data:
            #     pend_date = payroll_data.month_year.replace(day=pay_cycle_end_day) + relativedelta(months=1)
            # else:
            #     pend_date = ars_obj.attendance_paycycle_end_date
            
            pend_date = get_payroll_month_year(company = request.query_params.get('company_id'), company_obj=False)['payroll_end_date']

            q_filters = db_models.Q(company_id=request.query_params.get('company_id'))
            # q_filters &= db_models.Q(is_processed=True)            
            q_filters &= db_models.Q(date_of_join__lte=pend_date)            
            
            if "dept_id" in params:
                q_filters &= db_models.Q(work_details__department__id__in = request.query_params.get('dept_id').split(','))

            if "emp_id" in params:
                q_filters &= db_models.Q(id__in = request.query_params.get('emp_id').split(','))

            q_filters &= (db_models.Q(payroll_status=True) | db_models.Q(payroll_status__isnull=True))
            
        
            emp_report_qs = Employee.objects.filter(q_filters).annotate(
                father_name = StringAgg('employee_family_details__name',delimiter=', ',filter =db_models.Q(employee_family_details__relationship__relationship_type = RelationshipTypes.FATHER,), distinct = True),
                mother_name = StringAgg('employee_family_details__name',delimiter=', ',filter =db_models.Q(employee_family_details__relationship__relationship_type = RelationshipTypes.MOTHER,), distinct = True),
                pan_number = StringAgg('employee_document_ids__document_number',delimiter=', ',filter =db_models.Q(employee_document_ids__document_type__document_type = DocumentsTypes.PAN_CARD,), distinct = True),
                aadhar_number = StringAgg('employee_document_ids__document_number',delimiter=', ',filter =db_models.Q(employee_document_ids__document_type__document_type = DocumentsTypes.AADHAAR_CARD,), distinct = True),
                user_name = F('user__username'),
                company_name = F('company__company_name'),
                employee_number = F('work_details__employee_number'),
                designation_name = F('work_details__designation__name'),
                department_name = F('work_details__department__name'),                
                ifsc_code = F('salary_details__ifsc_code'),
                # date_of_birth = F('date_of_birth'),
                # marital_status = F('marital_status'),
                # nominee_name = F('emp_compliance_detail__nominee_name'),
                nominee_name = StringAgg(
                                        Case(
                                            When(Q(emp_compliance_detail__nominee_name__in=[None, 'na', '', 'null', 'None'])|Q(emp_compliance_detail__nominee_name__isnull=True),
                                            then=Value('NA')),
                                            default=F('emp_compliance_detail__nominee_name'),
                                            output_field=db_models.CharField()
                                        ),
                                        delimiter=', ', distinct=True),
                # nominee_rel = F('emp_compliance_detail__nominee_rel'),
                nominee_rel = StringAgg(
                                        Case(
                                            When(Q(emp_compliance_detail__nominee_rel__in=[None, 'na', '', 'null', 'None'])|Q(emp_compliance_detail__nominee_rel__isnull=True),
                                            then=Value('NA')),
                                            default=F('emp_compliance_detail__nominee_rel'),
                                            output_field=db_models.CharField()
                                        ),
                                        delimiter=', ', distinct=True),

                nominee_dob = F('emp_compliance_detail__nominee_dob'),
                pf_num = F('emp_compliance_detail__pf_num'),
                uan_num = F('emp_compliance_detail__uan_num'),
                # esi_num = F('emp_compliance_detail__esi_num'),
                esi_num = StringAgg(
                                    Case(
                                        When(Q(emp_compliance_detail__esi_num__in=[None, 'na', '', 'null', 'None'])|Q(emp_compliance_detail__esi_num__isnull=True),
                                        then=Value('NA')),
                                        default=F('emp_compliance_detail__esi_num'),
                                        output_field=db_models.CharField()
                                    ),
                                    delimiter=', ', distinct=True),
                monthly_ctc = Cast(F('salary_details__ctc')/12, output_field = db_models.IntegerField()),
                annual_ctc = F('salary_details__ctc'),
                bank_name = F('salary_details__bank_name'),
                account_number = F('salary_details__account_number'),
                # personal_email = F('personal_email'),
                # official_email = F('official_email')
                bank_branch_name = F('salary_details__branch_name'),
                ).values('user_name', 'company_name', 'employee_number', 'designation_name', 'department_name', 'monthly_ctc', 'ifsc_code', 'bank_name', 'account_number', 'father_name', 'mother_name', 'date_of_birth', 'date_of_join', 'gender', 'marital_status','nominee_name', 'nominee_rel', 'nominee_dob', 'pf_num','uan_num','pan_number','aadhar_number','esi_num','phone','alternate_phone','personal_email', 'bank_branch_name', 'official_email', 'annual_ctc')
            df = pd.DataFrame(emp_report_qs)
            if not df.empty:
                df['monthly_gross'] = df['monthly_ctc'].apply(lambda x: round(ctc_to_gross_per_year(x * 12) / 12))
            data = df.to_dict(orient='records')

            if ("download" in params) and (params['download']=="true"):
                df = pd.DataFrame(emp_report_qs)
                df['uan_num'] = df['uan_num'].astype(str)
                df['aadhar_number'] = df['aadhar_number'].astype(str)

                df['date_of_join'] = pd.to_datetime(df.date_of_join)

                df['date_of_join'] = df['date_of_join'].dt.strftime('%d-%m-%Y')

                df['nominee_dob'] = pd.to_datetime(df.nominee_dob)

                df['nominee_dob'] = df['nominee_dob'].dt.strftime('%d-%m-%Y')

                file_name = "employee_report.xlsx"
                return excel_converter(df,file_name)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(data, request)

            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_ae_func(cmp_id = request.query_params.get('company_id'),pend_date=pend_date)}, msg= "Successfully fetched employee report data"
                ),
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
class EmployeeOTApi(AbstractAPIView):
    """
    this api is used for calculating the ot days following hrms
    """
    pagination_class = CustomPagePagination

    def get(self, request, *args, **kwargs):
        try:
            """
            params = request.query_params
            q_filters = db_models.Q()
            if "company_id" in params:
                q_filters &= db_models.Q(company__id = request.query_params.get('company_id'))
            if "emp_ids" in params:
                q_filters &= db_models.Q(id__in = request.query_params.getlist('emp_ids'))
            if "month_years" in params:
                q_filters &= db_models.Q(emp_ot__ot_month_year__in = request.query_params.getlist('month_years'))
            
            cmp_id = request.user.employee_details.first().company.id
            # leaves_month_year = get_month_year_for_payroll_to_run_by_company(request.session.get("cmp_id"))# remove the logic for company id as sessions are expiring
            leaves_month_year = get_month_year_for_payroll_to_run_by_company(cmp_id)
            month_and_year=leaves_month_year.strftime('%m-%Y')
            year_month_split_list = month_and_year.split('-')    
            year_of_payroll_running = year_month_split_list[1]

            month_of_payroll_running = int(year_month_split_list[0])
            # month_of_payroll_running = datetime.datetime.strptime(year_month_split_list[0], '%b').month    # in integer -> 1-12                
            
            month_days = monthrange(int(year_of_payroll_running), month_of_payroll_running)[1]       

            pay_cycle_start_day, pay_cycle_end_day = get_pay_cycle_start_and_end_day(request.query_params.get('company_id'),month_days)
            
            financial_year_start, financial_year_end, cur_month, cur_year = get_current_financial_year_start_and_end(month_of_payroll_running,year_of_payroll_running)
            
            pay_cycle_start_date, pay_cycle_end_date = get_pay_cycle_start_and_end_date(financial_year_start,pay_cycle_start_day,month_of_payroll_running,financial_year_end,pay_cycle_end_day,year_of_payroll_running)
        
            q_filters &= db_models.Q(date_of_join__lte = pay_cycle_end_date)
            q_filters &= db_models.Q(payroll_status = True)
            

            emp_qs = Employee.objects.filter(q_filters).annotate(emp_name =  Concat(
                                        F('first_name'),
                                        Value(' '),
                                          F('middle_name') ,
                                          Value(' '),
                                            F('last_name')
                                    ),
                                    p_ot_month_year = db_models.Value(leaves_month_year),
                                    total_ot_count = db_models.Value(0),
                                    ).values('id', 'emp_name', 'p_ot_month_year', 'total_ot_count')

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(emp_qs, request)

            if ("download" in params) and (params['download']=="true"):                
                df = pd.DataFrame(emp_qs)
                df.rename(columns = {'p_ot_month_year':'ot_month_year',
                              'id':'employee'}, inplace = True)

                file_name = "emp_ot_report.xlsx"
                return excel_converter(df,file_name)
        
            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id = request.query_params.get('company_id'))}, msg= "Successfully fetched ot data"
                ),
            status=status.HTTP_200_OK
            )            
            """
            company_obj = request.user.employee_details.first().company
            params = request.query_params
            pay_cycle_end_date = get_payroll_month_year(company_obj)            
            q_filters = db_models.Q(company = company_obj)
            if "company_id" in params:
                q_filters &= db_models.Q(company__id = request.query_params.get('company_id'))
            if "emp_ids" in params:
                q_filters &= db_models.Q(id__in = request.query_params.getlist('emp_ids'))
            if "month_years" in params:
                q_filters &= db_models.Q(emp_ot__ot_month_year__in = request.query_params.getlist('month_years'))
            
            q_filters &= db_models.Q(date_of_join__lte = pay_cycle_end_date['payroll_end_date'])
            q_filters &= db_models.Q(payroll_status = True)

            emp_qs = Employee.objects.filter(q_filters).annotate(emp_name =  Concat(
                                        F('first_name'),
                                        Value(' '),
                                          F('middle_name') ,
                                          Value(' '),
                                            F('last_name')
                                    ),
                                    ot_month_year = db_models.Value(pay_cycle_end_date['payroll_month']),
                                    total_ot_count = db_models.Value(0),
                                    Emp_Email = F('official_email'),
                                    employee_number = StringAgg('work_details__employee_number', delimiter=', ')
                                    ).values('Emp_Email', 'emp_name', 'ot_month_year', 'total_ot_count', 'employee_number')

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(emp_qs, request)

            if ("download" in params) and (params['download']=="true"):                
                df = pd.DataFrame(emp_qs)
                df['ot_month_year'] = pd.to_datetime(df.ot_month_year)
                df['ot_month_year'] = df['ot_month_year'].dt.strftime('%m-%Y')
                df.rename(columns = {'ot_month_year':'OT Month Year', 'Emp_Email':"Employee Email", "emp_name":"Employee Name", "total_ot_count":"Total OT Count" , 'employee_number':'Employee Number'}, inplace = True)
                df = df[['Employee Name', 'Employee Email', 'Employee Number', 'OT Month Year', 'Total OT Count']]
                file_name = f"emp_ot_report_for{str(pay_cycle_end_date['payroll_month'])}.xlsx"
                return excel_converter(df,file_name)
        
            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id = request.query_params.get('company_id'))}, msg= "Successfully fetched ot data"
                ),
            status=status.HTTP_200_OK
            )            

        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request, *args, **kwargs):
        try:
            request_data= request.data            

            file = request.FILES["file"]
            df = pd.read_excel(file, keep_default_na=False, skiprows=0)
            try:
                df['ot_month_year'] = pd.to_datetime(df['OT Month Year'], format='%b-%y')                    
            except Exception as e:
                df['ot_month_year'] = pd.to_datetime(df['OT Month Year'], format='%m-%Y')
            df['year'] = df['ot_month_year'].dt.strftime('%Y')
            df['month'] = df['ot_month_year'].dt.strftime('%m')

            df = df.rename(columns={'Employee Email':'employee', 'Total OT Count':'overtime_count'})
            request_data = df.to_dict(orient="records")   
            
            emp_ot_data = EmployeeMonthlyAttendanceRecordsSerializer(data=request_data, many=True)

            if emp_ot_data.is_valid():
                emp_ot_data.save()
                msg = "sucessfully saved in database"
            else:
                msg = str(emp_ot_data.errors)
            return Response(
                success_response(
                    result="", msg = msg
                ),
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
    def patch(self, request, *args, **kwargs):
        try:
            request_data= request.data
            request_data['updated_from'] = "payroll"
            emp_ot_obj = EmployeeMonthlyAttendanceRecords.objects.get(id = request.data.get('id'))
            emp_ot_data = EmployeeMonthlyAttendanceRecordsSerializer(instance = emp_ot_obj, data=request_data, partial=True)
            if emp_ot_data.is_valid():
                emp_ot_data.save()
                msg = "sucessfully saved in database"
            else:
                msg = str(emp_ot_data.errors)
            return Response(
                success_response(
                    result="", msg = msg
                ),
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )



class EmployeeGratuity(AbstractAPIView):
    pagination_class = CustomPagePagination

    def get(self, request, *args, **kwargs):
        
        try:
            params = request.query_params
            cmp_id = params.get('company_id')

            now = timezone.now()
            cur_year = now.year 
            cur_month = now.month

            #fiveyears_ago = datetime.datetime(cur_year, cur_month-1, now.day)
            fiveyears_ago = datetime.datetime(cur_year, cur_month, now.day)-relativedelta(months=1)
            q_filters = db_models.Q(date_of_join__lte=fiveyears_ago, company_id=cmp_id, work_details__isnull=False)


            if "emp_ids" in params:
                q_filters &= db_models.Q(id__in = request.query_params.getlist('emp_ids'))

            
            emps_eligible_qs = Employee.objects.filter(q_filters)
            basic_amount_pct = PaySalaryComponents.objects.get(company_id=cmp_id, component_name="Basic").pct_of_basic            
            emp_gratuity_data = EmployeeGratuitySerializer(emps_eligible_qs, many=True, context={'basic_amount_pct': basic_amount_pct}).data


            paginator = self.pagination_class()
            page = paginator.paginate_queryset(emp_gratuity_data, request)
            if ("download" in params) and (params['download']=="true"):                
                df = pd.DataFrame(emp_gratuity_data)
                

                df['date_of_join'] = pd.to_datetime(df.date_of_join)
                df['date_of_join'] = df['date_of_join'].dt.strftime('%d-%m-%Y')
                
                df['last_working_day'] = pd.to_datetime(df.last_working_day)

                df['last_working_day'] = df['last_working_day'].dt.strftime('%d-%m-%Y')

                df.rename(columns = {'first_name':'First Name','middle_name':'Middle Name','last_name':'Last Name','date_of_join':'Date of Join','emp_id':'Emp ID','last_working_day':'Last Working Day','eligible_salary':'Eligible Salary','years_worked':'Years Worked','months_worked':'Months Worked','gratuity_amount':'Gratuity Amount'}, inplace = True)

                file_name = "Gratuity_report.xlsx"
                return excel_converter(df,file_name)

            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page)}, msg= "Successfully fetched gratuity data"
                ),
            status=status.HTTP_200_OK
            )   

        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
class MissingInfoApi(AbstractAPIView):

    model = Employee
    serializer_class = EmployeeMissingInfoSerializer
    pagination_class = CustomPagePagination

    def get(self, request):
        try:
            query_params = request.query_params
            cmp_id = query_params.get('company_id')
            query_filters = db_models.Q(is_deleted=False) & db_models.Q(payroll_status=True) & db_models.Q(company__id=cmp_id)
            
            if "emp_ids" in query_params:
                query_filters &= db_models.Q(id__in=query_params.getlist('emp_ids'))
            
            emp_missing_info_qs = self.model.objects.filter(query_filters).annotate(employee_details = JSONObject(
                name=Trim(Concat(F('first_name'),Value(" "),F('middle_name'),Value(" "),F('last_name'),)),
                emp_id= F('id') ))
            
            emp_missing_data = self.serializer_class(emp_missing_info_qs, many=True).data

            if ("download" in query_params) and (query_params['download']=="true"):
                df = pd.DataFrame(emp_missing_data) 
                df.rename(columns = {'employee_details':'Employee Details','missing_info':'Missing Info'}, inplace = True)

                file_name = "missing_info_report.xlsx"  #excel will download but need to format the excel properly will do
                return excel_converter(df,file_name)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(emp_missing_data, request)

            emps_list = self.model.objects.filter(is_deleted=False, payroll_status=True, company__id = cmp_id).annotate(employee_name =
                Trim(Concat(F('first_name'),Value(" "),F('middle_name'),Value(" "),F('last_name'),),),
                emp_id= F('id') ).values('employee_name', 'emp_id')
            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":emps_list}, msg= "Successfully fetched missing info data"
                ),
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )




class EsiComplianceApi(APIView):
    model = PayrollInformation
    pagination_class = CustomPagePagination

    def get(self, request):
        try:    
            params = request.query_params
            q_filters = db_models.Q(employee__company_id=request.query_params.get('company_id'),is_processed=True)
            
            if "dept_id" in params:
                q_filters &= db_models.Q(employee__work_details__department__id__in = request.query_params.getlist('dept_id'))

            if "emp_id" in params:
                q_filters &= db_models.Q(employee__id__in = request.query_params.getlist('emp_id'))

            if "year" in params:
                q_filters &= db_models.Q(month_year = request.query_params.get('year'))

            q_filters &= db_models.Q(total_esi_contribution__gt=0)

            esi_qs = self.model.objects.filter(q_filters).annotate(
                # user_name = F('employee__user__username'),
                user_name = Concat(
                        F('employee__first_name'),
                        Value(" "),
                        F('employee__middle_name'),
                        Value(" "),
                        F('employee__last_name'),
                    ),
                company_name = F('employee__company__company_name'),
                employee_number = F('employee__work_details__employee_number'),                
                esi_num = F('employee__emp_compliance_detail__esi_num'),                
                ).values('month_year', 'user_name', 'employee_number', 'esi_num','paid_days', 'payable_gross')

            q_filters &= db_models.Q(month_year__in = request.query_params.getlist('month_year'))

            esi_qs = self.model.objects.filter(q_filters).annotate(
                # user_name = F('employee__user__username'),
                user_name = Concat(
                        F('employee__first_name'),
                        Value(" "),
                        F('employee__middle_name'),
                        Value(" "),
                        F('employee__last_name'),
                    ),
                company_name = F('employee__company__company_name'),
                employee_number = F('employee__work_details__employee_number'),                
                esi_num = F('employee__emp_compliance_detail__esi_num'),                
                ).values('month_year', 'user_name', 'employee_number', 'esi_num','paid_days', 'payable_gross')
            # print(esi_qs)
            # if esi_qs:
            #     return Response(
            #     success_response(
            #         result={"paginated_data":,"filters_data":filters_data_func(cmp_id = request.query_params.get('company_id'))}, msg= "Successfully fetched esi data"
            #     ),
            # status=status.HTTP_200_OK
            # )
            

            if ("download" in params) and (params['download']=="true"):

                df = pd.DataFrame(esi_qs) 
                # print(df)                

                if esi_qs:
                    # org_name = df['company_name'][0]
                    df['esi_num'] = df['esi_num'].astype(str) 
                    df['paid_days'] = df['paid_days'].apply(lambda x: math.ceil(x))                                            

                    df.rename(columns = {'user_name':'IP Name','payable_gross':'Total Monthly Wages','paid_days':'No of Days for which wages paid/payable during the month','esi_num':'IP Number'}, inplace = True)
                
                    df["Reason Code for Zero workings days(numeric only; provide 0 for all other reasons- Click on the link for reference)"] = 0
                    df["Last Working Day( Format DD/MM/YYYY  or DD-MM-YYYY)"] = ''

                    BASE_COLUMNS = ['IP Number','IP Name','No of Days for which wages paid/payable during the month','Total Monthly Wages','Reason Code for Zero workings days(numeric only; provide 0 for all other reasons- Click on the link for reference)','Last Working Day( Format DD/MM/YYYY  or DD-MM-YYYY)']
                    
                    df = df[BASE_COLUMNS]      

                    num_cols = ['No of Days for which wages paid/payable during the month','Total Monthly Wages','Reason Code for Zero workings days(numeric only; provide 0 for all other reasons- Click on the link for reference)']

                    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce', axis=1)          

                # sum_row = [df[col].sum() if col in ['Employee ESI Contribution','Employer ESI Contribution','Total Contribution'] else "" for col in df]

                # df.loc[len(df.index)] = sum_row

                # headers = pd.MultiIndex.from_tuples([                                
                #                 ('Organisation', 'EMP ID'),
                #                 (org_name, 'Name'),                                
                #                 (org_name, 'Designation'),
                #                 (org_name, 'Department'),
                #                 ('Month', 'ESI No'),
                #                 (month_year, 'No. of paid days'),
                #                 (month_year, 'Gross Earnings'),
                #                 (month_year, 'Employee ESI Contribution'),
                #                 ('', 'Employer ESI Contribution'),
                #                 ('', 'Total Contribution')                               
                #             ])

                # Assign the MultiIndex to the columns of the existing DataFrame
                # df.columns = headers
                
                # data = df.reset_index(drop=True)
                # data.index = data.index + 1
                
                file_name = "esi_compliance_report.xlsx"
                return excel_converter(df,file_name)
                    


                # file_name = "esi_report.xlsx"
                # return excel_converter(df,file_name)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(esi_qs, request)

            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id = request.query_params.get('company_id'))}, msg= "Successfully fetched esi data"
                ),
            status=status.HTTP_200_OK
            )    
        
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )


# class TDSReport(AbstractAPIView):
#     """
#     this class is used to get the tds report
#     """
#     pagination_class = CustomPagePagination

#     def get(self, request, *args, **kwargs):
        
#         try:
#             request_params = request.query_params
#             cmp_id = request.user.employee_details.first().company.id
#             query_filters = Q(is_deleted=False, is_processed=True, employee__company_id=cmp_id)
            
#             if "years" in request_params:
#                 query_filters&=Q(month_year__year__in=request_params.getlist('years'))
#             if "months" in request_params:
#                 query_filters&=Q(month_year__month__in=request_params.getlist('months'))
#             if "depts" in request_params:
#                 query_filters&=Q(employee__work_details__department_id__in=request_params.getlist('depts'))
#             if "empids" in request_params:
#                 emp_query_filters=query_filters&Q(employee_id__in=request_params.getlist('empids'))
#             if not "empids" in request_params:
#                 emp_query_filters = query_filters
            
#             # pannum
#             payroll_inst = PayrollInformation.objects.filter(emp_query_filters).distinct().order_by("month_year").annotate(
#                 pan_number = StringAgg('employee__employee_document_ids__document_number',delimiter=', ',filter =db_models.Q(employee__employee_document_ids__document_type__document_type = DocumentsTypes.PAN_CARD,), distinct = True), 
#                 idc_objs = ArrayAgg(
#                     db_models.expressions.Func(
      
#                         db_models.Value('f1'),Case(When(employee__investmentdeclaration__declaration_forms__parentform_type_id=1, then=F('employee__investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),
                        
#                         db_models.Value('f2'),Case(When(employee__investmentdeclaration__declaration_forms__parentform_type_id=2, then=F('employee__investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),
                        
#                         db_models.Value('f3'),Case(When(employee__investmentdeclaration__declaration_forms__parentform_type_id=3, then=F('employee__investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),
                        
#                         db_models.Value('f4'),Case(When(employee__investmentdeclaration__declaration_forms__parentform_type_id=4, then=F('employee__investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),
                        
#                         db_models.Value('f5'),Case(When(employee__investmentdeclaration__declaration_forms__parentform_type_id=5, then=F('employee__investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),
                        
#                         db_models.Value('f6'),Case(When(employee__investmentdeclaration__declaration_forms__parentform_type_id=6, then=F('employee__investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),
                        
#                         db_models.Value('f7'),Case(When(employee__investmentdeclaration__declaration_forms__parentform_type_id=7, then=F('employee__investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),

#                         default=db_models.Value("json default value"), #this will not print
#                         function='jsonb_build_object',
#                         output_field=db_models.JSONField()),
#                         filter=db_models.Q(employee__investmentdeclaration__start_year=2023, employee__investmentdeclaration__status=60)
#                                     ),
                
#                 # emp_monthly_tds_values = db_models.Value(list(PayrollInformation.objects.filter(employee_id=F('employee_id')).filter(query_filters).values('month_year', 'monthly_tds')), output_field=db_models.CharField()),
#                 # emp_monthly_tds_values = Subquery(PayrollInformation.objects.filter(employee_id = OuterRef('employee_id')).values('id')[:1]),
#                 # emp_monthly_gross_values = db_models.Value(list(PayrollInformation.objects.filter(employee_id=F('employee_id')).filter(query_filters).values('month_year', 'earned_gross')), output_field=db_models.CharField()),
#                 emp_tds_monthly = ArrayAgg('employee__emp_payroll_info__month_year', filter=query_filters&Q(employee_id=F('employee_id'))),
#                 emp_monthly_tds_values = ArrayAgg('employee__emp_payroll_info__monthly_tds', filter=query_filters&Q(employee_id=F('employee_id'))),
#                 emp_gross_monthly = ArrayAgg('employee__emp_payroll_info__month_year', filter=query_filters&Q(employee_id=F('employee_id'))),
#                 emp_monthly_gross_values = ArrayAgg('employee__emp_payroll_info__earned_gross', filter=query_filters&Q(employee_id=F('employee_id'))),

#                 # total_tds = db_models.Value(PayrollInformation.objects.filter(employee_id=F('employee_id')).filter(query_filters).aggregate(Sum('monthly_tds'))['monthly_tds__sum'], output_field=db_models.CharField()),
#                 # total_gross = db_models.Value(PayrollInformation.objects.filter(employee_id=F('employee_id')).filter(query_filters).aggregate(Sum('earned_gross'))['earned_gross__sum'], output_field=db_models.CharField()),
#                 # total_tds = Sum('employee__emp_payroll_info__monthly_tds', filter=query_filters&Q(employee_id=F('employee_id'))),
#                 # total_tds = Subquery(PayrollInformation.objects.filter(db_models.Q(employee_id = OuterRef('employee_id')), query_filters).aggregate(Sum('earned_gross'))),
#                 # total_gross = Sum('employee__emp_payroll_info__earned_gross', filter=query_filters&Q(employee_id=F('employee_id'))),
#                 # total_tds = PayrollInformation.objects.filter(db_models.Q(employee_id = OuterRef('employee_id')), query_filters).annotate(tds_sum = Coalesce(Func('monthly_tds', function='Sum'), decimal.Decimal(0))).values('tds_sum'),
#                 total_tds = Value('9999'),
#                 total_gross = Value('9999'),
#                 # department = F('employee__work_details__department__name'),                
#                 # total_gross = PayrollInformation.objects.filter(db_models.Q(employee_id = OuterRef('employee_id')), query_filters).annotate(gross_sum = Coalesce(Func('earned_gross', function='Sum'), decimal.Decimal(0))).values('gross_sum'),
#                 emp_number = db_models.F('employee__work_details__employee_number'),
#                 emp_name = db_models.F('employee__user__username'),
#                 company_name=db_models.F('employee__company__company_name')).values('id', 'employee_id', 'emp_number', 'department' ,'emp_name', 'company_name', 'pan_number', 'month_year__year', 'emp_monthly_gross_values', 'total_gross', 'idc_objs', 'total_tds','emp_tds_monthly', 'emp_monthly_tds_values', 'emp_gross_monthly')
 
#             df = pd.DataFrame(payroll_inst)
#             df = df.drop_duplicates(subset=['employee_id'])

#             if ("download" in request_params) and (request_params['download']=="true"):
#                 file_name = "tds_report.xlsx"
#                 return excel_converter(df,file_name)
#             paginator = self.pagination_class()
#             page = paginator.paginate_queryset(df.to_dict(orient='records'), request)

#             return Response(
#                 success_response(
#                     result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id)}, msg= "Successfully fetched employee report data"
#                 ),
#             status=status.HTTP_200_OK
#             )
#             # return payroll_inst
#         except Exception as e:
#             return Response(
#                 error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

# class PayrollEmps(AbstractAPIView):

#     def get(self, request):
#         try:
#             query_filters = Q()
#             query_params = request.query_params
#             if 'dept_ids' in query_params:
#                 query_filters&=Q(employee__work_details__department_id__in=request.query_params.getlist('dept_ids'))
#             if 'emp_ids' in query_params:
#                 query_filters&=Q(employee_id__in=request.query_params.getlist('emp_ids'))
#             if 'month_year' in query_params: # "this month and year must be of single no need to be in list"
#                 query_filters&=Q(month_year=request.query_params.get('month_year'))

#             all_run_payroll_instances = PayrollInformation.objects.filter(query_filters)
#             data={"employees":"no employees found", "month_to_run":"no months found"}
#             if all_run_payroll_instances.exists():    
#                 filtered_emps = set(all_run_payroll_instances.values_list('employee', flat=True))
                
#                 last_payroll_run_month = all_run_payroll_instances.order_by('-month_year').first().month_year
#                 last_payroll_run_emps = set(all_run_payroll_instances.filter((Q(month_year = last_payroll_run_month)&(~Q(is_processed=False)))).values_list('employee', flat=True))
#                 #             #returns all the employees based on last payroll month and queryfilters

#                 print("last_payroll_run_emps", last_payroll_run_emps, "filtered_emps", filtered_emps)
#                 if not last_payroll_run_emps == filtered_emps:
#                     employees_not_run_for = filtered_emps-last_payroll_run_emps
#                     data = f"{employees_not_run_for}, employees not run for {last_payroll_run_month}"
#                 else:
#                     data= {"employees":last_payroll_run_emps, "month_to_run":last_payroll_run_month+relativedelta(months=+1)}
            
            
#             filter_qs = Departments.objects.filter(employeeworkdetails__employee__company_id=request.user.employee_details.first().company.id,employeeworkdetails__employee_status="Active").annotate(
#                 employee_details=db_models.expressions.Func(
#                 db_models.Value("employee_name"), Concat(F('employeeworkdetails__employee__first_name'),Value(" "),F('employeeworkdetails__employee__middle_name'),Value(" "),F('employeeworkdetails__employee__last_name')),
#                 db_models.Value("employee_id"),F('employeeworkdetails__employee__id'),
#                 function='jsonb_build_object',
#                 output_field=db_models.JSONField()
#                 )).values("id", "name", "employee_details")

#             return Response(
#                 success_response(
#                     result={"data":data,"filter_qs":filter_qs}, msg= "Successfully fetched run payroll data"
#                 ),
#             status=status.HTTP_200_OK
#             )

#         except Exception as e:
#             return Response(
#                 error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
        



@api_view(['GET'])
def getTaxStatesList(request,**kwargs):
    try:
        states = StatesTaxConfig._meta.get_field('state').choices        
    except:
        states = []
    return Response(states,status=status.HTTP_200_OK)
    

# @api_view(['GET'])
# def get_month_year_for_process(request,**kwargs):
#     try:
#         get_month_year_for_payroll_to_run_by_company(request.session.get("cmp_id"))
#     except:
#         states = []
#     return Response(states,status=status.HTTP_200_OK)
    

@api_view(['GET'])
def get_payroll_completed_month_year_list(request,**kwargs):
    try:
        completed_month_year = list(PayrollInformation.objects.filter(employee__company__id=request.params.get("cmp_id"),is_processed=True).values_list('month_year', flat=True).order_by('month_year').distinct())        
    except:
        completed_month_year = []
    return Response(completed_month_year,status=status.HTTP_200_OK)
    


class processPayrollApi(APIView):
    model = PayrollInformation
    pagination_class = CustomPagePagination
    
    def post(self, request):
        try:
            pay_ids_list = request.data.get('pay_id')                        
            pay_ids_list = pay_ids_list.split(',')

            payroll_obj = PayrollInformation.objects.filter(id__in=pay_ids_list,is_processed=False)            
            payroll_obj_emp_ids = list(payroll_obj.values_list('employee_id',flat=True))                    

            EmployeeMonthlyAttendanceRecords.objects.filter(
                            employee_id__in = payroll_obj_emp_ids, #self.kwargs[self.lookup_url_kwarg],                
                            year = int(payroll_obj[0].month_year.strftime('%Y')),
                            month = int(payroll_obj[0].month_year.strftime('%m'))-1
                        ).update(is_payroll_run = True)                                            

            EmployeeSalaryDetails.objects.filter(employee_id__in = payroll_obj_emp_ids).update(
                    variable_pay = 0, monthly_incentive=0, arrears=0, special_deductions=0, advance_deductions=0
                )
            company_config = CompanyCustomizedConfigurations.objects.filter(company_id = request.user.employee_details.first().company.id)
            if company_config.exists() and company_config.first().can_payroll_auto_deactivate == True:
                attendance_cycle_date = request.user.employee_details.first().company.attendancerulesettings_set.first().attendance_input_cycle_to
                payroll_end = payroll_obj.order_by('-month_year')[0].month_year.replace(day=attendance_cycle_date) #need to fix the day use get_payroll_month_year() this func
                payroll_start = payroll_end - relativedelta(months=1)
                payroll_start = payroll_start + relativedelta(days = 1)
                for p_obj in payroll_obj:
                    emp_obj = p_obj.employee
                    if (hasattr(emp_obj, 'resignation_info')) and (hasattr(emp_obj.resignation_info, 'last_working_day')) and (emp_obj.resignation_info.last_working_day is not None) and (emp_obj.resignation_info.last_working_day <= payroll_end):
                        emp_obj.payroll_status = False
                        emp_obj.save()

            payroll_obj.update(is_processed = True)
            
            return Response({"success":"Payroll process success"},status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
 

class rollbackPayrollApi(APIView):
    model = PayrollInformation
    pagination_class = CustomPagePagination
    
    def post(self, request):
        try:    
            pay_ids_list = request.data.get('pay_id').split(',')
            PayrollInformation.objects.filter(id__in=pay_ids_list).delete()
            
            return Response({"success":"Payroll Rollback success"},status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )


class getListofPayslipsForEmployeeApi(APIView):
    model = PayrollInformation
    pagination_class = CustomPagePagination
    
    def get(self, request):
        try:    
            params = request.query_params
            
            emp_id = params.get('emp_id', request.user.employee_details.first().id)

            all_emp_obj = PayrollInformation.objects.filter(employee__id=emp_id,is_processed=True).values('id','month_year', 'updated_at').order_by('-month_year')

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(all_emp_obj, request)

            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id = request.query_params.get('company_id'))}, msg= "Successfully fetched payslips data"
                ),
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
class EmpTdsReportV2(AbstractAPIView):
    """
    this class is used to get the tds report
    """
    model = Employee
    pagination_class = CustomPagePagination
    serializer = EmpTdsReportSerializerV2

    # def idc_objs_func(self,idc_objs_data, is_json=False):        
    #     if not idc_objs_data:
    #         idc_objs_data = [{'f1':0, 'f2':0, 'f3':0, 'f4':0, 'f5':0, 'f6':0, 'f7':0,"income_from_previous_employer":0,"tds_from_previous_employer":0}] # these can be removed here and keep it array agg default
    #     result = {key: sum(d[key] for d in idc_objs_data) for key in idc_objs_data[0]}
    #     if is_json == True:
    #         return [result]
    #     return result

    def get(self, request):
        try:

            params = request.query_params

            start_year = params.get('start_year')
            end_year = params.get('end_year')
            
            company_id = request.user.employee_details.first().company.id
            
            start_date = date(int(start_year), 4, 1)
            end_date = date(int(end_year), 3, 1)
            q_filters = Q(emp_payroll_info__isnull = False, company_id=company_id, emp_payroll_info__month_year__range=(start_date, end_date))
            
            if 'emp_ids' in params and params.get('emp_ids'):
                q_filters &= (Q(id__in = params.get('emp_ids').split(',')))
            if 'dept_ids' in params and params.get('dept_ids'):
                q_filters &= (Q(work_details__department_id__in = params.get('dept_ids').split(',')))


            qs = Employee.objects.filter(q_filters).distinct()# need to add filters
            filtered_qs = qs.annotate(
                                      emp_name = Concat(F('first_name'),Value(" "),F('middle_name'),Value(" "),F('last_name'),), 
                                      emp_number = F('work_details__employee_number'),                                      
                                      org_name = F('company__company_name'),
                                      pan = StringAgg('employee_document_ids__document_number',delimiter=', ',filter =db_models.Q(employee_document_ids__document_type__document_type = DocumentsTypes.PAN_CARD, employee_document_ids__is_deleted=False), distinct = True),
                                      dept_name = Coalesce('work_details__department__name', Value("NA")),
                                    
                                    # regime_type=Case(   #commenting and using method field as coming duplicates in case, when in FK
                                    # When(
                                    #     Q(investmentdeclaration__start_year__gte=start_year,
                                    #     investmentdeclaration__end_year__lte=end_year,
                                    #     investmentdeclaration__regime_type=InvestmentDeclaration.OLD_TAX_REGIME),
                                    #     then=Value('old')
                                    # ),
                                    # When(
                                    #     Q(investmentdeclaration__start_year__gte=start_year,
                                    #     investmentdeclaration__end_year__lte=end_year,
                                    #     investmentdeclaration__regime_type=InvestmentDeclaration.NEW_TAX_REGIME),
                                    #     then=Value('New')
                                    # ),
                                    # default=Value('NA'),
                                    # output_field=db_models.CharField()
                                    #     ),

                                      approved_amount = Coalesce(Sum('investmentdeclaration__approved_amount',
                                                filter=Q(investmentdeclaration__start_year__gte=start_year, investmentdeclaration__end_year__lte=end_year),
                                                distinct=True
                                            ),Value(decimal.Decimal(0))),
                                      financial_year = Value(start_year+"-"+end_year)
                                        
                                    #   idc_objs = ArrayAgg(
                                    #     db_models.expressions.Func(
                    
                                    #     db_models.Value('f1'),Case(When(Q(investmentdeclaration__declaration_forms__parentform_type_id=1) & Q(investmentdeclaration__start_year__gte=start_year,investmentdeclaration__end_year__lte=end_year, investmentdeclaration__admin_resubmit_status=InvestmentDeclaration.APPROVE), then=F('investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),
                                    #     db_models.Value('f2'),Case(When(Q(investmentdeclaration__declaration_forms__parentform_type_id=2) & Q(investmentdeclaration__start_year__gte=start_year,investmentdeclaration__end_year__lte=end_year, investmentdeclaration__admin_resubmit_status=InvestmentDeclaration.APPROVE), then=F('investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),
                                        
                                    #     db_models.Value('f3'),Case(When(Q(investmentdeclaration__declaration_forms__parentform_type_id=3) & Q(investmentdeclaration__start_year__gte=start_year,investmentdeclaration__end_year__lte=end_year, investmentdeclaration__admin_resubmit_status=InvestmentDeclaration.APPROVE), then=F('investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),
                                        
                                    #     db_models.Value('f4'),Case(When(Q(investmentdeclaration__declaration_forms__parentform_type_id=4) & Q(investmentdeclaration__start_year__gte=start_year,investmentdeclaration__end_year__lte=end_year, investmentdeclaration__admin_resubmit_status=InvestmentDeclaration.APPROVE), then=F('investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),
                                        
                                    #     db_models.Value('f5'),Case(When(Q(investmentdeclaration__declaration_forms__parentform_type_id=5) & Q(investmentdeclaration__start_year__gte=start_year,investmentdeclaration__end_year__lte=end_year, investmentdeclaration__admin_resubmit_status=InvestmentDeclaration.APPROVE), then=F('investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),
                                        
                                    #     db_models.Value('f6'),Case(When(Q(investmentdeclaration__declaration_forms__parentform_type_id=6) & Q(investmentdeclaration__start_year__gte=start_year,investmentdeclaration__end_year__lte=end_year, investmentdeclaration__admin_resubmit_status=InvestmentDeclaration.APPROVE), then=F('investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),
                                        
                                    #     db_models.Value('f7'),Case(When(Q(investmentdeclaration__declaration_forms__parentform_type_id=7) & Q(investmentdeclaration__start_year__gte=start_year,investmentdeclaration__end_year__lte=end_year, investmentdeclaration__admin_resubmit_status=InvestmentDeclaration.APPROVE), then=F('investmentdeclaration__declaration_forms__approved_amount')),default=Value(0),output_field=db_models.FloatField()),
                                        
                                    #     db_models.Value('income_from_previous_employer'), Case(When(Q(investmentdeclaration__income_from_previous_employer__isnull=False) & Q(investmentdeclaration__start_year__gte=start_year, investmentdeclaration__end_year__lte=end_year, investmentdeclaration__admin_resubmit_status=InvestmentDeclaration.APPROVE),then=
                                    #     F('investmentdeclaration__income_from_previous_employer')), default = F('salary_details__previous_income'), output_field=db_models.FloatField()),
                                        
                                    #     db_models.Value('tds_from_previous_employer'),  Case(When(Q(investmentdeclaration__tds_from_previous_employer__isnull=False) & Q
                                    #     (investmentdeclaration__start_year__gte=start_year, investmentdeclaration__end_year__lte=end_year, investmentdeclaration__admin_resubmit_status=InvestmentDeclaration.APPROVE),then=
                                    #     F('investmentdeclaration__tds_from_previous_employer')), default = F('salary_details__previous_tds'), output_field=db_models.FloatField()),                                                                                
                                    #     default=db_models.Value("json default value"),
                                    #     function='jsonb_build_object',
                                    #     output_field=db_models.JSONField()),
                                    #     # filter=db_models.Q(investmentdeclaration__start_year__gte=start_year,investmentdeclaration__end_year__lte=end_year, investmentdeclaration__admin_resubmit_status=InvestmentDeclaration.APPROVE),
                                    #     distinct=True,
                                    #                 ),
                                      )
            
            context = {"start_year":start_year, "end_year":end_year}
            data = self.serializer(filtered_qs, many=True, context = context).data
            df = pd.DataFrame(data)
            # df['idc_objs']=df['idc_objs'].apply(self.idc_objs_func, is_json=True)
            data = df.to_dict(orient='records')
            # if ("download" in params) and (params['download']=="true"):            

            #     modified_idc_df = pd.json_normalize(df['idc_objs'])                
            #     modified_tds_df = pd.json_normalize(df['monthly_tds'])                
            #     # modified_gross_df = pd.json_normalize(df['monthly_gross'])   
            #     modified_net_salary_df = pd.json_normalize(df['monthly_net_salary'])   
            #     df = pd.concat([df,modified_net_salary_df, modified_idc_df, modified_tds_df ], axis=1)
            #     df = df.fillna('')                
            #     df.drop(columns=['idc_objs', 'monthly_tds', 'monthly_net_salary', 'all_payroll_objs'], inplace=True)
            #     BASE_COLUMNS = ['id','emp_number','emp_name','org_name','dept_name','pan','year','income_from_previous_employer','April-NetSalary','May-NetSalary','June-NetSalary','July-NetSalary','August-NetSalary','September-NetSalary','October-NetSalary','November-NetSalary','December-NetSalary','January-NetSalary','February-NetSalary','March-NetSalary', 'total_net_salary', 'f1','f2','f3','f4','f5','f6','f7', 'tds_from_previous_employer','April-TDS','May-TDS','June-TDS','July-TDS','August-TDS','September-TDS','October-TDS','November-TDS','December-TDS','January-TDS','February-TDS','March-TDS','total_tds']
            #     for column in BASE_COLUMNS: 
            #         if column not in df.columns:
            #             df[column] = ""

            #     df = df[BASE_COLUMNS]                
            #     df['year'] = "FY "+str(start_year)+"-"+str(end_year)
            #     # df['total_gross'] = df['income_from_previous_employer'] + df['total_gross']
            #     df['tds_from_previous_employer'] = pd.to_numeric(df['tds_from_previous_employer'])
            #     df['total_tds'] = df['tds_from_previous_employer'] + df['total_tds']
            #     num_cols = ['income_from_previous_employer','April-NetSalary','May-NetSalary','June-NetSalary','July-NetSalary','August-NetSalary','September-NetSalary','October-NetSalary','November-NetSalary','December-NetSalary','January-NetSalary','February-NetSalary','March-NetSalary','total_net_salary','f1','f2','f3','f4','f5','f6','f7', 'tds_from_previous_employer','April-TDS','May-TDS','June-TDS','July-TDS','August-TDS','September-TDS','October-TDS','November-TDS','December-TDS','January-TDS','February-TDS','March-TDS','total_tds']
            #     df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce', axis=1)             

            #     sum_row = [df[col].sum() if col in num_cols else "" for col in df]

            #     df.loc[len(df.index)] = sum_row
            #     df.rename(columns = {'id':'ID','emp_number':'Employee No.','emp_name':'Employee Name','org_name':'Organisation Name','dept_name':'Department Name','pan':'PAN','year':'Year','income_from_previous_employer':'Income from Previous Employer','tds_from_previous_employer':'TDS from Previous Employer','total_tds':'Total TDS','total_net_salary':'Total Net Salary'}, inplace = True)
                
            #     file_name = f"tds_report_for {str(start_year)}-{str(end_year)}.xlsx"
            #     return excel_converter(df,file_name)

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(data, request)
            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page)}, msg= "Successfully fetched tds report data"
                ),
            status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

class runPayrollApi(APIView):
    model = PayrollInformation    
    
    def post(self, request):
        try:               
            emp_ids_list = request.query_params.get('emp_id').split(',')
            dep_ids_list = request.query_params.get('dept_id').split(',')
            month_year = request.query_params.get('month_year')  #Apr-2023
            cmp_id = request.query_params.get('company_id')

            payroll_id = request.query_params.get('payroll_id') if request.query_params.get('payroll_id')  else None
            txp = request.query_params.get('txp') if request.query_params.get('txp') else None

            details_dict = get_all_salary_details(cmp_id, emp_ids_list, dep_ids_list,month_year,payroll_id=payroll_id,txp=txp)    

            return Response({"result":details_dict, "msg": "Successfully fetched professional tax data"},status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )



class checkNullUANEmployees(APIView):
    model = EmployeeComplianceNumbers
    pagination_class = CustomPagePagination
    
    def get(self, request):
        try:    
            params = request.query_params

            query_filters=Q(employee__emp_compliance_detail__uan_num__isnull=True)

            if params.getlist('employees'):
                query_filters &= Q(employee_id__in=params.getlist('employees'))

            if params.getlist('departments'):
                query_filters &= Q(employee__work_details__department__name__in = params.getlist('departments'))

            all_emp_obj = EmployeeComplianceNumbers.objects.filter(query_filters).annotate(                
                employee_name = Concat(
                        F('employee__first_name'),
                        Value(" "),
                        F('employee__middle_name'),
                        Value(" "),
                        F('employee__last_name'),
                    ),
                department = F('employee__work_details__department__name')
                ).values('employee_name','department').order_by('department')
            
            if ("download" in params) and (params['download']=="true"):
                df = pd.DataFrame(all_emp_obj)
                df = df[['employee_name', 'department']]
                file_name = "uan_report.xlsx"
                return excel_converter(df,file_name)

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(all_emp_obj, request)

            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id = request.query_params.get('company_id'))}, msg= "Successfully fetched professional tax data"
                ),
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

class MissingEmployeeInfo(AbstractAPIView):
    """
    this api is used to showcase the employee missing info to run the payroll.
    """

    def get(self, request, *args, **kwargs):
        try:
            today = timezone_now().date()
            emp_qs = Employee.objects.filter((Q(payroll_status=True) | Q(payroll_status__isnull=True)), company=request.user.employee_details.first().company.id, date_of_join__lte = today)
            ser_data = MissingEmployeeInfoSerializer(emp_qs, many=True).data
            return Response(
                success_response(
                    result={"data":ser_data}, msg= "Successfully fetched missing info data"
                ),
            status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )



class PayrollEmps(AbstractAPIView):
    
    def get(self, request):
        try:
            query_filters = Q(payroll_status = True)
            query_filters|= Q(payroll_status__isnull =True)
            query_params = request.query_params
            # attedance_obj = AttendanceRuleSettings.objects.get(company__id = request.user.employee_details.first().company.id) 
            # att_from = attedance_obj.attendance_input_cycle_from
            # att_to = attedance_obj.attendance_input_cycle_to
            # print(request.query_params)
            if 'dept_ids' in query_params:
                query_filters&=Q(work_details__department_id__in=request.query_params.get('dept_ids').split(','))
            if 'emp_ids' in query_params:
                query_filters&=Q(id__in=request.query_params.get('emp_ids').split(','))
            
            # if 'month_year' in query_params: # "this month and year must be of single no need to be in list"
            #     month_year = request.query_params.get('month_year')
            #     run_month = datetime.datetime.strptime(month_year, '%d-%m-%Y').date()
            #     query_filters&=Q(date_of_join__day__gte = att_from) | Q(date_of_join__day__lte = att_to)
            #     query_filters&=Q(date_of_join__month__lte = run_month.month, date_of_join__year__lte = run_month.year)

            # print(query_filters)
            empqs = Employee.objects.filter(query_filters)
            # print(empqs)

            payroll_data = PayrollInformation.objects.filter(employee_id__in = empqs.values('id'),is_processed=True).annotate(emp_last_run_month = Window(expression = Max('month_year'), partition_by=[F('employee_id')]))
            
            if payroll_data:
            
                payroll_months = set(payroll_data.values_list('emp_last_run_month', flat=True))

                resp_payroll_date = list(payroll_data.values("emp_last_run_month"))[0]

            else:            
                from_month_year = AttendanceRuleSettings.objects.get(company__id=request.user.employee_details.first().company.id)    
                payroll_months = from_month_year.attendance_paycycle_end_date - relativedelta(months=1)
                # payroll_months = set(payroll_months)
                resp_payroll_date = {"emp_last_run_month":payroll_months}

            resp_payroll_date['emp_last_run_month'] = resp_payroll_date['emp_last_run_month'] + relativedelta(months=1)

            return Response(resp_payroll_date,status=status.HTTP_200_OK)


            # if len(payroll_months)>1: #will return if already payroll employees month and year is different
            #     return Response(
            #     success_response(
            #         result={"data":payroll_data.values("employee_id", "month_year")}, msg= "employee months are improper"
            #     ),
            # status=status.HTTP_200_OK
            # )

            # payroll_qs_emp_ids = set(payroll_data.values_list('employee_id', flat=True))
            # empqs_emp_ids = set(empqs.values_list('id', flat=True))
            # # print("all employees", empqs_emp_ids)
            
            # payroll_missed_emps = empqs_emp_ids - payroll_qs_emp_ids # the new employee, or employee not existing in payroll
            # # print("payroll missed emps", payroll_missed_emps)

            # if not payroll_missed_emps: #all emps are in payroll and sucess, no new emp's are added.
            #     return Response(resp_payroll_date)
            
            
            # new_payroll_emps = Employee.objects.filter(Q(id__in=payroll_missed_emps), (Q(date_of_join__day__gte = att_from) | Q(date_of_join__day__lte = att_to)), Q(date_of_join__month__lte = run_month.month, date_of_join__year__lte = run_month.year), payroll_status=True)
           
            # payroll_valid_emp_ids = set(new_payroll_emps.values_list('id', flat=True))
            # print("payroll_valid_emp_ids", payroll_valid_emp_ids)    
            
            # missing_emps = payroll_missed_emps - payroll_valid_emp_ids # set

            # if missing_emps:
            # emp_data =Employee.objects.filter(id__in=payroll_missed_emps).values('id', 'first_name')
            # # last_month_year = list(payroll_data.values("emp_last_run_month"))[0]
            # return Response(success_response(
            #     result={"data":emp_data,"last_month_year":resp_payroll_date}, msg= "New Employees some can have joining date more than pay schedule end date. You can proceed but these employees will not be considered for payroll calculation"
            # ),status=status.HTTP_200_OK)
                

            

            # if payroll_valid_emp_ids == payroll_missed_emps:
            #     emp_data =Employee.objects.filter(id__in=payroll_valid_emp_ids).values('id', 'first_name', 'emp_payroll_info__month_year')
            #     return Response(success_response(
            #         result={"data":emp_data}, msg= "success employees to run payroll"
            #     ),status=status.HTTP_200_OK)
            # else:
            #     emp_data =Employee.objects.filter(id__in=missing_emps).values('id', 'first_name', 'date_of_join')
            #     return Response(success_response(
            #         result={"data":emp_data}, msg= "missing these employees"
            #     ),
            # status=status.HTTP_200_OK
            # )


        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
class GetPayslip(AbstractAPIView):
    """
    this class is used to get the payslip for api
    i/p employee id, month_year
    """

    #to do round off's, decimals can be done by pandas or in query directly.
    def post(self, request):
        try:
            emp_id = request.data.get('emp_id', request.user.employee_details.first().id)

            month_year = request.data.get('month_year')

            #need to add directly in query
            payroll_obj = PayrollInformation.objects.get(
            employee__id=emp_id,
            month_year=month_year
            )
            ars_obj = AttendanceRuleSettings.objects.get(company__id=payroll_obj.employee.company.id)
        
            pay_day = ars_obj.attendance_input_cycle_to
            pay_day_end = (payroll_obj.month_year).replace(day=pay_day)
            pay_day_start = pay_day_end - relativedelta(months=1) 
            pay_day_start = pay_day_start + relativedelta(days=1)

            payroll_obj = PayrollInformation.objects.filter(employee_id = emp_id, month_year=month_year).\
                annotate(
                    company_details = db_models.expressions.Func(
                        db_models.Value("company_name"),  F('employee__company__company_name'),
                        db_models.Value("company_image"),  F('employee__company__company_image'),  
                        db_models.Value("registered_line1"), F('employee__company__registered_adress_line1'),
                        db_models.Value("registered_line2"), F('employee__company__registered_adress_line2'),
                        db_models.Value("registered_country"), F('employee__company__registered_country'),
                        db_models.Value("company_hr_email"), F('employee__company__payslip_hr_email'),
                        db_models.Value("company_hr_phone"), F('employee__company__payslip_hr_phone'),
                        db_models.Value("company_cin"), F('employee__company__statutorydetails__cin_number'),
                        db_models.Value("company_address"), Trim(Concat(F('employee__company__registered_state'),Value(" "),F('employee__company__registered_city'),Value(" "),F('employee__company__registered_pincode'),)),
                        function='jsonb_build_object',
                        output_field=db_models.JSONField()
                                                                ),
                    payslip_month_year = F('month_year'),
                    paycycle_start = db_models.Value(pay_day_start),
                    paycycle_end = db_models.Value(pay_day_end),
                    emp_name = Trim(Concat(F('employee__first_name'),Value(" "),F('employee__middle_name'),Value(" "),F('employee__last_name'),)),
                    emp_img =  F('employee__employee_image'),
                    emp_details = db_models.expressions.Func(
                        db_models.Value("emp_id"),  F('employee__work_details__employee_number'),
                        db_models.Value("emp_doj"),F('employee__date_of_join'),
                        db_models.Value("department"),F('department'),
                        db_models.Value("designation"),F('designation'),
                        db_models.Value("location"), Coalesce(F('employee__work_details__work_location'), db_models.Value('NA')),
                        db_models.Value("emp_dob"), F('employee__date_of_birth'),
                        db_models.Value("gender"), F('employee__gender'),
                        db_models.Value("Annual_ctc"), F('yearly_ctc'),
                        db_models.Value("emp_pf"), F('employee__emp_compliance_detail__pf_num'),
                        db_models.Value("emp_esi"), StringAgg(
                                                    Case(
                                                        When(Q(employee__emp_compliance_detail__esi_num__in=[None, 'na', '', 'null', 'None'])|Q(employee__emp_compliance_detail__esi_num__isnull=True),
                                                        then=Value('NA')),
                                                        default=F('employee__emp_compliance_detail__esi_num'),
                                                        output_field=db_models.CharField()
                                                    ),
                                                    delimiter=', ', distinct=True),
                        db_models.Value("emp_uan"), F('employee__emp_compliance_detail__uan_num'),
                        db_models.Value("emp_pan"), StringAgg('employee__employee_document_ids__document_number',delimiter=', ',filter =db_models.Q(employee__employee_document_ids__document_type__document_type = DocumentsTypes.PAN_CARD,), distinct = True),
                        db_models.Value("Bank_Name"), F('bank_name'),
                        db_models.Value("account_number"), F('account_number'),
                        db_models.Value("total_working_days"), F('paid_days'),
                        db_models.Value("lop_days"), F('lop'),                        
                        function='jsonb_build_object',
                        output_field=db_models.JSONField()
                                                                    ),
                    earnings = db_models.expressions.Func(
                        db_models.Value('gross_Basic'), F('s_basic'),
                        db_models.Value('gross_HRA'), F('s_hra'),
                        db_models.Value('gross_Conveyance_Allowance'), F('s_conv'),
                        db_models.Value('gross_Special_Allowance'), F('s_special_allow'),
                        db_models.Value('gross_monthly_incentive'), F('monthly_incentive'),
                        db_models.Value('gross_Arrears'), F('arrears'),
                        
                        db_models.Value('earning_Basic'), F('e_basic'),
                        db_models.Value('earning_HRA'), F('e_hra'),
                        db_models.Value('earning_Conveyance_Allowance'), F('e_conv'),
                        db_models.Value('earning_Special_Allowance'), F('e_special_allow'),
                        db_models.Value('earning_monthly_incentive'), db_models.Value(0),
                        db_models.Value('earning_Arrears'), db_models.Value(0),
                        
                        db_models.Value('Reimbursement'), F('reimbursed_amount'),
                        db_models.Value('Overtime'), F('overtime_pay'),

                        function='jsonb_build_object',
                        output_field=db_models.JSONField()
                                                        ),
                    deductions = db_models.expressions.Func(
                        db_models.Value("Employee_Provident_Fund"), F('employee_pf'),
                        db_models.Value("ESI"), F('employee_esi'),
                        db_models.Value("Professional_Tax"), F('profession_tax'),
                        db_models.Value("Gross_Deductions"), db_models.Value(0),
                        db_models.Value("LOP_Deductions"), F("lop_deduction"),
                        db_models.Value("Income_Tax_TDS"), F("monthly_tds"),
                        db_models.Value("Salary_Advance_Deductions"), db_models.Value(0),
                        db_models.Value("Employee_Loan"), db_models.Value(0),
                        db_models.Value("Other"), db_models.Value(0),
                        function='jsonb_build_object',
                        output_field=db_models.JSONField()
                                                            ),
                    Total_gross = F('total_earnings'),
                    Total_earnings = F('earned_gross'),
                    Total_deductions = F('total_deduction'),
                    NetSalary = F('net_pay'),
                    payslip_water_mark = Case(
                        When(
                            Q(employee__company__payslip_watermark__isnull=False)&                       
                             ~Q(employee__company__payslip_watermark="")&                        
                             Q(employee__company__watermark_status=CompanyDetails.SHOW),
                        then=F('employee__company__payslip_watermark')),
                        default=Value(""),
                        output_field=db_models.CharField(),
                        ),
                    
                    payslip_signature = Case(
                        When(
                            Q(employee__company__payslip_signature__isnull=False)&                       
                             ~Q(employee__company__payslip_signature="")&                        
                             Q(employee__company__signature_status=CompanyDetails.SHOW),
                        then=F('employee__company__payslip_signature')),
                        default=Value(""),
                        output_field=db_models.CharField(),
                        ),
                    
                              )\
                    .values('company_details', 'payslip_month_year', 'paycycle_start', 'paycycle_end', 'emp_name', 'emp_img', 'emp_details', 'earnings', 'deductions', 'Total_gross', 'Total_earnings', 'Total_deductions', 'NetSalary', 'payslip_water_mark', 'payslip_signature')
            df = pd.DataFrame(payroll_obj)
            df['ctc_words'] = df['NetSalary'].apply(lambda x: num2words(x, lang='en_IN'))
            data = df.to_dict(orient='records')

            return Response(
                        success_response(
                            result=data, msg= "Successfully fetched the payslip data"
                        ),status=status.HTTP_200_OK) 
        
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
        



class getSavingDeclarationEmployees(APIView):
    model = Employee
    pagination_class = CustomPagePagination
    
    def get(self, request):
        try:                
            all_emp_obj = Employee.objects.filter(work_details__employee_status="Active", company_id=request.user.employee_details.first().company.id).values('id','first_name','middle_name','last_name','date_of_join')

            now = timezone.now()
            cur_year = now.year 
            cur_month = now.month

            # Eg. Current Month is Jan and Month of payroll Running is Nov / Dec
            if (cur_month < 4):    
                financial_year_end = cur_year
                financial_year_start = cur_year - 1               
            # Eg. Current Month is Feb and Month of payroll Running is Jan
            # Current month is july and running for June
            else:
                financial_year_end = cur_year+1 
                financial_year_start = cur_year 

            data = []        
            for obj in all_emp_obj:
                context = {}
                try:
                    
                    inv_obj = InvestmentDeclaration.objects.get(start_year=financial_year_start,end_year=financial_year_end,employee_id=obj['id'], admin_resubmit_status__in=[InvestmentDeclaration.APPROVE, InvestmentDeclaration.FINAL_APPROVED])
                    context = {
                        "emp_id": obj['id'],
                        'first_name': obj['first_name'],
                        'middle_name': obj['middle_name'],
                        'last_name': obj['last_name'],
                        'date_of_join': obj['date_of_join'],                        
                    }
                    context['id'] = inv_obj.id
                    
                    context['last_submission_date'] = inv_obj.last_submission_date
                    context['regime_type'] = inv_obj.regime_type
                    context['admin_resubmit_status'] = inv_obj.admin_resubmit_status
                except:
                    pass

                if context:
                    data.append(context)

            # paginator = self.pagination_class()
            # page = paginator.paginate_queryset(all_emp_obj, request)

            return Response(
                success_response(
                    result={"data":data}, msg= "Successfully fetched data"
                ),
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
        


class EmployeeBulkVariablePay(AbstractAPIView):
    """
    this class is used to Import and Export the lops bulk CSV in payroll
    """    
    def post(self, request):
        try:
            type= request.data.get("type")
            company_obj = request.user.employee_details.first().company
            
            if type == "upload":
                file = request.FILES["file"]
                
                df = pd.read_excel(file, keep_default_na=False, skiprows=0)             
                variable_pay_objs = df.to_dict(orient="records")                
                
                for variable_pay_obj in variable_pay_objs: 
                    EmployeeSalaryDetails.objects.filter(employee__official_email = variable_pay_obj['Employee Email']).update(variable_pay = variable_pay_obj['Variable Pay'])
                return Response({"msg":"file uploaded sucessfully"},status=status.HTTP_200_OK)

            elif type =="download":

                payroll_month_year = get_payroll_month_year(company_obj)

                month_and_year=payroll_month_year['payroll_month'].strftime('%m-%Y')                    
                pay_cycle_end_date = payroll_month_year['payroll_end_date']

                emps_df = pd.DataFrame(list(Employee.objects.filter
                                        (company__id=company_obj.id, date_of_join__lte = pay_cycle_end_date, payroll_status=True).annotate(employee_name =  Concat(
                                        F('first_name'),
                                        Value(' '),
                                          F('middle_name') ,
                                          Value(' '),
                                            F('last_name')
                                    ),employee_number=F('work_details__employee_number'),
                                    fixed_salary=F('salary_details__fixed_salary'),
                                    ).values('employee_name','employee_number','fixed_salary', 'official_email')))
               
                emps_df.rename(columns = {'employee_name':'Employee Name', 'employee_number':'Employee Number', 'fixed_salary':'Fixed Salary', 'official_email':'Employee Email'}, inplace = True)
                emps_df["Variable Pay Month Year"] = month_and_year
                emps_df["Variable Pay"] = 0                      
                file_name = f"emp_vp_report{str(payroll_month_year['payroll_month'])}.xlsx"
                
                return excel_converter(emps_df,file_name)
            
        except Exception as e:
                return Response({"error":str(e)})

class HoldSalaryReport(AbstractAPIView):
    """
    this class is used to get employees who are on hold(disbursement) for the month
    """
    model = PayrollInformation
    pagination_class = CustomPagePagination

    def get(self, request):
        
        try:    
            params = request.query_params
            cmp_id =  request.user.employee_details.first().company.id
            q_filters = db_models.Q(employee__company_id = cmp_id, is_processed = True, is_on_hold=True)

            if "year" in params:
                q_filters &= db_models.Q(month_year = params.get('month_year'))

            payroll_qs = self.model.objects.filter(q_filters).annotate(
                emp_name = Trim(F('employee__user__username')),
                emp_number=F('employee__work_details__employee_number'),
                designation_name = F('employee__work_details__designation__name'),
                department_name = F('employee__work_details__department__name'),
                status = F('employee__work_details__employee_status')).\
                values('emp_number', 'emp_name', 'designation_name', 'department_name', 'month_year', 'net_pay', 'status')

            if ("download" in params) and (params['download']=="true"):
                df = pd.DataFrame(payroll_qs) 
                df['month_year'] = pd.to_datetime(df.month_year)

                df['month_year'] = df['month_year'].dt.strftime('%b-%Y')
                df.rename(columns = {'month_year':'Month year', 'net_pay':'Net Pay', 'emp_name':'Emp Name', 'emp_number':'Emp Number','designation_name':'Designation Name','status':'Status'}, inplace = True)
                
                file_name = "HoldSalaryReport.xlsx"
                return excel_converter(df,file_name)
            
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(payroll_qs, request)
            
            return Response(
                    success_response(
                        result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_year_func(cmp_id)}, msg= "Successfully fetched payroll Hold Salary data"
                    ),
                status=status.HTTP_200_OK
                )
        
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
                )


class EsiComplianceReminder(APIView):            

    def get(self,request,*args, **kwargs):
        try:          
            rem_dates = ReminderDates.objects.get(company_id=request.query_params.get('cmp_id'))                     
            return JsonResponse({"data":rem_dates.esi_compliance_date})            

        except Exception as e:
            print("error in EsiComplianceReminder get request"+str(e))
    
    def patch(self,request,*args, **kwargs):
        try:       
            rem_dates = ReminderDates.objects.get(company_id=request.query_params.get('cmp_id'))                     
            rem_dates.esi_compliance_date = request.query_params.get("esi_compliance_date")
            rem_dates.save()
            return JsonResponse({"data":rem_dates.esi_compliance_date})            
        except Exception as e:
            return JsonResponse({"msg":"expection occured at server"+str(e)})

    def post(self,request,*args, **kwargs):
        try:       
            rem_dates = ReminderDates.objects.create(company_id=request.query_params.get('cmp_id'))         
            rem_dates.esi_compliance_date = request.query_params.get("esi_compliance_date")
            rem_dates.save()
            return JsonResponse({"data":rem_dates.esi_compliance_date})            
        except Exception as e:
            return JsonResponse({"msg":"expection occured at server"+str(e)})
        

class GetPayrollMonthYear(APIView):
    """
    this class is used to get the payroll month and year to based on request user.
    """
    def get(self, request):
        company = request.user.employee_details.first().company
        data = get_payroll_month_year(company)
        return Response(data)

class GetPaySlipFields(AbstractAPIView):
    """
    this class is used to get all the fields in the company
    A company can have only one fields obj.
    """
    def get(self,request):
        try:
            company = request.user.employee_details.first().company
            if not hasattr(company, 'payslip_fields'):
                services.init_payslip_fields(self, company)
            cmp_fields = company.payslip_fields
            cmp_fields_data = PayslipFieldsSerializer(cmp_fields).data
            return Response(data=cmp_fields_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )    

class GetPayslipTemplates(AbstractAPIView):
    """
    this class is used to get the list of all templates in the company
    """
    def get(self,request):
        try:
            params = request.query_params
            q_filters=Q(is_deleted = False)
            if 'id' in params:
                q_filters &= Q(id=params.get('id'))
            company = request.user.employee_details.first().company
            if not hasattr(company, 'payslip_templates.all()'):
                services.init_payslip_templates(self, company)
            cmp_templates = company.payslip_templates.filter(q_filters).values()
            return Response(data=cmp_templates, status=status.HTTP_200_OK)
        except (ObjectDoesNotExist):
            return Response(data=[], status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

class TemplateFields(AbstractAPIView):
    """
    this class is used to setup the payslip templates with their fields
    """
    model = PayslipTemplateFields
    parser_classes = (JSONParser,)

    def get(self, request):
        try:
            params = request.query_params
            q_filters=Q(is_deleted = False)
            if 'id' in params:
                q_filters &= Q(id=params.get('id'))
            if 'get_selected' in params:
                q_filters &= Q(is_selected=params.get('get_selected'))
            cmp_payslip_templates = request.user.employee_details.first().company.payslip_fields_templates.filter(q_filters)
            cmp_payslip_templates_data= PayslipTemplateFieldsSerializer(cmp_payslip_templates, many=True).data
            return Response(data=cmp_payslip_templates_data, status=status.HTTP_200_OK)
        except (ObjectDoesNotExist):
            return Response(data=[], status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
    def post(self, request):
        try:
            data = request.data
            paysliptemplate_data = PayslipTemplateFieldsSerializer(data=data)
            if paysliptemplate_data.is_valid():
                paysliptemplate_data.save()
                return Response(data=paysliptemplate_data.data, status=status.HTTP_201_CREATED)
            else:
                return Response(data=paysliptemplate_data.errors)
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
    def patch(self, request):
        try:
            data = request.data
            paysliptemplate_obj = request.user.employee_details.first().company.payslip_fields_templates.get(id=data.get('id'))
            paysliptemplate_data = PayslipTemplateFieldsSerializer(paysliptemplate_obj, data=data, partial=True)
            if paysliptemplate_data.is_valid():
                paysliptemplate_data.save()
                return Response(data=paysliptemplate_data.data, status=status.HTTP_207_MULTI_STATUS)
            else:
                return Response(data=paysliptemplate_data.errors)

        except (ObjectDoesNotExist):
            return Response(data=[], status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
    
    def delete(self, request):
        try:
            ids = request.data.get('ids')
            objs = PayslipTemplateFields.objects.filter(id__in=ids).delete()
            return Response({'msg':"payslip template fields deleted"},status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,)
            
class EpfEmployeesApi(AbstractAPIView):
    """
    this class is used to create read and update the employees for epf in a company
    """
    model = EPFEmployees

    def get(self, request):
        emp_qs = request.user.employee_details.first().company.employees.all()
        emps_data = emp_qs.annotate(is_selected = StringAgg(Case(
                                    When(epf_emps__emps__isnull=False, then = Value('selected')),
                                    default = Value('not_selected'),
                                    output_field=models.CharField()
                                    ), delimiter = ', ', distinct=True)).values('id', 'first_name', 'middle_name', 'last_name', 'work_details__employee_number', 'is_selected')
        return Response({"all_emps":emps_data})

    def put(self, request):
        company_id = request.data['company_id']
        emps = request.data.get('emps', [])
        instance, updated = self.model.objects.update_or_create(company_id = company_id)
        instance.emps.set(emps)
        return Response(f"updated employees {emps} for the company {company_id}")

class EmployeesHold(AbstractAPIView):
    """
    this class manages the employees hold
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        try:
            query_params = request.query_params
            hold_status = False 
            if 'status' in query_params:
                hold_status = eval(query_params.get('status')) #listing all the employees
            q_filters = ~Q(hold_employee__isnull = hold_status)    
            emps = Employee.objects.filter(q_filters). \
            annotate(
                emp_id = StringAgg('work_details__employee_number', delimiter=','),
                emp_name = StringAgg(Trim(Concat(F('first_name'),Value(" "),F('middle_name'),Value(" "),F('last_name'))), delimiter=', '),
                dept = StringAgg('work_details__department__name', delimiter=', '),
                disbursement_status = Case(
                    When(hold_employee__isnull=False, then=Value('Enabled')),
                        default=Value('Not Enabled'),
                        output_field=models.CharField()),
                disbursement_created_by = F('hold_employee__hold_created_by__user__username'),
                disbursement_created_at = F('hold_employee__hold_created_at'),
                disbursement_updated_by = F('hold_employee__hold_updated_by__user__username'),
                disbursement_updated_at = F('hold_employee__hold_updated_at'),
                    )
            return Response(emps.values('id', 'emp_id', 'emp_name', 'dept',
                                         'disbursement_status', 'disbursement_created_by', 'disbursement_created_at', 
                                         'disbursement_updated_by', 'disbursement_updated_at',
                                        #  'comments'
                                         ))
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,)
    
    def post(self, request, *args, **kwargs):
        #adding the employees to hold 
        try:
            emp_ids = request.data.get('emp_ids', [])
            emp_ids = list(Employee.objects.filter(id__in=emp_ids).values_list('id', flat=True))
            if len(emp_ids) == 0:
                return Response("No employees Are there in the db")
            request_employee = request.user.employee_details.first().id
            emps_lst = []
            for emp_id in emp_ids:
                emps_lst.append(EmployeePayrollOnHold(employee_id = emp_id, hold_created_by_id = request_employee, hold_created_at = timezone_now(), hold_updated_by_id = request_employee, hold_updated_at = timezone_now()))
            EmployeePayrollOnHold.objects.bulk_create(emps_lst)
            return Response(f"Employee ids updated for {emps_lst}")
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,)
    
    def patch(self, request):
        try:
            emp_ids = request.data.get('emp_ids', [])
            emp_hold_objs = EmployeePayrollOnHold.objects.filter(employee__id__in=emp_ids)
            if not emp_hold_objs.exists():
                return Response("No employees Are there in the db")
            emp_hold_objs.delete()
            return Response(f"removed the hold for these {str(list(emp_hold_objs.values_list('employee__user__username', flat=True)))} emp_ids")
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,)
        
class PayRollAddComment(AbstractAPIView):
    """
    this class is used to add or update the comment while run payroll
    """
    def post(self, request):
        payroll_id = request.data.get('payroll_id', None)
        comments = request.data.get('comments', "")
        if not payroll_id:
            return Response("payroll id need to send mandatory")
        payroll_obj = PayrollInformation.objects.filter(id=payroll_id)
        if not payroll_obj:
            return Response("given payroll id is not present in db")

        payroll_obj.update(comments = comments)
        user_name = payroll_obj.first().employee.user.username
        return Response(f'comment added for the payroll obj of {user_name}')

class PayrollOverviewApiV2(APIView):
    """
    this API is to retrive the PayrollOverviewApi info reports
    old:PayrollOverviewApi
    new:PayrollOverviewApiV2
    """

    model = PayrollInformation
    pagination_class = CustomPagePagination
    def get(self, request):
        try:        
            params = request.query_params
            company = request.user.employee_details.first().company
            q_filters = db_models.Q(employee__company=company, is_processed=True)

            if "dept_id" in params:
                q_filters &= db_models.Q(employee__work_details__department__id = request.query_params.get('dept_id'))

            if "emp_id" in params:
                q_filters &= db_models.Q(employee__id = request.query_params.get('emp_id'))

            if "month_year" in params:
                q_filters &= db_models.Q(month_year = request.query_params.get('month_year'))

            payroll_qs = self.model.objects.filter(q_filters).annotate(
                Month = F('month_year'),
                Employee_Name = StringAgg(Trim(F('employee__user__username')), delimiter=', ', distinct=True),
                Organisation_Name = StringAgg('employee__company__company_name', delimiter=', ', distinct=True),
                Mode_of_payment = F('mode_of_payment'),
                Bank_Name = F('bank_name'),
                Bank_Account_Number = F('account_number'),
                Bank_IFSC_Code = StringAgg('employee__salary_details__ifsc_code', delimiter=', ', distinct=True),
                Employee_Identification_Number = StringAgg('employee__work_details__employee_number', delimiter=', ', distinct=True),
                Employee_Income_Tax_PAN = StringAgg('employee__employee_document_ids__document_number',delimiter=', ', filter =db_models.Q(employee__employee_document_ids__document_type__document_type = DocumentsTypes.PAN_CARD, employee__employee_document_ids__is_deleted=False), distinct = True),
                Employee_EPF_Number = StringAgg('employee__emp_compliance_detail__pf_num', delimiter=', ', distinct=True),
                Employee_EPF_UAN = StringAgg('employee__emp_compliance_detail__uan_num', delimiter=', ', distinct=True),
                Employee_ESI_Number = StringAgg(
                    Case(
                        When(Q(employee__emp_compliance_detail__esi_num__in=[None, 'na', '', 'null', 'None'])|Q(employee__emp_compliance_detail__esi_num__isnull=True),
                        then=Value('NA')),
                        default=F('employee__emp_compliance_detail__esi_num'),
                        output_field=db_models.CharField()
                    ),
                    delimiter=', ', distinct=True),
                Employee_Designation = StringAgg('employee__work_details__designation__name', delimiter=', ', distinct=True),
                Department = StringAgg('employee__work_details__department__name', delimiter=', ', distinct=True),
                Date_of_joining = StringAgg(Cast('employee__date_of_join', models.CharField()), delimiter=', ', distinct=True),
                Date_of_Leaving = Case(
                                        When(
                                            Q(employee__resignation_info__last_working_day__isnull=False),
                                            then=F('employee__resignation_info__last_working_day')),#need to as str
                                            default = None, #need to change as NA
                                            output_field = db_models.DateField() #need to be as char field
                                        ),

                Total_Month_Days = F('month_days'),
                Employee_Working_Days = F('working_days'),
                Days_Present = F('days_present'),
                Leave_with_Pay = F('leaves'),
                Holidays = F('holidays'),
                Weekly_Offs = F('weekly_offs'),
                Loss_of_Pay = F('lop'),
                Total_Paid_Days = F('paid_days'),
                Annual_CTC = F('yearly_ctc'),
                Monthly_CTC = F('monthly_ctc'),
                # Gross_Salary_per_month = F('monthly_gross'), # adding in df
                Basic_Salary = F('s_basic'),
                House_Rent_Allowance = F('s_hra'),
                Conveyance_Allowance = F('s_conv'),
                Special_Allowance = F('s_special_allow'),
                Earned_Gross_Salary = F('earned_gross'),
                Earned_Basic_Salary = F('e_basic'),
                Earned_HRA = F('e_hra'),
                Earned_Conveyance_Allowance = F('e_conv'),
                Earned_Special_Allowance = F('e_special_allow'),
                Arrears = F('arrears'),
                Arrears_Basic_Salary = F('a_basic'),
                Arrears_Others = F('a_others'),
                Incentives = F('monthly_incentive'),
                Other_Additions_If_any = F('other_additions'),
                Net_Earned_Salary = F('net_salary'),
                Basic_Salary_for_EPF =  F('pf_basic'),
                EPF_Employee_Contribution = F('employee_pf'),
                Compensation_for_ESI = F('compensation_for_esi'),
                ESI_Employee_Contribution = F('employee_esi'),
                Profession_Tax = F('profession_tax'),
                TDS = F('monthly_tds'),
                Salary_Advance_Deduction = F('advance_deduction'),
                Staff_Loan_Deduction = F('staff_loan_deduction'),
                Other_Deductions = F('other_deduction'),
                Total_Deductions = F('total_deduction'),
                Net_Salary_Payable = F('net_pay'),
                EPF_Employer_Contribution = F('employer_pf'),
                ESI_Employer_Contribution = F('employer_esi'),
                Current_Month_CTC = F('current_month_ctc'),
                Disbursement_Status = F('is_on_hold'), # need name convection
                Comments = F('comments'),
            ).order_by('-month_year').values()
            
            df = pd.DataFrame(payroll_qs)
            df['Gross_Salary_per_month'] = df['Annual_CTC'].apply(ctc_to_gross_per_year)
            df['Gross_Salary_per_month'] = (df['Gross_Salary_per_month'] / 12).round(0)
            
            data = df.to_dict(orient='records')
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(data, request)
            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id = company.id)}, msg= "Successfully fetched payroll overview data"
                ),
            status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
        
class IciciBankReport(APIView):
    """
    this class is used to get/download the bank report
    #logic disbusement status enabled (true) must not be included
    """

    model = PayrollInformation
    pagination_class = CustomPagePagination
    
    def post(self, request):
        try:
            request_data = request.data
            company = request.user.employee_details.first().company
            q_filters = db_models.Q(employee__company=company, is_processed=True, is_on_hold=False)
            if 'emp_ids' in request_data and request_data.get('emp_ids'):
                q_filters &= (Q(employee_id__in = request_data.get('emp_ids')))
            if 'dept_ids' in request_data and request_data.get('dept_ids'):
                q_filters &= (Q(employee__work_details__department__id = request_data.get('dept_ids')))
            if 'month_years' in request_data and request_data.get('month_years'):
                q_filters &= (Q(month_year__in = request_data.get('month_years')))

            payroll_req_qs = PayrollInformation.objects.filter(q_filters).annotate\
                                    (
                report_values = db_models.expressions.Func(
                    Value('Debit_Ac_No'), StringAgg('employee__company__bankdetails__account_number', delimiter=', '),
                    Value('Beneficiary_Ac_No'), F('account_number'),
                    Value('Beneficiary_Name') , Case(When(employee__salary_details__account_holder_name__isnull=False, then=F('employee__salary_details__account_holder_name')), default = F('employee__user__username'), output_field=db_models.CharField()),
                    Value('Amt') , F('net_pay'),
                    Value('Pay_Mod') , Case(When(employee__salary_details__ifsc_code__icontains='icic', then=Value('I')), default = Value("N"), output_field = db_models.CharField()),
                    Value('IFSC'), Case(When(employee__salary_details__ifsc_code__icontains='icic', then=Value('')), default = StringAgg('employee__salary_details__ifsc_code', delimiter=', '), output_field = db_models.CharField()),
                    Value('Payable_Location_name'), Value(''),
                    Value('Print_Location') , Value(''),
                    Value('Bene_Mobile_no') , Value(''),
                    Value('Bene_email_id') , Value(''),
                    Value('Ben_add1'), Value(''),
                    Value('Ben_add2'), Value(''),
                    Value('Ben_add3') , Value(''),
                    Value('Ben_add4'), Value(''),
                    Value('Add_details_1'), Value(''),
                    Value('Add_details_2'), Value(''),
                    Value('Add_details_3'), Value(''),
                    Value('Add_details_4'), Value(''),
                    Value('Add_details_5'), Value(''),
                    Value('Remarks'), Value('Salaries'),
                    Value('Dummy'), Value(''),
                    Value('IFSC_Valiation'), Value(''),

                    function='jsonb_build_object',
                    output_field=db_models.JSONField()
                                                         )
                                    ).order_by('-month_year')

            payroll_req_qs_data = IciciBankReportSerializer(payroll_req_qs, many=True).data

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(payroll_req_qs_data, request)
            return Response(
                success_response(
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id = company.id)}, msg= "Successfully fetched payroll icici bank report data"
                ),
            status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
class EsiComplianceApiV2(APIView):
    model = PayrollInformation
    pagination_class = CustomPagePagination

    def get(self, request):
        try:    
            params = request.query_params

            company_obj = request.user.employee_details.first().company

            q_filters = db_models.Q(employee__company = company_obj, is_processed=True)
            
            if "dept_ids" in params:
                q_filters &= db_models.Q(employee__work_details__department__id__in = params.get('dept_ids').split(','))

            if "emp_ids" in params:
                q_filters &= db_models.Q(employee__id__in = params.get('emp_ids').split(','))

            if not ("month_year" in params):
                return Response('month_year is mandate to send in params')
            
            month_year = params.get('month_year')
            q_filters &= db_models.Q(month_year = month_year)
            
            previous_start_date = get_paycyclestart_and_paycycle_end(month_year)['payroll_start_date'] - relativedelta(months=1)
            previous_end_date = get_paycyclestart_and_paycycle_end(month_year)['payroll_end_date'] - relativedelta(months=1)
                        
            paycycle_start_date = get_paycyclestart_and_paycycle_end(month_year)['payroll_start_date']

            paycycle_end_date = get_paycyclestart_and_paycycle_end(month_year)['payroll_end_date']

            days_in_paycle = paycycle_end_date - paycycle_start_date 
            
            days_in_paycle = (days_in_paycle + datetime.timedelta(days=1)).days

            month_year = parser.parse(month_year).date()
            _, last_day_of_month = monthrange(month_year.year, month_year.month)
            
            emp_qs = Employee.objects.filter(resignation_info__last_working_day__gte = previous_start_date, resignation_info__last_working_day__lte = previous_end_date).exclude(Q(emp_compliance_detail__esi_num__in=[None, 'na', '', 'null', 'None'])|Q(emp_compliance_detail__esi_num__isnull=True))

            emp_qs = emp_qs.annotate(ip_number=StringAgg(
                    Case(
                        When(Q(emp_compliance_detail__esi_num__in=[None, 'na', '', 'null', 'None'])|Q(emp_compliance_detail__esi_num__isnull=True),
                        then=Value('NA')),
                        default=F('emp_compliance_detail__esi_num'),
                        output_field=db_models.CharField()
                    ),
                    delimiter=', ', distinct=True), 
                                     ip_name = StringAgg(Concat(
                                                        F('first_name'),
                                                        Value(" "),
                                                        F('middle_name'),
                                                        Value(" "),
                                                        F('last_name'),
                                                    ), delimiter=','),
                                    wages_days = Value(0),
                                    wages_paid = Value(last_day_of_month),
                                    reason_code = StringAgg(F('emp_esi_resignation__esi_resignation_status'), delimiter=','),
                                    last_working_day = Case(
                                                        When(
                                                            Q(resignation_info__last_working_day__isnull=False),
                                                            then=F('resignation_info__last_working_day')),
                                                            default = None,
                                                            output_field = db_models.DateField()
                                                        ), 
                                    ).values('ip_number', 'ip_name', 'wages_days', 'wages_paid', 'reason_code', 'last_working_day')
            
            emp_qs = list(emp_qs)

            esi_qs = list(self.model.objects.filter(q_filters).exclude(Q(employee__emp_compliance_detail__esi_num__in=[None, 'na', '', 'null', 'None'])|Q(employee__emp_compliance_detail__esi_num__isnull=True)).annotate(
                ip_number = StringAgg(
                    Case(
                        When(Q(employee__emp_compliance_detail__esi_num__in=[None, 'na', '', 'null', 'None'])|Q(employee__emp_compliance_detail__esi_num__isnull=True),
                        then=Value('NA')),
                        default=F('employee__emp_compliance_detail__esi_num'),
                        output_field=db_models.CharField()
                    ),
                    delimiter=', ', distinct=True),                
                ip_name = StringAgg(Concat(
                        F('employee__first_name'),
                        Value(" "),
                        F('employee__middle_name'),
                        Value(" "),
                        F('employee__last_name'),
                    ), delimiter=','),
                wages_days = Case(
                    When(paid_days=days_in_paycle, then=Value(last_day_of_month)),
                    default=F('paid_days'),
                    output_field=models.IntegerField(),
                ),
                wages_paid = F('payable_gross'),
                reason_code = Case(
                    When(payable_gross=0, then=Value('1')),
                    default=Value('0'),
                    output_field=models.CharField(),
                ),
                last_working_day = Value('')
                ).values('ip_number', 'ip_name', 'wages_days', 'wages_paid', 'reason_code', 'last_working_day'))
            
            # print(esi_qs)

            emp_qs.extend(esi_qs)
            

            # if ("download" in params) and (params['download']=="true"):

            #     df = pd.DataFrame(esi_qs) 
            #     # print(df)                

            #     if esi_qs:
            #         df['esi_num'] = df['esi_num'].astype(str) 
            #         df['paid_days'] = df['paid_days'].apply(lambda x: math.ceil(x))                                            

            #         df.rename(columns = {'user_name':'IP Name','payable_gross':'Total Monthly Wages','paid_days':'No of Days for which wages paid/payable during the month','esi_num':'IP Number'}, inplace = True)
                
            #         df["Reason Code for Zero workings days(numeric only; provide 0 for all other reasons- Click on the link for reference)"] = 0
            #         df["Last Working Day( Format DD/MM/YYYY  or DD-MM-YYYY)"] = ''

            #         BASE_COLUMNS = ['IP Number','IP Name','No of Days for which wages paid/payable during the month','Total Monthly Wages','Reason Code for Zero workings days(numeric only; provide 0 for all other reasons- Click on the link for reference)','Last Working Day( Format DD/MM/YYYY  or DD-MM-YYYY)']
                    
            #         df = df[BASE_COLUMNS]      

            #         num_cols = ['No of Days for which wages paid/payable during the month','Total Monthly Wages','Reason Code for Zero workings days(numeric only; provide 0 for all other reasons- Click on the link for reference)']

            #         df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce', axis=1)          

            #     file_name = "esi_compliance_report.xlsx"
            #     return excel_converter(df,file_name)
                    

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(emp_qs, request)

            return Response(
                success_response(
                    # result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(cmp_id = request.query_params.get('company_id'))}, msg= "Successfully fetched esi data"
                    result={"paginated_data":paginator.get_paginated_response(page),"filters_data":filters_data_func(company_obj.id)}, msg= "Successfully fetched esi data"

                ),
            status=status.HTTP_200_OK
            )    
        
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )

class EsiResignationChoices(AbstractAPIView):
    """
    this class is used to get the esi resignation statuses for the frontend
    """
    def get(self, request):
        try:
            statuses = EsiResignationDetails.esi_resignation_statuses
            return Response(statuses)
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )


class EmployeeEsiResignation(AbstractAPIView):
    """
    this class is used to set the esi resignation status
    """
    def get(self, request):
        try:
            emp_obj = Employee.objects.get(id = request.query_params.get('emp_id'))
            if hasattr(emp_obj, 'emp_esi_resignation'):
                status_keys = dict(EsiResignationDetails.esi_resignation_statuses)
                emp_resig_obj = emp_obj.emp_esi_resignation
                key_list = None
                if emp_resig_obj.esi_resignation_status != None:
                    key_list = [key for key, val in status_keys.items() if val == emp_resig_obj.esi_resignation_status][0]
                emp_resig_obj.esi_resignation_status = key_list
                data = EsiResignationSerializer(emp_resig_obj).data
                return Response(data)
            else:
                return Response([])

        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
    
    def post(self, request):
        try:
            emp_id = request.query_params.get('emp_id')
            cause = request.query_params.get('cause', None)
            if cause == 'null':
                cause = None
            defaults = {'esi_resignation_status' : cause}
            emp_resig_obj, created = EsiResignationDetails.objects.update_or_create(employee_id = emp_id, defaults=defaults)
            return Response({"message": f"succesfully {created}", 'emp_resig_obj':str(emp_resig_obj.employee.user.username)})
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )
    
    # def patch(self, request):
    #     try:
    #         emp_id = request.query_params.get('emp_id')
    #         cause = request.query_params.get('cause', None)
    #         if cause == 'null':
    #             cause = None
    #         emp_resig_obj = EsiResignationDetails.objects.get(employee_id = emp_id)
    #         emp_resig_obj.esi_resignation_status = cause
    #         emp_resig_obj.save()
    #         return Response({"message":"succesfully updated", "emp_resig_obj":str(emp_resig_obj.employee.user.username)})

    #     except Exception as e:
    #         return Response(
    #             error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
    #             status=status.HTTP_400_BAD_REQUEST,
    #         )
    # def delete(self, request):
    #     try:
    #         emp_id = request.query_params.get('emp_id')
    #         EsiResignationDetails.objects.get(employee_id = emp_id).delete()
    #         return Response("sucessfully deleted for the employee esi resignation")
    #     except Exception as e:
    #         return Response(
    #             error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
    #             status=status.HTTP_400_BAD_REQUEST,
    #         )
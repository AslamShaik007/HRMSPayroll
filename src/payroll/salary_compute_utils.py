import django
django.setup()
from calendar import monthrange
from dateutil.relativedelta import relativedelta

from directory.models import Employee, EmployeeDocuments, EmployeeResignationDetails, EmployeeSalaryDetails
from investment_declaration.models import InvestmentDeclaration, FormChoices, DeclarationForms
from .utils import calculate_tax_for_regime, ctc_to_gross_per_year, get_current_financial_year_start_and_end, get_leaves_lop_for_employee, get_pay_cycle_start_and_end_date, get_pay_cycle_start_and_end_day, get_projected_ctc_for_fixed_pay, get_weekend_count

from HRMSApp.models import CompanyDetails

from django.db.models import Sum, Q
import math, datetime, logging
from .serializers import EmployeeBulkImportSerializer
from .models import ( EmployeeComplianceNumbers, HealthEducationCess, PaySalaryComponents, EmployeePayrollOnHold,
                     PayrollInformation, Regime, Reimbursement)
from pss_calendar.models import Holidays
# from concurrent.futures import ProcessPoolExecutor

logger = logging.getLogger("django")


def get_lop_leaves_det(empId, month_year):
      

    #jan-2024 - 01-2024
    # leaves / lop data month = 12-2023
    if int(datetime.datetime.strptime("01-"+month_year, '%d-%b-%Y').strftime('%m')) == 1:
        
        context = get_leaves_lop_for_employee(
                        int(datetime.datetime.strptime("01-"+month_year, '%d-%b-%Y').strftime('%Y'))-1,
                        int(datetime.datetime.strptime("01-"+month_year, '%d-%b-%Y').strftime('%m'))-1,
                        empId
                        )
        return context
        
    context = get_leaves_lop_for_employee(
                        int(datetime.datetime.strptime("01-"+month_year, '%d-%b-%Y').strftime('%Y')),
                        int(datetime.datetime.strptime("01-"+month_year, '%d-%b-%Y').strftime('%m'))-1,
                        empId
                        )
    return context
    



def parallel_task(ctx_data,emp_obj):
         
    det = {}

    det["month"] = ctx_data['month_of_payroll_running'] 
    ctx_data['month_days'] = (ctx_data['pay_cycle_end_date'] - ctx_data['pay_cycle_start_date']).days + 1   
    # ctx_data['month_days'] = 29  
    det["month_days"] = ctx_data['month_days']
    det["org_name"] = ctx_data['company_name']

    det['month_year'] = datetime.datetime.strptime("01-"+ctx_data['month_year'], '%d-%b-%Y')
    payroll_obj, created = PayrollInformation.objects.get_or_create(employee=emp_obj,month_year=datetime.datetime.strptime("01-"+ctx_data['month_year'], '%d-%b-%Y')) 
    if created:
        det['comments'] = ""
    else:
        det['comments']=payroll_obj.comments

    det['id'] = payroll_obj.id
    payroll_obj.month_days = ctx_data['month_days']     

    # if emp_obj.payroll_status is None:
    det['is_on_hold'] = False
    if EmployeePayrollOnHold.objects.filter(employee_id=emp_obj.id):
        det['is_on_hold'] = True
        payroll_obj.is_on_hold=True
    det['other_additions'] = 0
    payroll_obj.other_additions = det['other_additions']

    # If condtion will only apply, when user changes the TDS to be cut manually - which comes when TDS more than 50% of salary and less than total salary
    # is_tds_percent_deducted = True
    # txp = tax percent , of how much tds should be deducted 
    if ctx_data['txp'] and ctx_data['payroll_id'] and (int(ctx_data['payroll_id']) == payroll_obj.id):
        tds_percent_value = int(ctx_data['txp'])
        is_tds_percent_deducted = True
    else: # by default both are 0/Null
        tds_percent_value = payroll_obj.consider_tds_percent
        is_tds_percent_deducted = payroll_obj.is_tds_percent_deducted

    payroll_obj.consider_tds_percent = tds_percent_value
    
    det["is_tds_percent_deducted"] = payroll_obj.is_tds_percent_deducted = is_tds_percent_deducted        
    
    det["emp_code"] = ""

    if emp_obj.work_details.employee_number:
        det["emp_code"] = emp_obj.work_details.employee_number
        
    payroll_obj.department = det["department"] = emp_obj.work_details.department.name
    
    if emp_obj.work_details.designation:
        payroll_obj.designation = det["designation"] = emp_obj.work_details.designation.name            

    
    det["emp_name"] = (
        emp_obj.first_name + " "
        + (emp_obj.middle_name or "") + " "
        + (emp_obj.last_name or "")
    )
            
    # Fetching Leaves and LOP of the particular employee for the particlar month        
    emp_id = emp_obj.id
    leave_lop_det = get_lop_leaves_det(emp_id, ctx_data['month_year'])        

    payroll_obj.leaves = det["leaves"] = leave_lop_det.get("totalLeavesCount",0)
    if (hasattr(emp_obj, 'resignation_info')) and (hasattr(emp_obj.resignation_info, 'last_working_day')) and (emp_obj.resignation_info.last_working_day is not None):
        payroll_obj.leaves = det["leaves"] = leave_lop_det.get("orginal_leaves_count")

    payroll_obj.lop = det["lop"] = leave_lop_det.get("totalLopCount") if leave_lop_det.get("totalLopCount") else 0

    leaves_to_encash = leave_lop_det.get("leavesEncashed",0)

    det["doj"] = emp_obj.date_of_join
    det["doe"]="NA"
    if (hasattr(emp_obj, 'resignation_info')) and (hasattr(emp_obj.resignation_info, 'last_working_day')) and (emp_obj.resignation_info.last_working_day is not None):
        det["doe"] = emp_obj.resignation_info.last_working_day
    # Employee Joining Year and month
    
    try:
        emprd_obj = EmployeeResignationDetails.objects.get(employee=emp_obj)
        resignation_date = emprd_obj.resignation_date
        last_working_day = emprd_obj.last_working_day
        resignation_status = emprd_obj.resignation_status
        notice_period = emprd_obj.notice_period
        termination_date = emprd_obj.termination_date                        
    except EmployeeResignationDetails.DoesNotExist:
        resignation_date = last_working_day = resignation_status = notice_period = termination_date = None

    if last_working_day:
        last_working_date = last_working_day
    elif termination_date:
        last_working_date = termination_date
    elif resignation_date:
        last_working_date = termination_date + datetime.timedelta(days=(notice_period or 0))
    else:
        last_working_date = False
        
    emp_sal_det = EmployeeSalaryDetails.objects.filter(
        employee=emp_obj.id
    ).values('ifsc_code','fund_transfer_type','special_deductions','advance_deductions','monthly_incentive','arrears','bank_name','account_number','ctc','fixed_salary','variable_pay')[0]

    det["ifsc_code"] = emp_sal_det['ifsc_code']
    # det["fund_transfer_type"] = emp_sal_det['fund_transfer_type']
    
    det["fund_transfer_type"] = "Bank Transfer" #need to implement the dropdown in hrms.

    try:
        empd_obj = EmployeeDocuments.objects.filter(employee=emp_obj.id,document_type__document_type=10)
        if empd_obj.exists():
            empd_obj = empd_obj[0]
            pan_number = empd_obj.document_number
        else:
            pan_number = ""  
    except:
        pan_number = ""  

    det["special_deductions"] = emp_sal_det['special_deductions']
    det["advance_deductions"] = emp_sal_det['advance_deductions']
    det["monthly_incentive"] = emp_sal_det['monthly_incentive']
    det["arrears"] = emp_sal_det['arrears']
    det["pan_number"] = pan_number

    try:
        emp_comp_no = EmployeeComplianceNumbers.objects.filter(
            employee=emp_obj.id
        ).values('pf_num','uan_num','esi_num')[0]
        
        na_values = ["", "null", "None", None]

        if emp_comp_no['pf_num'] in na_values:
            emp_comp_no['pf_num'] = "NA"

        if emp_comp_no['esi_num'] in na_values:
            emp_comp_no['esi_num'] = "NA"
        
        if emp_comp_no['uan_num'] in na_values:
            emp_comp_no['uan_num'] = "NA"
            

        det["pf_num"] = emp_comp_no['pf_num']
        det["uan_num"] = emp_comp_no['uan_num']
        det["esi_num"] = emp_comp_no['esi_num']

    except:
        det["pf_num"] = ""
        det["uan_num"] = ""
        det["esi_num"] = ""


    payroll_obj.special_deductions = round(det["special_deductions"])
    payroll_obj.advance_deduction = round(det["advance_deductions"])
    payroll_obj.monthly_incentive = round(det["monthly_incentive"])        
    payroll_obj.arrears = round(det["arrears"])

    # A_Basic = Arrears/2 if Arrears > 0 else 0
    payroll_obj.a_basic = det['a_basic'] =  round(det["arrears"]/2) if det['arrears'] > 0 else 0
    
    # A_Others = Arrears - A_Basic

    det['a_others'] = det["arrears"] - det["a_basic"]
    payroll_obj.a_others = det['a_others']


    payroll_obj.bank_name = det["bank_name"] = emp_sal_det['bank_name']
    payroll_obj.account_number = det["account_number"] = emp_sal_det['account_number']

    
    
    payroll_obj.yearly_ctc = det["ctc"] = emp_sal_det['ctc']
    payroll_obj.monthly_ctc = round(det["ctc"]/12)
    # print(emp_obj, "Hi")
    try:
        payroll_obj.fixed_salary = det["fixed_salary"] = float(emp_sal_det.get('fixed_salary', 0)) if emp_sal_det['fixed_salary'] is not None else 0
        payroll_obj.variable_pay = det["variable_pay"] = float(emp_sal_det.get('variable_pay', 0)) if emp_sal_det['variable_pay'] is not None else 0
    except:
        payroll_obj.fixed_salary = det["fixed_salary"] =  0
        payroll_obj.variable_pay = det["variable_pay"] =  0
        
    # Check for fixed pay if user is getting
    if det["fixed_salary"] > 0:
        payroll_obj.monthly_ctc = det["fixed_salary"] + det["variable_pay"]


        payroll_obj_filter = PayrollInformation.objects.filter(
                                            employee=emp_obj,
                                            month_year__month__gte=4,
                                            month_year__year=ctx_data['financial_year_start'],
                                            month_year__lt=datetime.datetime.strptime("01-"+ctx_data['month_year'], '%d-%b-%Y'),
                                            is_processed=True
                                            )
        prev_month_paid_total = 0
        if payroll_obj_filter.count() > 0:
            payroll_obj_dict = payroll_obj_filter.aggregate(                                                
                                                prev_month_paid_total = Sum("monthly_ctc")
                                            )
            prev_month_paid_total = payroll_obj_dict['prev_month_paid_total']
        # months_left_for_current_financial_yr = (ctx_data['financial_year_end'] - ctx_data['cur_year']) * 12 + (4 - ctx_data['month_of_payroll_running'])
        
        payroll_obj.yearly_ctc = det["ctc"] = get_projected_ctc_for_fixed_pay(det["fixed_salary"],det["variable_pay"],prev_month_paid_total,payroll_obj_filter.count())
    
        
        # payroll_obj.monthly_ctc = (emp_sal_det.fixed_salary + emp_sal_det.variable_pay)
    

    det['monthly_ctc'] = payroll_obj.monthly_ctc


    # Calcuating Yearly Gross Salary
    det['gross_year'] = ctc_to_gross_per_year(det["ctc"],ctx_data['employer_esi_pct'])
    det['gross_monthly'] = round(ctc_to_gross_per_year(emp_obj.salary_details.ctc)/12)
    det['ctc_yearly']=emp_obj.salary_details.ctc
    
    # Calcuating monthly Gross Salary
    actual_gross_salary = det["gross_salary"] = round(det['gross_year'] / 12)

    # Per Day Salary
    per_day_salary = float(det["gross_salary"] / det["month_days"])

    deduction_for_joining_month = 0                                  

    # Checking - if Last working date month and year is same as the month for which we are running payroll
    # then we need to calculate, 
    # how many days the employee has worked based on PaySchedule start date and End date                          
    # print(pay_cycle_start_date, det["doj"] , pay_cycle_end_date) 
    if last_working_date and (ctx_data['pay_cycle_start_date'] <= last_working_date <= ctx_data['pay_cycle_end_date']):

        # print("LWD falls between Payroll start and end dates.")
                    
        # Calculate the difference between two dates
        date_difference = last_working_date - ctx_data['pay_cycle_start_date']
        # ab = ctx_data['pay_cycle_start_date']+datetime.timedelta(days=2)
        # date_difference = last_working_date - ab 
        
        days_worked = date_difference.days + 1

        payroll_obj.working_days = det["working_days"] = days_worked

        payroll_obj.paid_days = det["paid_days"] = days_worked - det["lop"]
    
        deduction_for_joining_month = round(per_day_salary * (det["month_days"] - days_worked))


    # Checking - if joining month and year is same as the month for which we are running payroll
    # then we need to calculate, 
    # how many days the employee has worked based on PaySchedule start date and End date                          
    # print(pay_cycle_start_date, det["doj"] , pay_cycle_end_date)        
    elif ctx_data['pay_cycle_start_date'] <= det["doj"] <= ctx_data['pay_cycle_end_date']:

        # print("Joining date falls between Payroll start and end dates.")
                    
        # Calculate the difference between two dates

        rj = ctx_data['pay_cycle_end_date']
        # rj = ctx_data['pay_cycle_end_date']-datetime.timedelta(days=2)
        # rj = ctx_data['pay_cycle_end_date']-datetime.timedelta(days=0)
        
        date_difference = rj - emp_obj.date_of_join
        
        days_worked = date_difference.days + 1

        payroll_obj.working_days = det["working_days"] = days_worked

        payroll_obj.paid_days = det["paid_days"] = days_worked - det["lop"]
    
        deduction_for_joining_month = round(per_day_salary * (det["month_days"] - days_worked))

    else:
        #Existing employees
        payroll_obj.working_days = det["working_days"] = det["month_days"]
        payroll_obj.paid_days = det["paid_days"] = det["working_days"] - det["lop"]
    
    
    payroll_obj.lop_deduction = det["lop_deduction"] = round(per_day_salary * float(det["lop"]))
                        
    # if deduction_for_joining_month >  det["gross_salary"]:            
    #     payroll_obj.s_gross = det["gross_salary"] = deduction_for_joining_month - round(det["gross_salary"])            
    # else:            
    payroll_obj.s_gross = det["gross_salary"] = round(det["gross_salary"]) - deduction_for_joining_month            

    regime_type = 20
    regime_name = "new"
    # print(ctx_data['financial_year_start'],ctx_data['financial_year_end'])
    idc_obj, created = InvestmentDeclaration.objects.get_or_create(
        employee=emp_obj,                                                                                                                        
        start_year=ctx_data['financial_year_start'],
        end_year=ctx_data['financial_year_end'],
        defaults={'regime_type': regime_type}
    )          

    idc_obj.income_from_previous_employer = emp_obj.salary_details.previous_income
    idc_obj.tds_from_previous_employer = emp_obj.salary_details.previous_tds
    idc_obj.admin_resubmit_status = InvestmentDeclaration.APPROVE
    idc_obj.save()
    if not created:                
        regime_type = idc_obj.regime_type
        regime_name = "old" if idc_obj.regime_type == 10 else "new"

    regime_obj = Regime.objects.get(regime_name=regime_name)
    
    each_regime = {
        int(key): value for key, value in regime_obj.salary_range_tax.items()
    }
    
    less_saving = 0

    if regime_name == "new":
        det['after_saving_salary'] = float(det["gross_year"]) - float(50000)        
        less_saving = 50000
        idc_obj.approved_amount = 50000
        default_comments = {"approved_amount" : 50000, "comments_from_employee":'default new regime 50000 employee', "comments_from_employer":"default new regime 50000 employer"}
        DeclarationForms.objects.get_or_create(parentform_type_id = ctx_data['standard_deduction_obj'], declaration = idc_obj, defaults=default_comments) 
        if det['after_saving_salary'] <= 700000:
            det['after_saving_salary'] = 0                  
    else:
        less_saving = float(idc_obj.approved_amount)
        det['after_saving_salary'] = float(det["gross_year"]) - less_saving
        

    payroll_obj.earned_gross = det["earned_gross"] = round((
        float(det["gross_salary"])
        - float(det["lop_deduction"])
        - float(det["special_deductions"])
        - float(det["advance_deductions"])            
    ))
    

    basic_psc_obj = PaySalaryComponents.objects.get(company__id=ctx_data['cmp_id'],component_name="Basic")
    hra_psc_obj = PaySalaryComponents.objects.get(company__id=ctx_data['cmp_id'],component_name="HRA")

    payroll_obj.s_basic = det["s_basic"] = round((det["gross_salary"] * (basic_psc_obj.pct_of_basic/100) ))
    payroll_obj.s_hra = det["s_hra"] = round((float(det["s_basic"]) * (hra_psc_obj.pct_of_basic/100)))

    if det["gross_salary"] > 10000:
        det["s_conv"] = 1600
    elif det["gross_salary"] > 5000:
        det["s_conv"] = 800
    else:
        det["s_conv"] = 0

    payroll_obj.s_conv = det["s_conv"]
    
    det["s_special_allow"] = round(
                                    (det["gross_salary"] - det["s_basic"] - det["s_hra"] - det["s_conv"])
                                )
    payroll_obj.s_special_allow = round(det["s_special_allow"])
    

    payroll_obj.e_basic = det["e_basic"] = round((det["earned_gross"] * (basic_psc_obj.pct_of_basic/100)))

    payroll_obj.e_hra = det["e_hra"] = round((det["e_basic"] * (hra_psc_obj.pct_of_basic/100)))
    
    if det["earned_gross"] > 10000:
        det["e_conv"] = 1600
    elif det["earned_gross"] > 5000:
        det["e_conv"] = 800
    else:
        det["e_conv"] = 0

    payroll_obj.e_conv = det["e_conv"]
    payroll_obj.e_special_allow = det["e_special_allow"] = round(
                                                    (det["earned_gross"] - det["e_basic"] - det["e_hra"] - det["e_conv"])
                                                )
    payroll_obj.payable_gross =  round(det["earned_gross"])
    payroll_obj.t_basic = det["t_basic"] =   det["e_basic"] + det["a_basic"]


    det["net_salary"] = (
        float(det["monthly_incentive"])
        + float(det["arrears"])
        + float(det["earned_gross"])
    )     

    det['total_earnings'] = round(det["gross_salary"] + float(det["monthly_incentive"]) + float(det["arrears"]))
    
    payroll_obj.total_earnings = det['total_earnings']

    payroll_obj.net_salary = round(det["net_salary"])


    if det["t_basic"] > 15000:
        det["pf_basic"] = 15000
    else:
        det["pf_basic"] = det["t_basic"]


    payroll_obj.pf_basic = det["pf_basic"]

    payroll_obj.employee_pf = det["emp_pf"] = 1800 if float(det["pf_basic"]) * 0.12 > 1800 else round((float(det["pf_basic"]) * 0.12))     

    gender = (emp_obj.gender).lower()

    det['gender'] = gender

    tax_range_list = (ctx_data['tax_config'])[gender]['salary_ranges']

    for idx,range in enumerate(tax_range_list):
        range_split = range.split("-")
        if range_split[1] != 'x':                  
            if det["net_salary"] <= int(range_split[1]):                    
                det["pt"] = (ctx_data['tax_config'])[gender]['tax_value'][idx]
                break
        else:
            if det["net_salary"] > int(range_split[0]):
                det["pt"] = (ctx_data['tax_config'])[gender]['tax_value'][idx]
                break
                
    payroll_obj.profession_tax = round(det["pt"])

    payroll_obj.employer_pf = det["own_pf"] = 1800 if float(det["pf_basic"]) * 0.12 > 1800 else round((float(det["pf_basic"]) * 0.12))         

    # if det["gross_salary"] < 21000:
    if det['gross_monthly'] < 21000:
        det["own_esi"] = round(
            (float(det["earned_gross"]) * (ctx_data['employer_esi_pct'] / 100))
        )

        det["emp_esi"] = round(
            (
                float(det["earned_gross"]) * (ctx_data['employee_esi_pct'] / 100)
            ),                
        )
    else:
        det["own_esi"] = 0
        det["emp_esi"] = 0

    payroll_obj.employee_esi = det["emp_esi"]
    payroll_obj.employer_esi = det["own_esi"]

    # Net Earned(AQ) + EPF Employer(BC) + ESI Employer(BD)
    det["current_month_ctc"] = det["net_salary"] + det["own_pf"] + det["own_esi"]
    payroll_obj.current_month_ctc = det["current_month_ctc"]
    det["emp_ded"] = 0
    det["own_ded"] = 0

    tds_left = 0

    prof_tax_for_tds = 0 if regime_type == 20 else det["pt"]

    
    # gross salary is total salary - after tds
    det["salary_bef_tds"] = (
            float(det["monthly_incentive"])
            + float(det["arrears"])
            + float(det["earned_gross"])
        )

    # Calculation for Leave Encashment

    total_leave_taken_till_date = 0
    # try:

    total_leave_taken_till_date = leave_lop_det.get('totalLeavesTakenTillDate',0)
    # except:
    #     payroll_lop_obj = EmployeeLops.objects.filter(
    #         employee_id=emp_id            
    #     ).aggregate(total_leaves_count=Sum('total_leaves_count'))

    #     total_leave_taken_till_date = payroll_lop_obj['total_leaves_count']

    if not total_leave_taken_till_date:
        total_leave_taken_till_date = 0
    # laves_count - employee lop table total 
    
    basic_salary = det["s_basic"]
    da = 0
    no_of_days_for_lc = 30
    per_day_wage = (basic_salary + da)/no_of_days_for_lc        
    taxable_amount = 0
    exemption_amount = 0
    delta = relativedelta(ctx_data['pay_cycle_end_date'] , det["doj"])
    # print(delta)
    service_years = delta.months / 12    # + delta.months

    # print(service_years,ctx_data['pay_cycle_end_date'] , det["doj"])
    factor2 = 0
    # conditions to check
    if leaves_to_encash > 0:
        factor1 = 2500000
        factor2 = leaves_to_encash * per_day_wage
        factor3 = basic_salary*10

        factor4 = ((30*service_years)-total_leave_taken_till_date)*per_day_wage

        exemption_amount = min(factor1,factor2,factor3,factor4)    

        taxable_amount = factor2 - exemption_amount

    det['leaves_encash_total_amount'] = round(factor2) if factor2 else 0

    payroll_obj.leaves_encash_taxable_amount = det['leaves_encash_taxable_amount'] = round(taxable_amount)
    payroll_obj.leaves_encash_exemption_amount = det['leaves_encash_exemption_amount'] = round(exemption_amount)
    payroll_obj.leaves_to_encash = det['leaves_to_encash'] = round(leaves_to_encash)


    # calculation for OT
    overtime_days = 0
    # try:        
 
    overtime_days = leave_lop_det.get('overtimeCount',0)
    # except:        
    #     payroll_lop_obj = EmployeeOT.objects.filter(
    #         employee__id=emp_id,
    #         ot_month_year=datetime.datetime.strptime("01-"+ctx_data['month_year'], '%d-%b-%Y').strftime('%Y-%m-01')
    #     )
    #     if payroll_lop_obj.exists():
    #         overtime_days = payroll_lop_obj.total_ot_count         
          
    
        # pass
    
    # print(overtime_days)
    payroll_obj.overtime_days = det['overtime_days'] = overtime_days

    overtime_pay = per_day_salary*overtime_days    

    payroll_obj.overtime_pay = det['overtime_pay'] = round(overtime_pay)

    # ot_psc_obj = PaySalaryComponents.objects.get(company__id=ctx_data['cmp_id'],component_name="Overtime")

    # if ot_psc_obj.calculation_type == 2:
    #     payroll_obj.overtime = det["overtime"] = det["gross_salary"] * (ot_psc_obj.pct_of_basic/100) 
    # elif ot_psc_obj.calculation_type == 1:
    #     payroll_obj.overtime = det["overtime"] = round((det["gross_salary"] * ot_psc_obj.flat_amount ))
    # else:
    #     payroll_obj.overtime = det["overtime"] = 0        

    salary_before_tds = round(float(det["salary_bef_tds"]) - prof_tax_for_tds + taxable_amount + overtime_pay)
    if salary_before_tds < 0:
        salary_before_tds = 0
    payroll_obj.salary_before_tds = salary_before_tds
    # print("month of payroll runnning - ",ctx_data['month_of_payroll_running'] )

    if ctx_data['month_of_payroll_running'] == 4:
        det['salary_before_tds'] = salary_before_tds 
        tds_cal_salary = salary_before_tds + (actual_gross_salary*11-(float(prof_tax_for_tds*11))) - less_saving
        # print(tds_cal_salary)
        if regime_type == 20:
            if tds_cal_salary <=700000:
                tds_cal_salary = 0  
        else:
            if tds_cal_salary <500000:
                tds_cal_salary = 0  

        tds_calc = calculate_tax_for_regime(
            tds_cal_salary,
            each_regime,
            ctx_data['health_education_cess']
        )      
                        
        monthly_tds_calc = int(math.ceil((round(tds_calc["total_tax"] / 12)) / 10.0)) * 10

    else:
        months_left_for_current_financial_yr = (ctx_data['financial_year_end'] - ctx_data['cur_year']) * 12 + (4 - ctx_data['month_of_payroll_running'])

        # print("months_left_for_current_financial_yr - ",months_left_for_current_financial_yr)
        if months_left_for_current_financial_yr < 0:
            months_left_for_current_financial_yr = 12 + months_left_for_current_financial_yr
        # months_left_for_current_financial_yr = months_left_for_current_financial_yr - 1
        # print(datetime.datetime.strptime("01-04-"+str(financial_year_start), '%d-%m-%Y'))   

        payroll_obj_filter = PayrollInformation.objects.filter(
                                            employee=emp_obj,
                                            # month_year__month__gte=4,
                                            month_year__gte=datetime.datetime.strptime("01-Apr-"+str(ctx_data['financial_year_start']), '%d-%b-%Y'),
                                            # month_year__year__gte=ctx_data['financial_year_start'],
                                            month_year__lt=datetime.datetime.strptime("01-"+ctx_data['month_year'], '%d-%b-%Y')
                                            )

        if payroll_obj_filter.count() > 0:
            payroll_obj_dict = payroll_obj_filter.aggregate(
                                                total_prev_salary_before_tds = Sum("salary_before_tds"),
                                                total_prev_tds = Sum("monthly_tds"),
                                                total_tds_left = Sum("tds_left")
                                            )                                                               
            prev_salary_before_tds = payroll_obj_dict['total_prev_salary_before_tds'] or 0
            prev_tds = payroll_obj_dict['total_prev_tds'] or 0
            tds_left = payroll_obj_dict['total_tds_left'] or 0
            try:
                prev_salary_before_tds = prev_salary_before_tds + idc_obj.income_from_previous_employer
                prev_tds = prev_tds + idc_obj.tds_from_previous_employer
            except Exception as e:                
                pass
        else:            
            tds_left = 0            
            prev_tds = float(idc_obj.tds_from_previous_employer)
            prev_salary_before_tds = float(idc_obj.income_from_previous_employer)                                                        

       
        total_salary_before_tds = salary_before_tds + float(prev_salary_before_tds)       
        
        det['salary_before_tds'] = total_salary_before_tds 
        
        

        tds_cal_salary = total_salary_before_tds + (actual_gross_salary*(months_left_for_current_financial_yr-1))-(float(prof_tax_for_tds*(months_left_for_current_financial_yr-1))) - less_saving
        
        print("tds_cal_salary", tds_cal_salary)
        if regime_name == "new":
            if tds_cal_salary <=700000:
                tds_cal_salary = 0            
        else:
            if tds_cal_salary < 500000:
                tds_cal_salary = 0 
        
        # print(tds_cal_salary,
        #     each_regime,
        #     ctx_data['health_education_cess'])
        
        tds_calc = calculate_tax_for_regime(
            tds_cal_salary,
            each_regime,
            ctx_data['health_education_cess']
        )
        # print("tds_calc", tds_calc)
        # print(prev_tds, tds_left)
        monthly_tds_calc = (tds_calc["total_tax"] - float(prev_tds) + float(tds_left)) / months_left_for_current_financial_yr
        monthly_tds_calc = int(math.ceil((round(monthly_tds_calc)) / 10.0)) * 10
        
        tds_left = 0

    # print("monthly_tds_calc", monthly_tds_calc)
    if monthly_tds_calc < 0:
        monthly_tds_calc = 0

    # print("check line no 559")

    if ctx_data['month_of_payroll_running'] >= 4:            
        if monthly_tds_calc > salary_before_tds:
            tds_left = monthly_tds_calc - (0.15*salary_before_tds)                
            monthly_tds_calc = 0.15*salary_before_tds                    
            monthly_tds_calc = int(math.ceil((round(monthly_tds_calc)) / 10.0)) * 10

    tds_left = round(tds_left)
    payroll_obj.tds_left = det['tds_left'] = tds_left
        
    det["monthly_tds"] = monthly_tds_calc

    if is_tds_percent_deducted:
        payroll_obj.tds_left = det['tds_left'] = tds_left = monthly_tds_calc - round((float(det["net_salary"]) * (tds_percent_value/100)))
        monthly_tds_calc = round((float(det["net_salary"]) * (tds_percent_value/100)))
        monthly_tds_calc = int(math.ceil((round(monthly_tds_calc)) / 10.0)) * 10
        det["monthly_tds"] = monthly_tds_calc

    payroll_obj.is_tds_fifty_percent = False
    det["is_tds_fifty_percent"] = False

    
    if float(monthly_tds_calc) > float(salary_before_tds/2):
        payroll_obj.is_tds_fifty_percent = True
        det["is_tds_fifty_percent"] = True        


    det["total_deduction"] = (
        float(det["emp_pf"])
        + float(det["emp_esi"])
        + float(det["pt"])
        + float(det["monthly_tds"])
    )        

    payroll_obj.monthly_tds = round(det["monthly_tds"])
    

    payroll_obj.total_employee_contribution = det['total_employee_contribution'] =   round((float(det["emp_pf"]) + float(det["emp_esi"])))
            
    payroll_obj.edli_contribution = det["edli_contribution"] = round((0.0367 * float(det["pf_basic"])))
    payroll_obj.eps_contribution = det["eps_contribution"] = round((0.0833 * float(det["pf_basic"])))

    payroll_obj.total_epf_contribution = det["eps_contribution"] + det["edli_contribution"] + det["own_pf"]
    payroll_obj.total_esi_contribution = det["own_esi"] + det["emp_esi"]
            
    payroll_obj.total_employer_contribution = det['total_employer_contribution'] = round((float(det["own_esi"]) + float(det["own_pf"])))

    payroll_obj.total_deduction = round(det["total_deduction"])        


    # det["net_pay"] = round((det['overtime_pay'] + det['leaves_encash_total_amount']+float(det["net_salary"]) - det["total_deduction"] + float(det["lop_deduction"]) + float(det["special_deductions"]) + float(det["advance_deductions"])))
    
    det["net_pay"] = round((det['overtime_pay'] + det['leaves_encash_total_amount']+float(det["net_salary"]) - det["total_deduction"] + float(det["special_deductions"]) + float(det["advance_deductions"])))
    

    approved_reimbursement_amount = Reimbursement.objects.filter(employee=emp_obj,approval_date__gte=ctx_data['pay_cycle_start_date'],approval_date__lte=ctx_data['pay_cycle_end_date']).aggregate(Sum('approved_amount'))['approved_amount__sum']
    approved_reimbursement_amount = approved_reimbursement_amount if approved_reimbursement_amount else 0
    payroll_obj.reimbursed_amount = approved_reimbursement_amount

    payroll_obj.total_earnings += round(approved_reimbursement_amount + det['overtime_pay'] + det['leaves_encash_total_amount'])


    payroll_obj.net_pay = det["net_pay"] + approved_reimbursement_amount
    
    det['compensation_for_esi'] = min(21000, (det['earned_gross'] + det['arrears'] + det['monthly_incentive']))
    det['esi_employee_contribution'] = det['emp_esi']

    det['holidays'] = Holidays.objects.filter(holiday_date__gte=ctx_data['pay_cycle_start_date'], holiday_date__lte=ctx_data['pay_cycle_end_date'], holiday_type=False).count()
    if ctx_data['pay_cycle_start_date'] <= det["doj"] <= ctx_data['pay_cycle_end_date']:
        det['weekly_offs'] = get_weekend_count(det["doj"], ctx_data['pay_cycle_end_date'])
    elif last_working_date and ctx_data['pay_cycle_start_date'] <= last_working_date <= ctx_data['pay_cycle_end_date']:
        det['weekly_offs'] = get_weekend_count(ctx_data['pay_cycle_start_date'], last_working_date)
    else:
        det['weekly_offs'] = get_weekend_count(ctx_data['pay_cycle_start_date'], ctx_data['pay_cycle_end_date'])

    #det['weekly_offs'] = get_weekend_count(ctx_data['pay_cycle_start_date'], ctx_data['pay_cycle_end_date'])
    det['days_present'] = det['working_days'] - det["leaves"] - det["lop"] - det["weekly_offs"]
    if det['days_present'] < 0:
        det['days_present'] = 0
    det['staff_loan_deduction'] = 0
    det['other_deduction'] = 0

    payroll_obj.compensation_for_esi = det['compensation_for_esi']
    payroll_obj.holidays = det['holidays']
    payroll_obj.weekly_offs = det['holidays']
    payroll_obj.days_present = det['days_present']
    payroll_obj.staff_loan_deduction = det['staff_loan_deduction']
    payroll_obj.comments=det['comments']
    payroll_obj.other_deduction=det['other_deduction']
    idc_obj.save()
    payroll_obj.save() 
 
    # det = {k: round(v) if isinstance(v, (float)) else v for k, v in det.items()}
    return det



def get_all_salary_details(cmp_id, emp_id=None,dept_id=None,month_year=None,payroll_id=None, txp=None ):
               
    # now = timezone.now()    
    # Fetching company details from company ID
    company_inst = CompanyDetails.objects.get(id=cmp_id)    
    company_name = company_inst.company_name
    # employer_pf = company_inst.epf_comp.is_employer_contribution_in_ctc        
    # employer_esi = company_inst.esi_comp.is_employer_contribution_in_ctc            
    
    # Fetching Employer ESI percent - 3.25%
    employer_esi_pct = company_inst.esi_comp.employer_contribution_pct            
    
    # Fetching Employer ESI percent - 0.75%    
    employee_esi_pct = company_inst.esi_comp.employee_contribution_pct

    # Month and Year for which - payroll details will be calculated
    # Eg. Apr-2023 | ['Apr','2023']
    year_month_split_list = month_year.split('-')    
    
    month_of_payroll_running = datetime.datetime.strptime(year_month_split_list[0], '%b').month    # in integer -> 1-12
    year_of_payroll_running = year_month_split_list[1]
    
    # print("Hii", month_of_payroll_running)
    # if month_of_payroll_running == 12:
    #     year_of_payroll_running = int(year_of_payroll_running)
    #     year_of_payroll_running +=  1
    #     year_of_payroll_running = str(year_of_payroll_running)
    # tuple (int,int) weekday, no. of days in month
    month_days = monthrange(int(year_of_payroll_running), month_of_payroll_running)[1]   
    # print("month days", month_days)    
        
    pay_cycle_start_day, pay_cycle_end_day = get_pay_cycle_start_and_end_day(cmp_id,month_days)
    # 21 - 20

    # Fetching current year on which user is performing action
    # Jan-2024
    financial_year_start, financial_year_end, cur_month, cur_year = get_current_financial_year_start_and_end(month_of_payroll_running,year_of_payroll_running)
    # 

    # if pay cycle start date is 1 then month of payroll running and pay cycle start and end month are same 
    # else pay cycle start month is month of payroll running , end month is (month_of_payroll_running + 1)
    # Eg. 2nd june to 1st july
    # 1st june to - last day of June    
    # 2nd dec 2022 - 1st jan 2023     
   
    pay_cycle_start_date, pay_cycle_end_date = get_pay_cycle_start_and_end_date(financial_year_start,pay_cycle_start_day,month_of_payroll_running,financial_year_end,pay_cycle_end_day,year_of_payroll_running)

    # print("Hello", pay_cycle_end_date)
    # if joining_date < pay_cycle_end_date:    
    # superuser False
    # payroll status is True
    # user__is_active is True
    # print(pay_cycle_end_date)
    query_filters = (Q(payroll_status=True) | Q(payroll_status__isnull=True)) & Q(company__id=cmp_id, date_of_join__lte=pay_cycle_end_date)

   # Filter for Department - tu run payroll for specific department
    if dept_id:
        query_filters&=Q(work_details__department_id__in=dept_id)        

    if emp_id: # Get Particular Employee data
        query_filters&=Q(id__in=emp_id)

    all_emp_obj = Employee.objects.filter(query_filters)

    # print(all_emp_obj, all_emp_obj.values('date_of_join'))
    tax_config = company_inst.pt_comp.state.tax_config
    
    health_education_cess = HealthEducationCess.objects.last().health_education_cess
    standard_deduction_obj = FormChoices.objects.get(formtype = 'Standard declaration of 50000 under section 16').id
    InvestmentDeclaration.objects.filter(start_year=2024).exclude(admin_resubmit_status=InvestmentDeclaration.APPROVE).delete()
    context = {
        "month_of_payroll_running":month_of_payroll_running,
        "month_days":month_days,
        "company_name":company_name,
        "payroll_id":payroll_id,
        "txp":txp,
        "month_year":month_year,
        # "employer_pf":employer_pf,
        # "employer_esi":employer_esi,
        "employer_esi_pct":employer_esi_pct,
        "employee_esi_pct":employee_esi_pct,
        "pay_cycle_start_date":pay_cycle_start_date,
        "pay_cycle_end_date":pay_cycle_end_date,
        "financial_year_end":financial_year_end,
        "financial_year_start":financial_year_start,
        "health_education_cess":health_education_cess,
        "cmp_id":cmp_id,
        "tax_config":tax_config,
        "standard_deduction_obj":standard_deduction_obj,
        "cur_year":cur_year
    }
    # payroll_parallel_task = partial(parallel_task,context)

    # with Pool(4) as exe:
        # details = exe.map(payroll_parallel_task, all_emp_obj)  
    from concurrent.futures import wait, ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(4) as exe:
        futures = [exe.submit(parallel_task,context, emp_data) for emp_data in all_emp_obj]
        # wait for all download tasks to complete
        _, _ = wait(futures)
        
        # print('Done', flush=True)
    
    # for each_employee in dict_data: #looping as if one record is improper we need to skip so,
    
    details = [r.result() for r in as_completed(futures)]
    # details.wait()
    # # start all processes
    # for process in processes:
    #     process.start()
    # # wait for all processes to complete
    # for process in processes:
    #     process.join()
    # report that all tasks are completed
    # print('Done', flush=True)

    return {"error":None,"details":list(details)}



def import_employees_task(each_employee,request):    
    ser_data = EmployeeBulkImportSerializer(data=each_employee,context={"request":request})
    if ser_data.is_valid():
        ser_data.save()                                       
    else:                   
        error_list = []
        error_structure = ser_data.errors                     
        for key,val in error_structure.items():                                                                        
            if key == "non_field_errors":                                                             
                for err in val:                                
                    if isinstance(err,list):
                        error_list.append(err[0])
                    else:
                        error_list.append(str(err))
            else:
                error_list.append(key.replace("_"," ") + " cannot be blank, It is mandatory")
        joined_list = '\n'.join(error_list)        
        each_employee.update({"Errors":joined_list})
        return {"error_rows_list":each_employee,"errors":{each_employee['Emp_first_name']:joined_list}}

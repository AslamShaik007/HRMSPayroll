from calendar import monthrange
from attendance.models import AttendanceRuleSettings, EmployeeMonthlyAttendanceRecords
from django.utils import timezone
from django.db.models import F, Sum, Q
from dateutil.relativedelta import relativedelta
from payroll.models import PayrollInformation
from directory.models import Employee
from HRMSApp.models import CompanyDetails
from datetime import timedelta
import datetime
import logging
logger = logging.getLogger("django")
import dateutil.parser as parser

def calculate_tax_for_regime(income, tax_regime, health_cess):
    # print(tax_regime)
    """
    this funtion is for tds calculation
    """
    salary_cuttings = {}
    tax_amount = 0
    slab_breaks = sorted(tax_regime.keys(), reverse=True)

    # print('slab breaks ', slab_breaks)

    # print("line no 8 utils.py - ", income, tax_regime, health_cess)
    for upper_tax_slab in slab_breaks:
        if income > int(upper_tax_slab):
            curr_tax = tax_regime[upper_tax_slab] * (income - int(upper_tax_slab))
            salary_cuttings.update({tax_regime[upper_tax_slab]: curr_tax})
            tax_amount += curr_tax
            income = int(upper_tax_slab)
    
    salary_cuttings_sum = sum(salary_cuttings.values())
    # print('salary_cuttings_sum  ', salary_cuttings_sum)

    health_cess_cuttings = float(salary_cuttings_sum) * float(health_cess)
    total_tax = health_cess_cuttings + salary_cuttings_sum
    return {
        "salary_cuttings": salary_cuttings,
        "salary_cuttings_sum": salary_cuttings_sum,
        "health_cess_cuttings": round(health_cess_cuttings,2),
        "total_tax": total_tax,
    }


def get_input(message):
    inp = input(message)
    if inp == "":
        return 0
    val = int(inp.replace(",", ""))
    return val


class TDS:
    """
    for proper using later...
    """

    tax_amount = 0

    def __init__(self, income, tax_regime, health_cess):
        self.income = income
        self.tax_regime = tax_regime
        self.health_cess = health_cess

    def calculate_tax_for_regime(self, income, tax_regime, health_cess):
        ...


# this function takes the ctc and returns the gross per year
def ctc_to_gross_per_year(ctc,employer_esi_pct=0):    
    
    ctc = float(ctc)
    # print(ctc)
    if ctc >= 381600:
        # if employer_pf:
        #     return ctc - 21600 - 21600
        # else:
        return ctc - 21600

    elif ctc < 381600 and ctc >= 267120:        
        # if employer_pf:
        #     return (ctc / (12*(1 + 0.06 + 0.06))) * 12
        # else:
        return (ctc / (12*(1 + 0.06))) * 12

    else:
        # if employer_esi:            
        #     return (ctc / (12*(1 + 0.06 + 0.0325 + 0.0075)) ) * 12
        # else:            
        return (ctc / (12*(1 + 0.06 + 0.0325)) ) * 12


def get_projected_ctc_for_fixed_pay(fixed_salary,variable_pay,prev_month_paid_total,months_paid):

    # print(fixed_salary,variable_pay,prev_month_paid_total,months_paid)
    avg_sal_month = ((fixed_salary + variable_pay) + float(prev_month_paid_total))/(months_paid+1)

    return avg_sal_month*12
    

def trim_all_columns(df):
    """
    Trim whitespace from ends of each value across all series in dataframe
    """
    trim_strings = lambda x: x.strip() if isinstance(x, str) else x
    return df.applymap(trim_strings)


def get_pay_cycle_start_and_end_day(cmp_id,month_days):
    ars_obj = AttendanceRuleSettings.objects.get(company__id=cmp_id)
    pay_cycle_start_day = ars_obj.attendance_input_cycle_from
    if pay_cycle_start_day == 1:
        pay_cycle_end_day = month_days
    else:
        pay_cycle_end_day = ars_obj.attendance_input_cycle_to
    
    return pay_cycle_start_day, pay_cycle_end_day


def get_current_financial_year_start_and_end(month_of_payroll_running,year_of_payroll_running):
    now = timezone.now()
    cur_year = now.year 
    cur_month = now.month
    month_of_payroll_running = int(month_of_payroll_running)
    year_of_payroll_running = int(year_of_payroll_running)

    if month_of_payroll_running in [1,2,3]:
        financial_year_end = year_of_payroll_running
        financial_year_start = year_of_payroll_running - 1
    else:
        financial_year_end = year_of_payroll_running + 1
        financial_year_start = year_of_payroll_running
    
    return financial_year_start, financial_year_end, cur_month, cur_year


def get_pay_cycle_start_and_end_date(financial_year_start,pay_cycle_start_day,month_of_payroll_running,financial_year_end,pay_cycle_end_day,year_of_payroll_running):
    pay_cycle_end_date_year = financial_year_end
    pay_cycle_start_date_year = financial_year_start   
    year_of_payroll_running = int(year_of_payroll_running)
    if month_of_payroll_running in [12]:
        pay_cycle_start_date_year = year_of_payroll_running
        pay_cycle_end_date_year = year_of_payroll_running + 1
    else:
        pay_cycle_start_date_year = year_of_payroll_running
        pay_cycle_end_date_year = year_of_payroll_running


    pay_cycle_end_month = month_of_payroll_running

    pay_cycle_end_date = datetime.date(pay_cycle_end_date_year, pay_cycle_end_month, pay_cycle_end_day)
    pay_cycle_start_date = datetime.date(pay_cycle_start_date_year, month_of_payroll_running-1, pay_cycle_start_day)

    return pay_cycle_start_date, pay_cycle_end_date


def filters_data_func(cmp_id):
    from payroll.models import PayrollInformation
    filters_data = PayrollInformation.objects.filter(employee__company_id = cmp_id,is_processed=True).annotate(dept_id=F("employee__work_details__department__id"), dept_name=F("employee__work_details__department__name"),emp_id = F("employee_id"), emp_name = F("employee__user__username")).values("dept_id", "dept_name", "emp_id", "emp_name", "month_year")
    return filters_data

def filters_data_ae_func(cmp_id,pend_date):    
    filters_data = Employee.objects.filter(
                                            Q(company_id = cmp_id) & Q(date_of_join__lte=pend_date)
                                            & (Q(payroll_status=True) | Q(payroll_status__isnull=True))
                                           ).annotate(dept_id=F("work_details__department__id"), dept_name=F("work_details__department__name"),emp_id = F("id"), emp_name = F("user__username")).values("dept_id", "dept_name", "emp_id", "emp_name")
    return filters_data

def filters_data_year_func(cmp_id, only_years = False):
    from payroll.models import PayrollInformation
    if only_years == True:
        filters_data = set(PayrollInformation.objects.filter(employee__company_id = cmp_id,is_processed=True).distinct().values_list("month_year__year", flat=True))
    else:
        filters_data = set(PayrollInformation.objects.filter(employee__company_id = cmp_id,is_processed=True).distinct().values_list("month_year", flat=True))
    return filters_data


def get_leaves_lop_for_employee(year,month,empId):
    if month == 0:
        month = 12
    context = {
                "employee": empId,
                "totalLeavesCount": 0,
                "totalLopCount": 0,
                "leavesEncashed":0,
                "totalLeavesTakenTillDate":0,
                "overtimeCount":0
            } 
    
    emar_obj = EmployeeMonthlyAttendanceRecords.objects.filter(
                employee_id = empId, #self.kwargs[self.lookup_url_kwarg],                
            )
    
    if not emar_obj.exists():
        return context

    context['totalLeavesTakenTillDate'] = emar_obj.aggregate(total_leaves_count=Sum('leaves_count'))['total_leaves_count']
    
    emar_obj_month = emar_obj.filter(
                                year = year, #int(leaves_month_year.strftime('%Y')),
                                month = month #int(leaves_month_year.strftime('%m'))
                            )

    if not emar_obj_month.exists():
        return context
    
    emar_obj_month = emar_obj_month[0]

    if emar_obj_month.is_hr_updated:                                                      
            context["totalLeavesCount"] =  emar_obj_month.leaves_count + emar_obj_month.lop_count
            context["totalLopCount"] =  emar_obj_month.updated_hr_lop_count
            context["leavesEncashed"] = emar_obj_month.leaves_encash_count   
            context["overtimeCount"] = emar_obj_month.overtime_count   
            context['orginal_leaves_count'] = emar_obj_month.leaves_count
                 
    else:
        context["totalLeavesCount"] = 0
        context["totalLopCount"] =  0        

    return context

def get_payroll_month_employee(emp_id, is_emp_obj=False):
    """
    this function is used to get the employee payroll month and year which needs to run
    basis of emp doj and attendance i/p cycle
    """
    emp_obj = emp_id
    if not is_emp_obj:
        emp_obj = Employee.objects.get(id = emp_id)

    emp_payroll_run = emp_obj.emp_payroll_info.filter(is_processed=True).order_by('-month_year').first()    
    employee_obj = emp_obj        
    
    if emp_payroll_run:
        to_be_run = emp_payroll_run.month_year + relativedelta(months=1)
        year = to_be_run.year
        month = to_be_run.month
    
    else:
        #first time running the payroll
        company_start_date = emp_obj.company.attendancerulesettings_set.first().attendance_input_cycle_from
        company_end_date = emp_obj.company.attendancerulesettings_set.first().attendance_paycycle_end_date
        # emp_join_date = emp_obj.date_of_join
        # logger.warning("above")
        # logger.warning(company_end_date)
        # logger.warning(emp_join_date)
        # if emp_join_date > company_end_date:
        #     emp_obj = emp_obj.date_of_join + relativedelta(months=1)
        #     year = emp_obj.year
        #     month = emp_obj.month
        # else:
        #     logger.warning("in else")
        emp_obj_doj = emp_obj.date_of_join - relativedelta(months=1)
        year = emp_obj_doj.year
        month = emp_obj_doj.month
    
    lop_obj = employee_obj.montly_attendance.filter(year=year, month=month, is_hr_updated=True)
    emp_payroll = {}
    emp_payroll['year'] = year
    emp_payroll['month'] = month
    
    if lop_obj.exists():
        emp_payroll['lop_exists'] = True
        emp_payroll['total_leaves'] = lop_obj.first().leaves_count + lop_obj.first().lop_count
        emp_payroll['total_lops'] = lop_obj.first().updated_hr_lop_count
    else:
        emp_payroll['lop_exists'] = False
        emp_payroll['total_leaves'] = 0
        emp_payroll['total_lops'] = 0
    
    return emp_payroll

def get_financial_year_start_and_end(date):
    """
    this function takes date returns financial_year_start and  financial_year_end
    """
    year = date.year
    month = date.month

    if month < 4:
        financial_year_start = year - 1
        financial_year_end = year
    else:
        financial_year_start = year
        financial_year_end = year + 1

    return financial_year_start, financial_year_end

def get_payroll_month_year(company, company_obj=True):
    """
    this function returns (paycycle start_date, end_date and month at initial setup) &
                          (payroll  start_date, end_date and month of payroll running )
    #considering only (pay_cycle_end_date) not (attendance_input_cycle_from, attendance_start_month, attendance_input_cycle_to)
    """
    if not company_obj:
        company = CompanyDetails.objects.get(id=company)
    
    company_attendance = company.attendancerulesettings_set.first()
    
    #first month of payroll running
    pay_cycle_end_date = company_attendance.attendance_paycycle_end_date

    _, last_day_of_month = monthrange(pay_cycle_end_date.year, pay_cycle_end_date.month)

    if last_day_of_month == pay_cycle_end_date.day:
        pay_cycle_start_date = pay_cycle_end_date.replace(day=1)
    else:
        pay_cycle_start_date = pay_cycle_end_date-relativedelta(months=1)
        pay_cycle_start_date = pay_cycle_start_date+relativedelta(days=1)
    pay_cycle_month = datetime.date(pay_cycle_end_date.year, pay_cycle_end_date.month, 1)
    
    # #existing payroll
    last_payroll_date = PayrollInformation.objects.filter(employee__company = company, is_processed=True).order_by('-month_year').first()
    if last_payroll_date:
        pay_cycle_start_day = pay_cycle_start_date.day
        pay_cycle_end_day = pay_cycle_end_date.day
        
        last_payroll_date = last_payroll_date.month_year
        last_payroll_year = last_payroll_date.year
        last_payroll_month = last_payroll_date.month

        payroll_start_date = datetime.date(last_payroll_year,
                                            last_payroll_month,
                                            pay_cycle_start_day)
        
        if pay_cycle_start_day == 1:
            _, attendance_cycle_end_date = monthrange(year= last_payroll_year, month=last_payroll_month)

            payroll_end_date = datetime.date(
                                            last_payroll_year,
                                            last_payroll_month,
                                            attendance_cycle_end_date)
            payroll_month = datetime.date(last_payroll_year, last_payroll_month, 1)
        
        else:
            payroll_end_date = datetime.date(last_payroll_year,
                                            last_payroll_month,
                                            pay_cycle_end_day)+relativedelta(months=1)
            payroll_month = datetime.date(last_payroll_year, last_payroll_month, 1)+relativedelta(months=1)

    else:
        payroll_start_date = pay_cycle_start_date
        payroll_end_date = pay_cycle_end_date
        payroll_month = pay_cycle_month

    return {
        "pay_cycle_start_date":pay_cycle_start_date, #attendance rule start date
        "pay_cycle_end_date":pay_cycle_end_date, #attendance rule end date
        "pay_cycle_month":pay_cycle_month, #attendance rule month
        "payroll_start_date":payroll_start_date, #payroll start date if no payroll then attendance rule start date
        "payroll_end_date":payroll_end_date, #payroll end date if no payroll then attendance rule end date
        "payroll_month":payroll_month #payroll month if no payroll then attendance rule month
    }

def get_financial_dates_start_and_end(today=None):
    """
    this function takes date or current date and returns financial start date  financial end date
    """
    if not today:
        today = datetime.datetime.now().date()
    start_year = today.year if today.month >= 4 else today.year - 1
    start_date = datetime.date(start_year, 4, 1)
    end_date = datetime.date(start_year + 1, 3, 31)
    return start_date, end_date

def get_weekend_count(start_date, end_date):
    weekend_count = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() in [5, 6]:  # Saturday = 5, Sunday = 6
            weekend_count += 1
        current_date += timedelta(days=1)
    return weekend_count

def get_paycyclestart_and_paycycle_end(month_year):
    """
    this function is used to get the paycycle start and paycycle end based on attendance rule setting from the payroll month_year
    """
    if isinstance(month_year, str):
        month_year = parser.parse(month_year).date()
    paycycle_start_from = 21
    paycycle_end_to = 20

    start_month = month_year - relativedelta(months=1)
    end_month = month_year

    payroll_start_date = start_month.replace(day=paycycle_start_from)
    payroll_end_date = end_month.replace(day=paycycle_end_to)
    return {"payroll_start_date":payroll_start_date, "payroll_end_date":payroll_end_date}
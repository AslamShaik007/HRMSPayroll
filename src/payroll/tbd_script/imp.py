import pandas as pd
import django
import sys
import os

sys.path.append('./')


if __name__ == "__main__":
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.prod')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1] #pss_indianhr_db , viteglobal_indianhr_db

from django.conf import settings
from payroll.models import PayrollInformation
from directory.models import Employee

if __name__ == "__main__":
    print(settings.BASE_DIR)
    df = pd.read_excel(settings.BASE_DIR / 'PSS_Sep.xlsx',engine='openpyxl')
    for idx,row in df.iterrows():
      
        print(row['email'])
        try:
            
            emp_obj = Employee.objects.get(
               official_email=row['email']
            )

            # emp_obj, _created = PayrollInformation.objects.update_or_create(
            #     employee = emp_obj,
            #     month_year = row['Month']
            # )            
            emp_obj = PayrollInformation.objects.filter(employee=emp_obj).first()
            if not emp_obj:
                emp_obj = PayrollInformation.objects.create(employee=emp_obj)
            emp_obj.month_year = row['month']
            emp_obj.month_days = row['Working Days']
            emp_obj.working_days = row['Working Days']
            emp_obj.paid_days = row['Days Worked']
            emp_obj.leaves = row['Leaves']
            emp_obj.lop = row['LOPD']

            # emp_obj.special_deductions = row['LOPD']
            emp_obj.monthly_incentive = row['Incentives']

            emp_obj.a_basic = row['A.basic']
            emp_obj.a_others = row['A.others']
            emp_obj.arrears = row['Arrears']

            # emp_obj.bank_name = row['FT/NEFT']
            emp_obj.account_number = str(row['Bank account No'])
            emp_obj.bank_name = row['Bank Name']
            
            emp_obj.monthly_ctc = row['Monthly CTC']
            emp_obj.yearly_ctc = row['Yearly CTC']
            
            emp_obj.earned_gross = row['Earned Gross']
            emp_obj.salary_before_tds = row['Earned Gross']

            emp_obj.e_basic = row['E.basic']
            emp_obj.e_hra = row['E.hra']
            emp_obj.e_conv = row['E.conv']
            emp_obj.e_special_allow = row['E.Spl.All']
            
            emp_obj.s_basic = row['S.basic']
            emp_obj.s_hra = row['S.hra']
            emp_obj.s_conv = row['S.conv']
            emp_obj.s_special_allow = row['S.Spl.Allo']
            emp_obj.s_gross = row['S.Gross']

            emp_obj.payable_gross = row['Payable.Gross']

            emp_obj.monthly_tds = row['TDS']
            emp_obj.tds_left = 0

            emp_obj.lop_deduction = row['LOP Deductions']
            emp_obj.other_deduction = row['Other Deductions']

            emp_obj.net_salary = row['Net Salary']
            emp_obj.t_basic = row['T.basic']

            emp_obj.profession_tax = row['PT']
            emp_obj.is_tds_fifty_percent = 0
            
            emp_obj.is_tds_percent_deducted = 0
            emp_obj.consider_tds_percent = 0
            
            emp_obj.pf_basic = row['PF Basic']
            emp_obj.employee_pf = row['PF']
            emp_obj.employer_pf = row['PF Employer contribution']

            emp_obj.employee_esi = row['ESI']
            emp_obj.employer_esi = row['ESI Employer contribution']

            # emp_obj.edli_contribution = row['S.Gross']
            # emp_obj.eps_contribution = row['S.Gross']

            emp_obj.total_epf_contribution = int(row['PF']) + int(row['PF Employer contribution'])
            emp_obj.total_esi_contribution = int(row['ESI']) + int(row['ESI Employer contribution'])

            emp_obj.total_employer_contribution = row['Total Employer contribution']
            emp_obj.total_employee_contribution = int(row['ESI']) + int(row['PF'])

            emp_obj.advance_deduction = row['Advance Deduction']
            emp_obj.total_deduction = row['T.Ded']
            # emp_obj.reimbursed_amount = row['S.Gross']
            emp_obj.net_pay = row['N.pay']
            emp_obj.total_earnings = row['Net Salary']
            emp_obj.department = row['Department']
            emp_obj.designation = row['Designation']
            
            emp_obj.is_processed = True
            

            emp_obj.save()

        except Exception as e:
            print(idx,str(e))
           
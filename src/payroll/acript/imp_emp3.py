import pandas as pd
import django
import sys
import os


env = 'local'

sys.path.append('./')


if __name__ == "__main__":
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f"HRMSProject.settings.{os.environ.get('APP_ENV', 'local')}")
    django.setup()

from django.conf import settings
from payroll.models import PayrollInformation
from directory.models import Employee, EmployeeSalaryDetails

if __name__ == "__main__":
    print(settings.BASE_DIR)
    # month	email	id	epf wages	eps wages	edli wages	EPF Contribution	EPS Contribution	EDLI Contribution

    df = pd.read_excel(settings.BASE_DIR / 'EPF_Report.xlsx',engine='openpyxl')
    for idx,row in df.iterrows():
        # print(idx)        
        # phone_no = 9900000000 + idx
        print(row['email'])
        try:
            
            emp_obj = Employee.objects.get(
               official_email=row['email']
            )

            # emp_obj, _created = EmployeeSalaryDetails.objects.update_or_create(
            #     employee = emp_obj                
            # )            
            emp_obj, _created = EmployeeSalaryDetails.objects.get_or_create(
                employee = emp_obj                
            ) 
            emp_obj.bank_name = row['bank_name']
         
            emp_obj.save()

        except Exception as e:
            print(idx,str(e))
           
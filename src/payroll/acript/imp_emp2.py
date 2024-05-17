import pandas as pd
import django
import sys
import os

sys.path.append('./')


if __name__ == "__main__":
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f"HRMSProject.settings.prod")
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1] #pss_indianhr_db , viteglobal_indianhr_db

from django.conf import settings
from payroll.models import PayrollInformation
from directory.models import Employee

if __name__ == "__main__":
    print(settings.BASE_DIR)
    # month	email	id	epf wages	eps wages	edli wages	EPF Contribution	EPS Contribution	EDLI Contribution

    df = pd.read_excel(settings.BASE_DIR / 'PSS_Sep__EPF_Report.xlsx',engine='openpyxl')
    for idx,row in df.iterrows():
        # print(idx)        
        # phone_no = 9900000000 + idx
        print(row['email'])
        try:
            
            emp_obj = Employee.objects.get(
               official_email=row['email']
            )

            # emp_obj, _created = PayrollInformation.objects.update_or_create(
            #     employee = emp_obj,
            #     month_year = row['month']
            # )            
            emp_obj = PayrollInformation.objects.filter(employee=emp_obj).first()
            if not emp_obj:
                emp_obj = PayrollInformation.objects.create(employee=emp_obj)
            emp_obj.month_year = row['month']
            emp_obj.edli_contribution = row['EDLI Contribution']
            emp_obj.eps_contribution = row['EPS Contribution']

         

            emp_obj.save()

        except Exception as e:
            print(idx,str(e))
           
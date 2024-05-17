import pandas as pd
import django
import sys
import os

env = 'production'

sys.path.append('./')


if __name__ == "__main__":
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f"HRMSProject.settings.{os.environ.get('APP_ENV', 'local')}")
    django.setup()

from django.conf import settings
from payroll.models import EmployeeComplianceNumbers

if __name__ == "__main__":
    print(settings.BASE_DIR)
    df = pd.read_excel(settings.BASE_DIR / 'pss.xlsx',engine='openpyxl')
    for idx,row in df.iterrows():
        # print(idx)
        print(row['email'])
        try:
            empc_obj = EmployeeComplianceNumbers.objects.get(employee__official_email=row['email'])            
            if row['pf']:
                empc_obj.pf_num = row['pf']
            else:
                empc_obj.pf_num = ''
            if row['uan']:
                empc_obj.uan_num = row['uan']
            if row['esi']:
                empc_obj.esi_num = row['esi']
            if row['name']:
                empc_obj.nominee_name = row['name']
            if row['rel']:
                empc_obj.nominee_rel = row['rel']
            if row['dob']:
                empc_obj.nominee_dob = row['dob']
            empc_obj.save()

        except Exception as e:
            print(idx,str(e))
           
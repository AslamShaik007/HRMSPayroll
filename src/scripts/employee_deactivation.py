import sys
import os
import django
import datetime
from django.db import transaction
sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from directory.models import EmployeeWorkDetails, EmployeeResignationDetails, EmployeeWorkHistoryDetails
from core.utils import timezone_now

today = timezone_now().date()
next_day = timezone_now().date() + datetime.timedelta(days=1)


class EmployeeDeactivation:

    def termination_change(self, emp_id):
        work_details = EmployeeWorkDetails.objects.get(employee_id=emp_id)
        work_details.employee_status = 'Inactive'
        work_details.save()
        EmployeeWorkHistoryDetails.objects.filter(employee_id=emp_id, work_to__isnull=True).update(work_to=timezone_now())
    
    def status_change(self):
        bulk_change = EmployeeWorkDetails.objects.filter(employee_id__in=self.emp_ids)
        bulk_change.update(employee_status='Inactive')
        print(bulk_change)
        
    # @transaction.atomic()
    def main(self, emp_ids):
        sid = transaction.set_autocommit(autocommit=False)
        self.emp_ids = emp_ids
        self.status_change()
        if "commit" in sys.argv: 
            transaction.commit()
            print("Employees Deactivated successfully!")
        else:
            transaction.rollback(sid)
            print("Dry Run!")


if __name__ == "__main__":
    # last_w_day_emps = list(EmployeeResignationDetails.objects.filter(last_working_day__lte=today).only('employee_id').values_list('employee_id', flat=True))
    # last_w_day_emps.extend(
    #     list(EmployeeResignationDetails.objects.filter(termination_date__lte=today).only('employee_id').values_list('employee_id', flat=True))
    # )
    last_w_day_emps = list(EmployeeResignationDetails.objects.filter(last_working_day__lte=today,reason_of_leaving__in=['Absconded','Terminated']).only('employee_id').values_list('employee_id', flat=True))
    last_w_day_emps.extend(
        list(EmployeeResignationDetails.objects.filter(last_working_day=next_day,reason_of_leaving__in=['Resigned']).only('employee_id').values_list('employee_id', flat=True))
    )
    EmployeeWorkHistoryDetails.objects.filter(employee_id__in=list(set(last_w_day_emps)), work_to__isnull=True).update(work_to=timezone_now())
    EmployeeDeactivation().main(list(set(last_w_day_emps)))

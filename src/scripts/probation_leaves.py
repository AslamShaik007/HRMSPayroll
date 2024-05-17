import sys
import os
import traceback
import django
import math
import datetime
import logging

sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from django.db import models as db_models

from core.utils import timezone_now

from directory.models import Employee

from leave.serializers import EmployeeLeaveRuleRelationSerializer
from leave.models import LeaveRules

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s -  %(levelname)s - %(message)s')

class ProbationAdd:
    
    def main(self, emp, l_rules):
        try:
            assigned_rules = list(emp.employeeleaverulerelation_set.all().values_list('leave_rule_id', flat=True))
            rules = list(l_rules.exclude(id__in=assigned_rules).values_list('id', flat=True))
            ser = EmployeeLeaveRuleRelationSerializer(data={"employee": [emp.id], "rules": rules, "effective_date": emp.date_of_join + datetime.timedelta(days=emp.work_details.probation_period if emp.work_details.probation_period else 0)})
            ser.is_valid(raise_exception=True)
            ser.save()
        except Exception as e:
            print(e)

if  __name__ == "__main__":
    today = timezone_now()
    l_rules = LeaveRules.objects.filter(
        allowed_under_probation=False, is_deleted=False, valid_from__lte=today, valid_to__gte=today
    )
    emps = Employee.objects.filter(work_details__probation_period__isnull=False, work_details__employee_status='Active').annotate(
        prob_end_date=db_models.ExpressionWrapper(
            db_models.F('date_of_join') + db_models.functions.Cast(db_models.F('work_details__probation_period'), output_field=db_models.IntegerField()),
            output_field=db_models.DateField()
        ),
        # assigned_rules=ArrayAgg(
        #     'employeeleaverulerelation__leave_rule_id',
        #     filter=db_models.Q(employeeleaverulerelation__leave_rule__is_deleted=False),
        #     distinct=True
        # )
    ).filter(
        prob_end_date=today, 
    )
    logging.critical(f"Employees Completing Probation :::{', '.join(list(emps.values_list('user__username', flat=True)))}")
    for emp in emps:
        ProbationAdd().main(emp, l_rules)

# db_con = 'pss'
# emps = Employee.objects.using(db_con).filter(work_details__probation_period__isnull=False, work_details__employee_status='Active').annotate(
#     prob_end_date=db_models.ExpressionWrapper(
#         db_models.F('date_of_join') + db_models.functions.Cast(db_models.F('work_details__probation_period'), output_field=db_models.IntegerField()),
#         output_field=db_models.DateField()
#     ),
#     # assigned_rules=ArrayAgg(
#     #     'employeeleaverulerelation__leave_rule_id',
#     #     filter=db_models.Q(employeeleaverulerelation__leave_rule__is_deleted=False),
#     #     distinct=True
#     # )
# ).filter(
#     prob_end_date__range=['2023-12-21', today], 
# )

# df = pd.DataFrame(emps.annotate(lrs=ArrayAgg(db_models.functions.Concat(F('employeeleaverulerelation__leave_rule__name'), db_models.Value('  '), db_models.F('employeeleaverulerelation__remaining_leaves'), db_models.Value('/'), db_models.F('employeeleaverulerelation__earned_leaves'), output_field=db_models.CharField()))).values('work_details__employee_number', 'user__username', 'prob_end_date', 'date_of_join', 'lrs'))
# df.to_excel(f'{db_con}_lrs.xlsx')
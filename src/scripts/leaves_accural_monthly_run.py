import sys
import os
import traceback
import django
import math
import datetime

sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from django.db import models as db_models
from django.utils import timezone
from django.db import transaction
from leave.models import EmployeeLeaveRuleRelation
from directory.models import EmployeeWorkDetails
from core.utils import timezone_now

today = timezone_now().date()

quaterly = {"1":{'Jan', 'Feb', 'Mar'}, "2":{'Apr', 'May', 'Jun'}, "3":{'Jul', 'Aug', 'Sep'}, "4":{'Oct', 'Nov', 'Dec'}}
half_yearly ={"1":{'Jan', 'Feb', 'Mar','Apr', 'May', 'Jun'}, "2":{'Jul', 'Aug', 'Sep','Oct', 'Nov', 'Dec'}}


class AccuralLevesCredit:
    
    def process_no_of_leaves(self, leave_count):
        fact_val, l_count = math.modf(float(leave_count))
        if fact_val < 0.5:
            return l_count
        elif 0.5 <= fact_val < 1:
            return l_count + 0.5

    def main(self,emps_leaves_relation):
        print("emps_leaves_relation", emps_leaves_relation)
        today_month = today.strftime("%b")
        today_month_number = datetime.datetime.strptime(today_month, "%b").month

        for emp_leave_relation in emps_leaves_relation:
            leave_rule = emp_leave_relation.leave_rule
            emp_leave_relation.employee.date_of_join.strftime("%b")

            last_credit_month_name = list(emp_leave_relation.extra_data.keys())[0]
            
            last_credit_month_number = datetime.datetime.strptime(last_credit_month_name, "%b").month

            if (leave_rule.accrual_frequency == "MONTHLY") and (last_credit_month_number < today_month_number):
                diff_months = today_month_number-last_credit_month_number
                monthly_credit_leaves = leave_rule.leaves_allowed_in_year / 12
                emp_leave_relation.earned_leaves += monthly_credit_leaves*diff_months
                emp_leave_relation.remaining_leaves += monthly_credit_leaves*diff_months
                emp_leave_relation.extra_data = {today_month:float(monthly_credit_leaves)}
                
            elif (leave_rule.accrual_frequency == "QUARTERLY"):
                current_quarter = {month: key for key, months in quaterly.items() for month in months}.get(today_month) #returns 3 if month is Aug
                employee_leaves_credited_month = list(emp_leave_relation.extra_data.keys())[0]
                credited_quarter = {month: key for key, months in quaterly.items() for month in months}.get(employee_leaves_credited_month)
                
                if credited_quarter != current_quarter:
                    diff_quaters = int(current_quarter) - int(credited_quarter)
                    quaterly_credit_leaves = leave_rule.leaves_allowed_in_year / 4
                    emp_leave_relation.earned_leaves += quaterly_credit_leaves*diff_quaters
                    emp_leave_relation.remaining_leaves += quaterly_credit_leaves*diff_quaters
                    emp_leave_relation.extra_data = {today_month : float(quaterly_credit_leaves)}

            elif leave_rule.accrual_frequency == "HALF_YEARLY":
                current_quarter = {month: key for key, months in half_yearly.items() for month in months}.get(today_month)
                employee_leaves_credited_month = list(emp_leave_relation.extra_data.keys())[0]
                credited_quarter = {month: key for key, months in half_yearly.items() for month in months}.get(employee_leaves_credited_month)
                
                if credited_quarter != current_quarter:
                    half_year_credit_leaves = leave_rule.leaves_allowed_in_year / 2
                    emp_leave_relation.earned_leaves += half_year_credit_leaves
                    emp_leave_relation.remaining_leaves += half_year_credit_leaves
                    emp_leave_relation.extra_data = {today_month : float(half_year_credit_leaves)}
            
            else:
                print("some thing other came", str(leave_rule.accrual_frequency),"or this cron run multiple times which causes no problems")
            emp_leave_relation.earned_leaves = self.process_no_of_leaves(emp_leave_relation.earned_leaves)
            emp_leave_relation.remaining_leaves = self.process_no_of_leaves(emp_leave_relation.remaining_leaves)
            # emp_leave_relation.extra_data = {today_month : self.process_no_of_leaves(emp_leave_relation.extra_data[today_month])}
            emp_leave_relation.save()



if __name__ == "__main__":
    sid = transaction.set_autocommit(autocommit=False)
    try:
        active_emps = EmployeeWorkDetails.objects.filter(employee_status = "Active").values_list('employee_id', flat=True)
        q_filters = db_models.Q(leave_rule__creditable_on_accrual_basis = True, effective_date__lte=timezone.now(),employee__in = active_emps)
        session_year = timezone_now().date().year
        # company_ids = [sys.argv[2]].remove("")
        # employee_ids = [sys.argv[3]].remove("")
        accural_period = None

        # print("company_ids", company_ids,"employee_ids", type(employee_ids),"accural_period", accural_period)

        # if company_ids:
        #     print("in company ids")
        #     q_filters &= db_models.Q(employee__company_id__in = company_ids)
        # if employee_ids:
        #     q_filters &= db_models.Q(employee_id__in = employee_ids)
        if accural_period and (accural_period not in ("Start","End")):
            q_filters &= db_models.Q(leave_rule__LeaveRules__accruel_period = accural_period)

        emps_leaves_relation = EmployeeLeaveRuleRelation.objects.filter(q_filters, session_year__session_year=session_year)
        AccuralLevesCredit().main(emps_leaves_relation)
        if "commit" in sys.argv:
            transaction.commit()
            print("leaves accural monthly run successfully")
        else:
            transaction.rollback(sid)
            print("Dry Run!")
    except Exception as e:
        print(f'{e}  Error: {traceback.format_exc()}')
        transaction.rollback(sid)
    # transaction.savepoint_commit(sid=sid)
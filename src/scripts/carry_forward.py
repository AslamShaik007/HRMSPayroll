import sys
import os
import django

from django.db import models as db_models
from django.db import transaction
sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from core.utils import timezone_now
from directory.models import SessionYear
from leave import models as leave_models
from attendance.models import EmployeeMonthlyAttendanceRecords
from attendance.services import get_monthly_record_obj_month, fetch_attendace_rule_start_end_dates
class CarryForwardLeaves:
    
    def __init__(self,company_id, current_session_year=timezone_now().year, upcoming_session_year=timezone_now().year+1):
        self.current_session_year = SessionYear.objects.filter(session_year=current_session_year)
        self.upcoming_session_year = SessionYear.objects.filter(session_year=upcoming_session_year)
        self.company_id = company_id
        if not self.current_session_year.exists() or not self.upcoming_session_year.exists():
            sys.exit("Session Years Were not created")
        self.current_session_year = self.current_session_year.first()
        self.upcoming_session_year = self.upcoming_session_year.first()
        
    # @transaction.atomic()
    def main(self):
        sid = transaction.set_autocommit(autocommit=False)
        emp_leave_rels = leave_models.EmployeeLeaveRuleRelation.objects.filter(
            db_models.Q(session_year=self.current_session_year, remaining_leaves__gt=0, is_deleted=False, leave_rule__is_deleted=False) & 
            (db_models.Q(leave_rule__carry_forward_enabled=True) | db_models.Q(leave_rule__is_leave_encashment_enabled=True))
        ).values('employee_id', 'leave_rule_id', 'remaining_leaves', 'leave_rule__max_leaves_to_carryforward',
                'leave_rule__all_remaining_leaves', 'leave_rule__leaves_allowed_in_year', 'session_year__session_year','leave_rule__carry_forward_enabled',
                'leave_rule__is_leave_encashment_enabled','leave_rule__all_remaining_leaves_for_encash','leave_rule__max_leaves_to_encash')
        
        # data = emp_leave_rels1.to_dict('records')
        if emp_leave_rels.exists():
            attendance_start_day, attendace_end_day = fetch_attendace_rule_start_end_dates(self.company_id)
            current_date = timezone_now().date()
            current_year = current_date.year
            check_month = get_monthly_record_obj_month(attendance_start_day, attendace_end_day, timezone_now().date())
            next_month = 1 if check_month == 12 else check_month+1
            if next_month == 1:
                current_year+=1
            for obj in emp_leave_rels:
                if obj['leave_rule__carry_forward_enabled'] and obj['leave_rule__is_leave_encashment_enabled']:
                    earned_leaves = obj['remaining_leaves']
                    leave_encash_requested_count =  0

                    if not obj['leave_rule__all_remaining_leaves']:
                        max_carryforward = obj['leave_rule__max_leaves_to_carryforward']
                        if max_carryforward < earned_leaves:
                            if (obj['leave_rule__all_remaining_leaves_for_encash'] or 
                                obj['leave_rule__max_leaves_to_encash'] > earned_leaves - max_carryforward ):
                                leave_encash_requested_count = earned_leaves - max_carryforward
                            else:
                                leave_encash_requested_count = obj['leave_rule__max_leaves_to_encash']
                                
                            earned_leaves = max_carryforward

                    query = leave_models.EmployeeLeaveRuleRelation.objects.filter(
                        employee_id=obj['employee_id'], leave_rule_id=obj['leave_rule_id'], session_year=self.upcoming_session_year)

                    att_rec, is_created = EmployeeMonthlyAttendanceRecords.objects.get_or_create(employee_id=obj['employee_id'],year=current_year,month=next_month)
                    att_rec.leaves_encash_count += float(leave_encash_requested_count)
                    att_rec.save()
                    
                    if query.exists():
                        query.update(earned_leaves = obj['leave_rule__leaves_allowed_in_year'] + earned_leaves,
                                    remaining_leaves = obj['leave_rule__leaves_allowed_in_year'] + earned_leaves,
                                )
                    else:
                        leave_models.EmployeeLeaveRuleRelation.objects.create(
                                                employee_id=obj['employee_id'], leave_rule_id=obj['leave_rule_id'], 
                                                session_year=self.upcoming_session_year,
                                                earned_leaves = obj['leave_rule__leaves_allowed_in_year'] + earned_leaves,
                                                remaining_leaves = obj['leave_rule__leaves_allowed_in_year'] + earned_leaves
                        )
                            
                elif obj['leave_rule__carry_forward_enabled']:
                    earned_leaves = obj['remaining_leaves']
                    if not obj['leave_rule__all_remaining_leaves']:
                        max_carryforward = obj['leave_rule__max_leaves_to_carryforward']
                        earned_leaves = min(earned_leaves, max_carryforward)
                            
                    query = leave_models.EmployeeLeaveRuleRelation.objects.filter(
                        employee_id=obj['employee_id'], leave_rule_id=obj['leave_rule_id'], session_year=self.upcoming_session_year)
                    
                    if query.exists():
                        query.update(earned_leaves = obj['leave_rule__leaves_allowed_in_year'] + earned_leaves,
                                    remaining_leaves = obj['leave_rule__leaves_allowed_in_year'] + earned_leaves
                                )
                    else:
                        leave_models.EmployeeLeaveRuleRelation.objects.create(
                                                employee_id=obj['employee_id'], leave_rule_id=obj['leave_rule_id'], 
                                                session_year=self.upcoming_session_year,
                                                earned_leaves = obj['leave_rule__leaves_allowed_in_year'] + earned_leaves,
                                                remaining_leaves = obj['leave_rule__leaves_allowed_in_year'] + earned_leaves
                                                )
                        
                elif obj['leave_rule__is_leave_encashment_enabled']:
                    leave_encash_requested_count = obj['remaining_leaves']
                    if not obj['leave_rule__all_remaining_leaves_for_encash']:
                        max_carryforward = obj['leave_rule__max_leaves_to_encash']
                        leave_encash_requested_count = min(leave_encash_requested_count, max_carryforward)
                        
                    att_rec, is_created = EmployeeMonthlyAttendanceRecords.objects.get_or_create(employee_id=obj['employee_id'],year=current_year,month=next_month)
                    att_rec.leaves_encash_count += float(leave_encash_requested_count)
                    att_rec.save()
        if "commit" in sys.argv:
            transaction.commit()    
            print("Carry forward and Leaves Enchash created successfully!")
        else:
            transaction.rollback(sid)
            print("Dry Run!")
            
if __name__ == "__main__":
    company_id = 1
    CarryForwardLeaves(company_id=company_id).main()

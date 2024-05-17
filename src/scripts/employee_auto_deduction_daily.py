import sys
import os
import django
import datetime
import pandas as pd
import traceback
from dateutil.relativedelta import relativedelta

sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from django.db import transaction
from django.db.models import Q, F
from attendance import models as attendance_models
from leave import models as leave_models
from core.utils import get_month_weeks
from leave.services import is_day_type

from core.utils import hrs_to_mins, localize_dt, mins_to_hrs, timezone_now

class AutoDeductionDailyRun:
    def convert_to_hours(self, delta):
        total_seconds = delta.total_seconds()
        hours = str(int(total_seconds // 3600)).zfill(2)
        minutes = str(int((total_seconds % 3600) // 60)).zfill(2)
        return f"{hours}:{minutes}"

    def half_day_check(self, clock_id):
        clock = attendance_models.EmployeeCheckInOutDetails.objects.get(id=clock_id)
        week_number = get_month_weeks(clock.date_of_checked_in)[clock.date_of_checked_in.day]
        return is_day_type(
            clock.employee.employeeworkrulerelation_set.first().work_rule.work_rule_choices.get(week_number=week_number),
            1,
            clock.date_of_checked_in
        )

    # def half_day_time_manipulations(self, date_of_checked_in, day_work_duration, is_leave_exists, is_half_day):
    #     delta_time = datetime.datetime.combine(date_of_checked_in,  datetime.datetime.strptime(day_work_duration, "%H:%M").time()) - datetime.datetime.combine(date_of_checked_in,  datetime.time(0,0))
    #     chk =  '{:02d}:{:02d}'.format(*divmod((delta_time.seconds // 60)//2 if is_leave_exists or is_half_day else 1 , 60))
    #     return [
    #         chk.split(":")[0],
    #         chk.split(":")[1]
    #     ]

    def create_deduction_history(self, employee, clock, choice, result, request_date):
        if work_rule_relation := leave_models.EmployeeWorkRuleRelation.objects.filter(
            employee=employee, effective_date__lte=request_date
        ).first():
            work_rule = work_rule_relation.work_rule
            week_number = get_month_weeks(
            request_date, need_week_number_only=True
            )
            rule_choice = leave_models.WorkRuleChoices.objects.filter(
            work_rule=work_rule, week_number=week_number
            ).first()
            if is_day_type(choice=rule_choice, dt_input=request_date):
                return ''
        if attendance_models.AutoDeductionHistory.objects.filter(
            clock_id=clock, choice=choice,  request_date=request_date
        ).exists():
            return attendance_models.AutoDeductionHistory.objects.filter(
                clock_id=clock, choice=choice,  request_date=request_date
            ).update(result=result)
        return attendance_models.AutoDeductionHistory.objects.create(
            clock_id=clock, choice=choice,
            result=result, request_date=request_date
        )

    def max_break_breach_check(self):
        check_df = self.final_df[['id', 'time_in', 'breaks', 'attendance_rule__max_breaks', 'employee']]
        check_df.apply(
            lambda obj: self.create_deduction_history(obj['employee'], 
                obj['id'], 'MAX_TOTAL_BREAKS_BREACH', obj['breaks'] - obj['attendance_rule__max_breaks'], obj['time_in'].date()
            ) if obj['breaks'] > obj['attendance_rule__max_breaks'] else '', axis=1
        )
        del check_df

    def break_duration_breach_check(self):
        check_df = self.final_df[['id', 'time_in', 'break_duration', 'attendance_rule__max_break_duration', 'employee']]
        check_df.break_duration = check_df.break_duration.fillna('0:0')
        check_df.attendance_rule__max_break_duration = check_df.attendance_rule__max_break_duration.fillna('0:0')
        check_df[['b_h', 'b_m']] = check_df.break_duration.str.split(':', expand=True)
        check_df.b_h = check_df.b_h.apply(lambda x: int(x))
        check_df.b_m = check_df.b_m.apply(lambda x: int(x))
        check_df[['r_h', 'r_m']] = check_df.attendance_rule__max_break_duration.str.split(':', expand=True)
        check_df.r_h = check_df.r_h.apply(lambda x: int(x))
        check_df.r_m = check_df.r_m.apply(lambda x: int(x))
        check_df.apply(
            lambda obj: self.create_deduction_history(obj['employee'], 
                obj['id'], 'MAX_BREAK_DURATION_BREACH', self.convert_to_hours(
                    datetime.datetime.combine(
                        datetime.datetime.fromtimestamp(obj['time_in'].timestamp()).date(), datetime.datetime.strptime(f"{obj['b_h']}:{obj['b_m']}", "%H:%M").time()    
                    ) - datetime.datetime.combine(
                        datetime.datetime.fromtimestamp(obj['time_in'].timestamp()).date(), datetime.datetime.strptime(f"{obj['r_h']}:{obj['r_m']}", "%H:%M").time()    
                    )
                ), obj['time_in'].date()
            ) if datetime.datetime.combine(
                datetime.datetime.fromtimestamp(obj['time_in'].timestamp()).date(), datetime.datetime.strptime(f"{obj['b_h']}:{obj['b_m']}", "%H:%M").time()    
            ) > datetime.datetime.combine(
                datetime.datetime.fromtimestamp(obj['time_in'].timestamp()).date(), datetime.datetime.strptime(f"{obj['r_h']}:{obj['r_m']}", "%H:%M").time()    
            ) else '', axis=1
        )
        del check_df

    def full_day_breach_check(self):
        check_df = self.final_df[['id', 'is_half_day', 'time_in', 'work_duration', 'attendance_rule__full_day_work_duration', 'employee', 'date_of_checked_in']]
        check_df.work_duration = check_df.work_duration.fillna('0:0')
        check_df.attendance_rule__full_day_work_duration = check_df.attendance_rule__full_day_work_duration.fillna('0:0')
        check_df[['wd_h', 'wd_m']] = check_df.work_duration.str.split(':', expand=True)
        check_df.wd_h = check_df.wd_h.apply(lambda x: int(x))
        check_df.wd_m = check_df.wd_m.apply(lambda x: int(x))
        check_df[['r_h', 'r_m']] = check_df.attendance_rule__full_day_work_duration.str.split(':', expand=True)
        check_df['is_leave_exists'] = check_df.apply(lambda obj:  leave_models.LeavesHistory.objects.filter(Q(employee_id=obj['employee'], start_date__lte=obj['date_of_checked_in'], end_date__gte=obj['date_of_checked_in'], status=10) &  (Q(start_day_session__isnull=False)| Q(end_day_session__isnull=False))).exists(), axis=1)
        check_df[['r_h', 'r_m']] = check_df.attendance_rule__full_day_work_duration.str.split(':', expand=True)

        check_df.r_h = check_df.apply(lambda obj: int(int(obj['r_h']) // 2) if obj['is_leave_exists'] or obj['is_half_day'] else  int(obj['r_h']), axis=1)
        check_df.r_m = check_df.apply(lambda obj: int(int(obj['r_m']) // 2) if obj['is_leave_exists'] or obj['is_half_day'] else  int(obj['r_m']), axis=1)
        check_df.apply(
            lambda obj: self.create_deduction_history(obj['employee'], 
                obj['id'], 'FULL_DAY_WD_BREACH', self.convert_to_hours(
                    datetime.datetime.combine(
                        datetime.datetime.fromtimestamp(obj['time_in'].timestamp()).date(), datetime.datetime.strptime(f"{obj['r_h']}:{obj['r_m']}", "%H:%M").time()    
                    ) - datetime.datetime.combine(
                        datetime.datetime.fromtimestamp(obj['time_in'].timestamp()).date(), datetime.datetime.strptime(f"{obj['wd_h']}:{obj['wd_m']}", "%H:%M").time()    
                    )
                ), obj['time_in'].date()
            ) if datetime.datetime.combine(
                datetime.datetime.fromtimestamp(obj['time_in'].timestamp()).date(), datetime.datetime.strptime(f"{obj['wd_h']}:{obj['wd_m']}", "%H:%M").time()    
            ) < datetime.datetime.combine(
                datetime.datetime.fromtimestamp(obj['time_in'].timestamp()).date(), datetime.datetime.strptime(f"{obj['r_h']}:{obj['r_m']}", "%H:%M").time()    
            ) else '', axis=1
        )
        del check_df

    def half_day_breach_check(self):
        check_df = self.final_df[['id', 'time_in', 'work_duration', 'attendance_rule__half_day_work_duration', 'employee', 'date_of_checked_in', 'is_half_day']]
        check_df.work_duration = check_df.work_duration.fillna('0:0')
        check_df.attendance_rule__half_day_work_duration = check_df.attendance_rule__half_day_work_duration.fillna('0:0')
        check_df[['wd_h', 'wd_m']] = check_df.work_duration.str.split(':', expand=True)
        check_df.wd_h = check_df.wd_h.apply(lambda x: int(x))
        check_df.wd_m = check_df.wd_m.apply(lambda x: int(x))
        check_df['is_leave_exists'] = check_df.apply(lambda obj:  leave_models.LeavesHistory.objects.filter(Q(employee_id=obj['employee'], start_date__lte=obj['date_of_checked_in'], end_date__gte=obj['date_of_checked_in'], status=10) &  (Q(start_day_session__isnull=False)| Q(end_day_session__isnull=False))).exists(), axis=1)
        check_df[['r_h', 'r_m']] = check_df.attendance_rule__half_day_work_duration.str.split(':', expand=True)

        check_df.r_h = check_df.apply(lambda obj: int(int(obj['r_h']) // 2) if obj['is_leave_exists'] or obj['is_half_day'] else  int(obj['r_h']), axis=1)
        check_df.r_m = check_df.apply(lambda obj: int(int(obj['r_m']) // 2) if obj['is_leave_exists'] or obj['is_half_day'] else  int(obj['r_m']), axis=1)

        check_df.apply(
            lambda obj: self.create_deduction_history(obj['employee'], 
                obj['id'], 'HALF_DAY_WD_BREACH', self.convert_to_hours(
                    datetime.datetime.combine(
                        datetime.datetime.fromtimestamp(obj['time_in'].timestamp()).date(), datetime.datetime.strptime(f"{obj['r_h']}:{obj['r_m']}", "%H:%M").time()    
                    ) - datetime.datetime.combine(
                        datetime.datetime.fromtimestamp(obj['time_in'].timestamp()).date(), datetime.datetime.strptime(f"{obj['wd_h']}:{obj['wd_m']}", "%H:%M").time()    
                    )
                ), obj['time_in'].date()
            ) if datetime.datetime.combine(
                datetime.datetime.fromtimestamp(obj['time_in'].timestamp()).date(), datetime.datetime.strptime(f"{obj['wd_h']}:{obj['wd_m']}", "%H:%M").time()    
            ) < datetime.datetime.combine(
                datetime.datetime.fromtimestamp(obj['time_in'].timestamp()).date(), datetime.datetime.strptime(f"{obj['r_h']}:{obj['r_m']}", "%H:%M").time()    
            ) else '', axis=1
        )
        del check_df

    def early_time_out_deduction_check(self):
        check_df = self.final_df[['id', 'time_out', 'attendance_rule__shift_out_time', 'attendance_rule__grace_out_time', 'employee', 'date_of_checked_in']]
        check_df.attendance_rule__grace_out_time = check_df.attendance_rule__grace_out_time.fillna('0:0')
        check_df[['out_g_h', 'out_g_m']] = check_df.attendance_rule__grace_out_time.str.split(':', expand=True)
        check_df.out_g_h = check_df.out_g_h.apply(lambda x: int(x))
        check_df.out_g_m = check_df.out_g_m.apply(lambda x: int(x))
        check_df['shift_grace_out_time'] = check_df.apply(
            lambda obj:  (datetime.datetime.strptime(
                f"{obj['attendance_rule__shift_out_time'].hour}:{0 if obj['attendance_rule__shift_out_time'].minute < 10 else ''}{obj['attendance_rule__shift_out_time'].minute}", "%H:%M"
            ) - datetime.timedelta(hours=obj['out_g_h']) - datetime.timedelta(minutes=obj['out_g_m'])).time(),
            axis=1
        )
        check_df.apply(lambda obj: self.create_deduction_history(obj['employee'], 
                obj['id'], 'OUT_TIME_BREACH', 
                self.convert_to_hours(
                    datetime.datetime.combine(obj['date_of_checked_in'], obj['shift_grace_out_time']) - datetime.datetime.fromtimestamp(obj['time_out'].timestamp())
                ), obj['time_out'].date()
            ) if datetime.datetime.combine(obj['date_of_checked_in'], obj['shift_grace_out_time']) > datetime.datetime.fromtimestamp(obj['time_out'].timestamp()) else '' , axis=1)
        del check_df

    def late_time_in_deduction_check(self):
        check_df = self.final_df[['id', 'time_in', 'attendance_rule__shift_in_time', 'attendance_rule__grace_in_time', 'employee', 'date_of_checked_in']]
        check_df.attendance_rule__grace_in_time = check_df.attendance_rule__grace_in_time.fillna('0:0')
        check_df[['in_g_h', 'in_g_m']] = check_df.attendance_rule__grace_in_time.str.split(':', expand=True)
        check_df.in_g_h = check_df.in_g_h.apply(lambda x: int(x))
        check_df.in_g_m = check_df.in_g_m.apply(lambda x: int(x))
        check_df['shift_grace_in_time'] = check_df.apply(
            lambda obj:  (datetime.datetime.strptime(
                f"{obj['attendance_rule__shift_in_time'].hour}:{0 if obj['attendance_rule__shift_in_time'].minute < 10 else ''}{obj['attendance_rule__shift_in_time'].minute}", "%H:%M"
            ) + datetime.timedelta(hours=obj['in_g_h']) + datetime.timedelta(minutes=obj['in_g_m'])).time(),
            axis=1
        )
        check_df.apply(lambda obj:  self.create_deduction_history(obj['employee'], 
            obj['id'], 'IN_TIME_BREACH', 
            self.convert_to_hours(
                datetime.datetime.fromtimestamp(localize_dt(obj['time_in']).timestamp()) - datetime.datetime.combine(obj['date_of_checked_in'], obj['shift_grace_in_time'])
            ), obj['time_in'].date()
            ) if datetime.datetime.fromtimestamp(obj['time_in'].timestamp()) > datetime.datetime.combine(obj['date_of_checked_in'], obj['shift_grace_in_time']) else '', axis=1)
        del check_df

    def calculate_work_time(self, time_out, latest_time_in, time_in, work_duration):
        current_work_delta = relativedelta(
            time_out, (latest_time_in or time_in)
        )
        work_delta = current_work_delta
        if _prev_work_delta := work_duration:
            _hrs = int(_prev_work_delta.split(":")[0])
            _mins = int(_prev_work_delta.split(":")[1])
            work_delta = relativedelta(hours=_hrs, minutes=_mins) + relativedelta(
                hours=current_work_delta.hours,
                minutes=current_work_delta.minutes,
            )
        return f"{work_delta.hours}:{work_delta.minutes}"

    def update_history_auto_clock_out(self, extra_data, attendance_rule__shift_out_time):
        history = extra_data.get("punch_history", [])
        last_clock_in_ip = next((entry['ip_address'] for entry in reversed(history) if entry['type'] == 'Clock In'), None)
        history.append(
            {
            "time": attendance_rule__shift_out_time.strftime("%I:%M %p"),
            "type": "Clock Out",
            "ip_address": last_clock_in_ip,}
        )
        return {"punch_history": history}

    def auto_clock_out_handle(self):
        check_df = self.final_df.loc[self.final_df.attendance_rule__auto_clock_out==True].loc[self.final_df.time_out == '-'][['id', 'attendance_rule__shift_out_time', 'date_of_checked_in', 'time_in', 'latest_time_in', 'work_duration', "extra_data", "is_half_day","attendance_rule__selected_time_zone"]]
        if len(check_df) == 0:
            del check_df
            return
        check_df['time_out_1'] = check_df.apply(lambda x: localize_dt(dt=datetime.datetime.combine(x['date_of_checked_in'], x['attendance_rule__shift_out_time']),tz=x['attendance_rule__selected_time_zone']), axis=1)
        check_df['work_duration'] = check_df.apply(
            lambda obj: self.calculate_work_time(
                obj["time_out_1"], obj["latest_time_in"], obj["time_in"], obj["work_duration"]
            ), axis=1
        )
        check_df['extra_data'] = check_df.apply(
            lambda obj: self.update_history_auto_clock_out(obj['extra_data'], obj['attendance_rule__shift_out_time']), axis=1
        )
        for ch_data in check_df.to_dict('records'):
            attendance_models.EmployeeCheckInOutDetails.objects.filter(id=ch_data['id']).update(
                time_out=ch_data['time_out_1'], is_logged_out=False, extra_data=ch_data["extra_data"]
            )
        self.final_df.loc[self.final_df.id.isin(list(check_df.id)), ['work_duration', 'extra_data', 'time_out']] = check_df[['work_duration', 'extra_data', 'time_out_1']]
        del check_df
    
    def half_day_manipuldations(self, date_of_checked_in, attendance_rule__shift_in_time,
                                attendance_rule__shift_out_time,attendance_rule__selected_time_zone):
        sh_in = localize_dt(dt=datetime.datetime.combine(date_of_checked_in, attendance_rule__shift_in_time),tz=attendance_rule__selected_time_zone)
        sh_out = localize_dt(dt=datetime.datetime.combine(date_of_checked_in, attendance_rule__shift_out_time),tz=attendance_rule__selected_time_zone)
        td = sh_out - sh_in
        return [
            sh_in.replace(
                hour=sh_in.hour + ((td.seconds//3600)//2),
                minute=sh_in.minute + ((td.seconds//60)//2)
            ).time(),
            sh_out.replace(
                hour=sh_out.hour - ((td.seconds//3600)//2),
                minute=sh_out.minute - ((td.seconds//60)//2)
            ).time() if sh_out.minute - ((td.seconds//60)//2) > 0 else sh_out.replace(
                hour=sh_out.hour - 1 - ((td.seconds//3600)//2),
                minute=60 - sh_out.minute - ((td.seconds//60)//2)
            ).time()
        ]
    
    # @transaction.atomic()
    def main(self, clocks):
        sid = transaction.set_autocommit(autocommit=False)
        try:
            clocks_df =pd.DataFrame(
                clocks.select_related('employee').values('id', 'autodeductionhistory', 'employee', 'employee__assignedattendancerules__attendance_rule',
                'status', 'time_in', 'time_out', 'work_duration', 'break_duration', 'breaks',
                'date_of_checked_in', 'latest_time_in', "extra_data"
                ),
                columns=['id', 'autodeductionhistory', 'employee', 'employee__assignedattendancerules__attendance_rule',
                'status', 'time_in', 'time_out', 'work_duration', 'break_duration', 'breaks', 'date_of_checked_in', 'latest_time_in', "extra_data"]
            )
            clocks_df.rename(columns={'employee__assignedattendancerules__attendance_rule': 'attendance_rule_id'}, inplace=True)
            clocks_df.time_in = clocks_df.time_in.apply(lambda x: localize_dt(x))
            clocks_df.time_out = clocks_df.time_out.fillna("-")
            clocks_df.time_out = clocks_df.time_out.apply(lambda x: localize_dt(x) if not isinstance(x, str) else x)
            rules_df = pd.DataFrame(
                attendance_models.AssignedAttendanceRules.objects.filter(
                    attendance_rule__auto_deduction=True,
                    attendance_rule_id__in=list(set(clocks_df['attendance_rule_id'])),
                    employee_id__in=list(set(clocks_df['employee']))
                ).select_related("attendance_rule").values(
                    'attendance_rule_id',
                    "attendance_rule__shift_in_time", "attendance_rule__shift_out_time", "attendance_rule__enable_anomaly_tracing",
                    "attendance_rule__grace_in_time", "attendance_rule__grace_out_time", "attendance_rule__full_day_work_duration", "attendance_rule__half_day_work_duration",  "attendance_rule__max_break_duration",  "attendance_rule__max_breaks",  "attendance_rule__auto_clock_out","attendance_rule__selected_time_zone"
                ),
                columns=[
                    "attendance_rule_id",
                    "attendance_rule__shift_in_time", "attendance_rule__shift_out_time", "attendance_rule__enable_anomaly_tracing",
                    "attendance_rule__grace_in_time", "attendance_rule__grace_out_time", "attendance_rule__full_day_work_duration", "attendance_rule__half_day_work_duration",  "attendance_rule__max_break_duration",  "attendance_rule__max_breaks",  "attendance_rule__auto_clock_out","attendance_rule__selected_time_zone"
                ]
            )
            rules_df = rules_df.drop_duplicates(subset=('attendance_rule_id')).reset_index(drop=True)
            self.final_df = pd.merge(clocks_df, rules_df, how='left', on=['attendance_rule_id'])
            self.final_df['is_half_day'] = self.final_df.id.apply(
                lambda x: self.half_day_check(x)
            )
            self.auto_clock_out_handle()
            self.final_df.attendance_rule__shift_in_time = self.final_df.apply(lambda obj: obj['attendance_rule__shift_in_time'] if not obj['is_half_day'] else self.half_day_manipuldations(obj['date_of_checked_in'], obj['attendance_rule__shift_in_time'], obj['attendance_rule__shift_out_time'],obj['attendance_rule__selected_time_zone'])[0], axis=1)
            self.final_df.attendance_rule__shift_out_time = self.final_df.apply(lambda obj: obj['attendance_rule__shift_out_time'] if not obj['is_half_day'] else self.half_day_manipuldations(obj['date_of_checked_in'], obj['attendance_rule__shift_in_time'], obj['attendance_rule__shift_out_time'],obj['attendance_rule__selected_time_zone'])[1], axis=1)
            self.late_time_in_deduction_check()
            self.early_time_out_deduction_check()
            self.half_day_breach_check()
            self.full_day_breach_check()
            self.max_break_breach_check()
            self.break_duration_breach_check()
            del self.final_df
            if "commit" in sys.argv: 
                transaction.commit()
                print("Employee Auto Deduction created successfully!")
            else:
                transaction.rollback(sid)
                print("Dry Run!")
        except Exception as e:
            print(f' {e} Error: {traceback.format_exc()}')
            transaction.rollback(sid)

if __name__ == "__main__":
    company_name = sys.argv[2]
    clocks = attendance_models.EmployeeCheckInOutDetails.objects.filter(
        employee__company__company_name=company_name,
        date_of_checked_in=timezone_now().date(),#datetime.datetime.now().date(),
        employee__assignedattendancerules__attendance_rule__auto_deduction=True
    )
    if clocks.exists():
        AutoDeductionDailyRun().main(clocks)
        clocks.filter(autodeductionhistory__isnull=True, time_in__date=timezone_now().date(), employee__assignedattendancerules__attendance_rule__auto_deduction=True).update(status="P")

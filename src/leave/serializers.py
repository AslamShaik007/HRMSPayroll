import logging
import math
import json
from datetime import timedelta
import calendar
from datetime import timedelta, datetime
from decimal import Decimal
import traceback

from django.db.models import FloatField, Sum, Q
from django.db.models.functions import Cast
from django.db import transaction
from dateutil.relativedelta import relativedelta
from rest_framework import serializers
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework import status as rest_status

from attendance.services import fetch_attendace_rule_start_end_dates, get_monthly_record_obj_month, custom_is_day_type

from attendance.models import AttendanceRuleSettings,EmployeeCheckInOutDetails, EmployeeMonthlyAttendanceRecords
from core.smtp import send_email
from core.utils import (
    email_render_to_string, get_month_weeks, timezone_now, get_month_pay_cycle_start_end_dates
)
from core.whatsapp import WhatsappMessage

from directory.models import Employee, EmployeeReportingManager, ManagerType, SessionYear
from leave.services import get_accruel_leaves, is_day_type
from pss_calendar.models import Holidays
from django.db.models import Sum

from .models import (
    EmployeeLeaveRuleRelation,
    EmployeeWorkRuleRelation,
    LeaveRules,
    LeavesHistory,
    WorkRuleChoices,
    WorkRules,
)
from HRMSApp.utils import Util
from alerts.utils import check_alert_notification


logger = logging.getLogger(__name__)


class WorkRuleChoicesSerializer(serializers.ModelSerializer):
    """
    Work Rule Choices Serializer

    SURESH, 13.02.2023
    """

    class Meta:
        model = WorkRuleChoices
        fields = (
            "id",
            "work_rule",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "week_number",
        )
        validators = []  # * To handle unique_together validation
        extra_kwargs = {
            "id": {"required": False, "read_only": False},
            "work_rule": {"required": False},
        }


class WorkRuleChoicesDetailSerializer(serializers.ModelSerializer):
    """
    Work Weeek Rules Serializer

    SURESH, 13.02.2023
    """

    class Meta:
        model = WorkRuleChoices
        fields = (
            "id",
            "work_rule",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "week_number",
        )


class WorkRulesSerializer(serializers.ModelSerializer):
    """
    Work Rules Serializer

    SURESH, 13.02.2023
    AJAY, 20.02.2023
    """

    no_of_employees = serializers.SerializerMethodField(read_only=True)
    rule_choices = WorkRuleChoicesSerializer(required=False, many=True)

    class Meta:
        model = WorkRules
        fields = (
            "id",
            "company",
            "name",
            "description",
            "is_default",
            "is_deleted",
            "no_of_employees",
            "rule_choices",
        )
        extra_kwargs = {
            "id": {"read_only": True},
            "description": {"required": False},
            "is_default": {"required": False},
            "name": {"required": False},
            "is_deleted": {"required": False},
        }

    def get_no_of_employees(self, obj):
        return EmployeeWorkRuleRelation.objects.filter(work_rule=obj).count()

    def create(self, validated_data):
        if "name" not in validated_data:
            if latest_rule_name := WorkRules.objects.filter(
                name__startswith="Custom Rule_"
            ).values_list("name", flat=True):
                validated_data[
                    "name"
                ] = f"Custom Rule_{int(latest_rule_name[0][-1]) + 1}"
            else:
                validated_data["name"] = "Custom Rule_1"

        choices = validated_data.pop("rule_choices", [])
        work_rule = super().create(validated_data)

        WorkRuleChoices.objects.bulk_create(
            [WorkRuleChoices(work_rule=work_rule, **choice) for choice in choices]
        )

        return work_rule

    def validate(self, data):
        # name = data.get('name') 
        # if  WorkRules.objects.filter(name=name).exists():
        #         raise serializers.ValidationError(
        #         "{name} is already Exists")
        
        if (
            data.get("is_deleted", False)
            and self.instance
            and EmployeeWorkRuleRelation.objects.filter(
                work_rule=self.instance
            ).exists()
        ):
            raise serializers.ValidationError(
                "Cannot be deleted, its assign to an employee"
            )
        return data

    def update(self, instance, validated_data):
        rule_choices = validated_data.pop("rule_choices", [])
        try:
            for rule_choice in rule_choices:
                rule_choice["work_rule"] = instance
                # WorkRuleChoices.objects.update_or_create(
                #     id=rule_choice.pop("id", None), defaults=rule_choice
                # )
                wr_id = rule_choice.get('id','')
                if wr_id:
                    WorkRuleChoices.objects.filter(id=rule_choice.pop("id")).update(**rule_choice)
                else:
                    WorkRuleChoices.objects.create(**rule_choice)
        except Exception as e:
            result = {"status": HTTP_400_BAD_REQUEST, "data": e}
            raise serializers.ValidationError(result) from e

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result["rule_choices"] = WorkRuleChoicesSerializer(
            instance.work_rule_choices, many=True
        ).data
        return result


class WorkRulesDetailSerializer(serializers.ModelSerializer):
    """
    Work Weeek Rules Serializer

    SURESH, 13.02.2023
    """

    work_rule_choices = WorkRuleChoicesSerializer(many=True)
    no_of_employees = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WorkRules
        fields = (
            "id",
            "company",
            "name",
            "description",
            "is_default",
            "no_of_employees",
            "work_rule_choices",
        )

    def get_no_of_employees(self, obj):
        return EmployeeWorkRuleRelation.objects.filter(work_rule=obj).count()


class EmployeeWorkRuleRelationSerializer(serializers.ModelSerializer):
    """
    Employee Work Rule Relation Serailizer

    AJAY, 21.02.2023
    """

    employee_data = serializers.SerializerMethodField()
    work_rule_data = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeWorkRuleRelation
        fields = (
            "id",
            "employee",
            "work_rule",
            "effective_date",
            "is_deleted",
            "employee_data",
            "work_rule_data",
        )
        extra_kwargs = {
            "id": {"read_only": True},
            "is_deleted": {"required": False},
            "employee": {"write_only": True},
            "work_rule": {"write_only": True},
        }

    def get_employee_data(self, obj):
        employee = obj.employee
        department = employee.work_details.department
        employee_type = employee.work_details.employee_type
        return {
            "id": employee.id,
            "name": employee.name,
            "department": department.name if department else " ",
            "location": employee.work_details.work_location or " ",
            "type": employee_type.get_employee_type_display() if employee_type else " ",
        }

    def get_work_rule_data(self, obj):
        no_of_employees = EmployeeWorkRuleRelation.objects.filter(
            work_rule=obj.work_rule
        ).count()
        return {
            "relation_id": obj.id,
            "id": obj.work_rule.id,
            "name": obj.work_rule.name,
            "no_of_employees": no_of_employees,
        }


class EmployeeWorkRuleRelationDetailSerializer(serializers.Serializer):
    employee_data = serializers.SerializerMethodField()
    work_rule_data = serializers.SerializerMethodField()

    class Meta:
        fields = ("employee_data", "work_rule_data")

    def get_employee_data(self, obj):
        try:
            work_details = obj.work_details
            department = work_details.department if work_details else None
            employee_type = work_details.employee_type if work_details else None
            return {
                "id": obj.id,
                "emp_id": work_details.employee_number if work_details else " ",
                "name": obj.name,
                "department": department.name if department else " ",
                "location": work_details.work_location if work_details else " ",
                "type": employee_type.get_employee_type_display()
                if employee_type
                else " ",
            }
        except Exception:
            logger.warn(
                f"Employee {obj} with id: {obj.id} don't have work details information."
            )
            return {"id": obj.id, "name": obj.name}

    def get_work_rule_data(self, obj):
        if rel := EmployeeWorkRuleRelation.objects.filter(employee=obj).first():
            no_of_employees = EmployeeWorkRuleRelation.objects.filter(
                work_rule=rel.work_rule
            ).count()
            return {
                "rel_id": rel.id,
                "work_rule_id": rel.work_rule.id,
                "name": rel.work_rule.name,
                # "description": rel.work_rule.description,
                # "effective_date": rel.effective_date,
                "no_of_employees": no_of_employees,
                # "choices": WorkRuleChoicesSerializer(
                #     rel.work_rule.work_rule_choices.all(), many=True
                # ).data,
            }
        else:
            return {}


class EmployeeWorkRuleBulkSerializer(serializers.Serializer):
    """
    Serializesr to make relations between employee and work rules.

    AJAY, l01.03.2023
    """

    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), many=True, required=False
    )
    work_rule = serializers.PrimaryKeyRelatedField(
        queryset=WorkRules.objects.all(), required=False
    )
    effective_date = serializers.DateField(required=False)
    is_deleted = serializers.BooleanField(required=False)

    def create(self, validated_data):
        objs = [
            EmployeeWorkRuleRelation(employee=employee, **validated_data)
            for employee in validated_data.pop("employee", [])
        ]
        try:
            return EmployeeWorkRuleRelation.objects.bulk_create(objs)
        except Exception as e:
            raise serializers.ValidationError(
                {
                    "errors": "one employee can have only one work rule",
                    "status": HTTP_400_BAD_REQUEST,
                }
            ) from e

    def update(self, instance, validated_data):
        # return [
        #     EmployeeWorkRuleRelation.objects.update_or_create(
        #         employee=employee, defaults=validated_data
        #     )
        #     for employee in validated_data.pop("employee", [])
        # ]
        for employee in validated_data.pop("employee", []):
            if EmployeeWorkRuleRelation.objects.filter(employee=employee).exists():
                EmployeeWorkRuleRelation.objects.filter(employee=employee).update(**validated_data)
            else:
                EmployeeWorkRuleRelation.objects.create(employee=employee,**validated_data)
        return None
    
class EmployeeGetWorkRuleRelationSerializer(serializers.ModelSerializer):
    """
    Employee Work_rule relation Serializer

    SURESH, 08.03.2023
    """

    class Meta:
        model = EmployeeWorkRuleRelation
        fields = (
            "employee",
            "work_rule",
            "effective_date",
        )


class EmployeeGetWorkRuleRelationDetailSerializer(serializers.ModelSerializer):
    """
    Employee Work_rule relation detail Serializer

    SURESH, 08.03.2023
    """

    work_rule = WorkRulesDetailSerializer(read_only=True)

    class Meta:
        model = EmployeeWorkRuleRelation
        fields = (
            "employee",
            "work_rule",
            "effective_date",
        )


class LeaveRulesSerializer(serializers.ModelSerializer):
    """
    Leave Types Serializer

    SURESH, 21.02.2023
    """

    no_of_employees = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRules
        fields = (
            "id",
            "company",
            "name",
            "description",
            "leaves_allowed_in_year",
            "weekends_between_leave",
            "holidays_between_leave",
            "creditable_on_accrual_basis",
            "accrual_frequency",
            "accruel_period",
            "allowed_under_probation",
            "carry_forward_enabled",
            "all_remaining_leaves",
            "max_leaves_to_carryforward",
            "continuous_leaves_allowed",
            "max_leaves_allowed_in_month",
            "allow_backdated_leaves",
            "no_of_employees",
            "is_deleted",
            "is_leave_encashment_enabled",
            "all_remaining_leaves_for_encash",
            "max_leaves_to_encash",
            "valid_from",
            "valid_to",
            "includes_check_in_leave"
        )

    def get_no_of_employees(self, obj):
        return EmployeeLeaveRuleRelation.objects.filter(leave_rule=obj).count()


class LeaveRulesDetailSerializer(serializers.ModelSerializer):
    """
    Leave Types Serializer

    SURESH, 21.02.2023
    """

    no_of_employees = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRules
        fields = (
            "id",
            "company",
            "name",
            "no_of_employees",
            "description",
            "leaves_allowed_in_year",
            "weekends_between_leave",
            "holidays_between_leave",
            "creditable_on_accrual_basis",
            "accrual_frequency",
            "accruel_period",
            "allowed_under_probation",
            "carry_forward_enabled",
            "all_remaining_leaves",
            "max_leaves_to_carryforward",
            "continuous_leaves_allowed",
            "max_leaves_allowed_in_month",
            "allow_backdated_leaves",
            "no_of_employees",
            "is_deleted",
            "is_leave_encashment_enabled",
            "all_remaining_leaves_for_encash",
            "max_leaves_to_encash",
            "valid_from",
            "valid_to",
            "includes_check_in_leave"
        )

    def get_no_of_employees(self, obj):
        return EmployeeLeaveRuleRelation.objects.filter(leave_rule=obj).count()

quaterly = {"1":{'Jan', 'Feb', 'Mar'}, "2":{'Apr', 'May', 'Jun'}, "3":{'Jul', 'Aug', 'Sep'}, "4":{'Oct', 'Nov', 'Dec'}}
half_yearly ={"1":{'Jan', 'Feb', 'Mar','Apr', 'May', 'Jun'}, "2":{'Jul', 'Aug', 'Sep','Oct', 'Nov', 'Dec'}}
class EmployeeLeaveRuleRelationSerializer(serializers.Serializer):
    """
    Serializer to make relation between Employee and Leave Rules

    AJAY, 22.02.2023
    """

    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), many=True, required=False
    )
    rules = serializers.PrimaryKeyRelatedField(
        queryset=LeaveRules.objects.all(), many=True, required=False
    )
    effective_date = serializers.DateField(required=False)
    is_deleted = serializers.BooleanField(required=False)
    del_relations = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )

    class Meta:
        fields = ("company", "effective_date", "is_deleted")
    
    # def validated_data(self):
    #     data = super().validated_data
    #     data['session_year'] = SessionYear.objects.get(session_year=timezone_now().year)
    #     return data

    def process_no_of_leaves(self, leave_count):
        fact_val, l_count = math.modf(float(leave_count))
        if fact_val < 0.5:
            return l_count
        elif 0.5 <= fact_val < 1:
            return l_count + 0.5

    def _process_leaves(
        self, employee: Employee, leave_rule: LeaveRules, validated_data: dict
    ):
        # if leave_rule.name == "Maternity Leave" and employee.gender in ["MALE","TRANSGENDER"]:
        #     raise serializers.ValidationError(
        #         {
        #             "errors": f"Employee {employee.name} Gender is Male/Transgender, He cant assign Metarnity Leave",
        #             "status": HTTP_400_BAD_REQUEST,
        #         }
        #     )
        # if leave_rule.name == "Paternity Leave" and employee.gender in ["FEMALE","TRANSGENDER"]:
        #     raise serializers.ValidationError(
        #         {
        #             "errors": f"Employee {employee.name} Gender is Female/Transgender, He cant assign Paternity Leave",
        #             "status": HTTP_400_BAD_REQUEST,
        #         }
        #     )
        # EmployeeLeaveRuleRelation.objects.filter(employee=employee,
        #     leave_rule=leave_rule, is_deleted=True).delete()
        if EmployeeLeaveRuleRelation.objects.filter(employee=employee,leave_rule=leave_rule, is_deleted=False,session_year__session_year=timezone_now().year).exists():
            raise serializers.ValidationError(
                {
                    "errors": "Leave rules are already assigned to employee",
                    "status": HTTP_400_BAD_REQUEST,
                }
            )
        elrr = EmployeeLeaveRuleRelation(
            employee=employee,
            leave_rule=leave_rule,
            **validated_data,
        )
        elrr.session_year = SessionYear.objects.get(session_year=timezone_now().year)
        month = timezone_now().date().month
        year = timezone_now().date().year
        # if leave_rule.name not in ['Maternity Leave', 'Bereavement Leave',
        #                         'Paternity Leave', 'Privileged Leave', 'Marriage Leave', 'Additional Leaves']:
        #     leaves_to_provide = (12 - (employee.date_of_join.month - 1)) * (leave_rule.leaves_allowed_in_year/12)
        # else:
        #     leaves_to_provide = leave_rule.leaves_allowed_in_year
        leaves_to_provide = leave_rule.leaves_allowed_in_year
        leaves_to_provide = self.process_no_of_leaves(leaves_to_provide)
        elrr.earned_leaves = leaves_to_provide
        if leave_rule.creditable_on_accrual_basis:
            doj = employee.date_of_join.replace(day=1)
            effective_date = validated_data['effective_date'].replace(day=1)
            diff_months =  effective_date.month # relativedelta(effective_date, doj).months+1
            creditable_type = leave_rule.accrual_frequency

            leave_rule_in_year = leave_rule.leaves_allowed_in_year
            joining_month = doj.strftime("%b")
            effective_month = validated_data['effective_date'].strftime("%b")

            if creditable_type == "MONTHLY":
                monthly_credit_leaves = leave_rule_in_year / 12
                elrr.earned_leaves = monthly_credit_leaves * diff_months
                leaves_to_provide = monthly_credit_leaves * diff_months

            elif creditable_type == "QUARTERLY":
                quaterly_credit_leaves = leave_rule_in_year / 4
                joining_quarter = {month: key for key, months in quaterly.items() for month in months}.get(joining_month)
                effective_quarter = {month: key for key, months in quaterly.items() for month in months}.get(effective_month)
                diff_quaters = (int(effective_quarter) - int(joining_quarter))+1
                elrr.earned_leaves = quaterly_credit_leaves * diff_quaters
                leaves_to_provide = quaterly_credit_leaves * diff_quaters

            elif creditable_type == "HALF_YEARLY":
                half_year_credit_leaves = leave_rule_in_year / 2
                joining_quarter = {month: key for key, months in half_yearly.items() for month in months}.get(joining_month)
                effective_quarter = {month: key for key, months in half_yearly.items() for month in months}.get(effective_month)
                diff_quaters = (int(effective_quarter) - int(joining_quarter))+1
                elrr.earned_leaves = half_year_credit_leaves * diff_quaters
                leaves_to_provide = half_year_credit_leaves * diff_quaters
            else:
                logger.warning(f"Error while sending email notificaton : {creditable_type}")
            leaves_to_provide = self.process_no_of_leaves(leaves_to_provide)
            elrr.earned_leaves = self.process_no_of_leaves(elrr.earned_leaves)
            
        
        # elif leave_rule.name.lower() == "casual leave":
        #     today = timezone_now().date()
        #     last_day = today + relativedelta(day=31, month=12)
        #     accruel_days = (last_day - today).days
        #     accrued_leaves = get_accruel_leaves(
        #         accruel_days, leave_rule.leaves_allowed_in_year
        #     )
        #     elrr.earned_leaves = accrued_leaves
            
        employee_leaves = LeavesHistory.objects.filter(
            leave_rule=leave_rule,employee=employee,
            status=10, start_date__year=year,end_date__year=year
        ).aggregate(Sum("no_of_leaves_applied"))
        employee_leaves['no_of_leaves_applied__sum'] = employee_leaves['no_of_leaves_applied__sum'] if employee_leaves['no_of_leaves_applied__sum'] else 0
        elrr.remaining_leaves =float(leaves_to_provide) - (float(employee_leaves['no_of_leaves_applied__sum']) if (float(employee_leaves['no_of_leaves_applied__sum']) >= 0) else 0)

        employee_lop = LeavesHistory.objects.filter(
            leave_rule=leave_rule,employee=employee,
            status=20, start_date__year=year, end_date__year=year
            ).aggregate(Sum("no_of_leaves_applied"))
        # elrr.earned_leaves = leave_rule.leaves_allowed_in_year
        if employee_lop.get('no_of_leaves_applied__sum'):
            if  employee_lop['no_of_leaves_applied__sum'] >= 0:
                r_leaves = float(elrr.remaining_leaves)
                r_leaves -= float(employee_lop['no_of_leaves_applied__sum'])
                elrr.remaining_leaves = r_leaves
                

        elrr.extra_data[timezone_now().strftime("%b")] = float(elrr.earned_leaves)
        if leave_rule.creditable_on_accrual_basis:
            elrr.extra_data = {validated_data['effective_date'].strftime("%b") : float(elrr.earned_leaves)}
        return elrr

    def _create_relations(self, validated_data):
        emps = validated_data.pop("employee", [])
        rules = validated_data.pop("rules", [])
        rel_objs = []

        if len(emps) == 1:
            if emps[0].gender in [None, '']:
                met_pet_rules = [rule.name for rule in rules if rule.name in ["Maternity Leave", "Paternity Leave"]]
                if "Maternity Leave" in met_pet_rules or "Paternity Leave" in met_pet_rules:
                    raise serializers.ValidationError(
                        {
                            "errors": f"{emps[0].name.title()} Employee Don't Assign Gender.",
                            "status": HTTP_400_BAD_REQUEST,
                        }
                    )
            for rule in rules:
                if rule.name == "Maternity Leave" and emps[0].gender in ["MALE","TRANSGENDER"]:
                    raise serializers.ValidationError(
                        {
                            "errors": f"Employee {emps[0].name} Gender is {emps[0].gender}, He cant assign Metarnity Leave",
                            "status": HTTP_400_BAD_REQUEST,
                        }
                    )
                if rule.name == "Paternity Leave" and emps[0].gender in ["FEMALE","TRANSGENDER"]:
                    raise serializers.ValidationError(
                        {
                            "errors": f"Employee {emps[0].name} Gender is {emps[0].gender}, She cant assign Paternity Leave",
                            "status": HTTP_400_BAD_REQUEST,
                        }
                    )
        prob_emps = set()       
        for rule in rules:
            for emp in emps:
                probation_period = emp.work_details.probation_period if emp.work_details.probation_period else 0
                date_of_join = emp.date_of_join
                today = timezone_now().date()
                if probation_period is not None and date_of_join:
                    emp_regular = date_of_join + timedelta(days=probation_period)
                    if today >= emp_regular or rule.allowed_under_probation or rule.name in ['Additional Leaves', 'Loss Of Pay']:
                        if rule.name == "Maternity Leave":
                            if emp.gender not in ["MALE","TRANSGENDER",None,'']:
                                rel_objs.append(self._process_leaves(emp, rule, validated_data))
                        elif rule.name == "Paternity Leave":
                            if emp.gender not in ["FEMALE","TRANSGENDER",None,'']:
                                rel_objs.append(self._process_leaves(emp, rule, validated_data))
                        else:
                            rel_objs.append(self._process_leaves(emp, rule, validated_data))
                    else:
                        prob_emps.add(emp.user.username)   
                    # if probation_period != 0 and not rule.allowed_under_probation and today <= emp_regular:
                    #     validated_data['effective_date'] = emp_regular
                
                
        # rel_objs = [
        #     self._process_leaves(emp, rule, validated_data)
        #     for emp in emps
        #     for rule in rules
        # ]
        company_id = emps[0].company.id if emps else 1
        try:
            final_leave_rel_data =  EmployeeLeaveRuleRelation.objects.bulk_create(rel_objs)
        except Exception as e:
            raise serializers.ValidationError(
                {
                    "errors": "Leave rules are already assigned to employee",
                    "status": HTTP_400_BAD_REQUEST,
                }
            ) from e
        my_dict = {}
        if rel_objs:
            for obj in rel_objs:
                if obj.employee.id not in my_dict:
                    my_dict[obj.employee.id] = [obj.leave_rule.name]
                else:
                    my_dict[obj.employee.id].append(obj.leave_rule.name)
        #Emails to employees
        hr_details = Employee.objects.filter(is_deleted=False,work_details__employee_status='Active',roles__name='HR',
        company_id=company_id)
        hr_email = list(hr_details.values_list('official_email',flat=True))
        hr_phone = list(hr_details.values_list('user__phone',flat=True))
        for emp_id in my_dict: 
            leave_rule_names = ','.join(my_dict[emp_id])
            employee = Employee.objects.get(id=emp_id)   
            manager_ins = employee.employee.filter(is_deleted=False, manager_type__manager_type=ManagerType.PRIMARY).first()
            # email to Manager
            domain = self.context.get('domain','')
            logged_in_user = self.context.get('logged_in_user','')
            try:
                man_em_id = manager_ins.manager.work_details.employee_number if not manager_ins.is_multitenant else manager_ins.multitenant_manager_emp_id
                body=f"""
    Hello {manager_ins.manager.user.username.title() if not manager_ins.is_multitenant else manager_ins.multitenant_manager_name} [{man_em_id}],

    I hope this email finds you well. I am writing to inform you about Leave Rules are assigned to {employee.user.username} [{employee.work_details.employee_number}]. 
    
    It's crucial to ensure transparency and clarity in scheduling and attendance management, so I wanted to notify you promptly.
    
    Leave Rules Names : {leave_rule_names}
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},
        
    If you have any questions or need further assistance, please feel free to reach out HR department,

    Thank you for your attention to this matter.

    Thanks & Regards,
    {employee.company.company_name.title()}.
            """
                data={
                        'subject': f'Changes in {employee.user.username} Leave Rules',
                        'body':body,
                        'to_email': manager_ins.manager.official_email if manager_ins.is_multitenant else manager_ins.multitenant_manager_email,
                        'cc':hr_email
                    }
                if check_alert_notification("Leave Management",'Employee Leave Rule Update', email=True): 
                    Util.send_email(data)
            except Exception as e:
                logger.warning(f"Error while sending Email notificaton to RM, for the Employee {employee.user.username} in notifications in Leave Rule Update: {e}")
            # HR & Manager Whatsapp notifications about Working Hours/Shift Timings
            try:
                hr_phone.append(manager_ins.manager.user.phone) if manager_ins.manager.user.phone else hr_phone
                whatsapp_data = {
                                'phone_number': hr_phone,
                                'subject': f'Changes in {employee.user.username} Leave Rules',
                                "body_text1":f"{employee.user.username.title()}'s Leave Rules has been changed",
                                'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                'url': f"{domain}leaveRules",
                                "company_name":employee.company.company_name.title()
                                }
                if check_alert_notification("Leave Management",'Employee Leave Rule Update', whatsapp=True): 
                    WhatsappMessage.whatsapp_message(whatsapp_data)
            except Exception as e:
                logger.warning(f"Error while sending Whatsapp notificaton to RM, for the Employee {employee.user.username} in notifications in Leave Rule Update: {e}") 
            # email to Employee
            try:
                # emp_number = employee.work_details.employee_number
                body=f"""
    Hello {employee.user.username.title()} [{employee.work_details.employee_number}],

    I hope this email finds you well. We wanted to inform you about Leave Rules are assigned
    
    Leave Rules Names : {leave_rule_names}
    
    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},

    Please refer the link for more information {domain}UserApplyLeave

    If you have any concern or changes, please don't hesitate to reach out to your manager or the HR department for clarification.
    
    Thanks & Regards,
    {employee.company.company_name.title()}.
            """
                data={
                        'subject': 'Changes to Your Leave Rules',
                        'body':body,
                        'to_email': employee.official_email,
                        'cc':hr_email
                    }
                if check_alert_notification("Leave Management",'Employee Leave Rule Update', email=True): 
                    Util.send_email(data)
            except Exception as e:
                pass
            
            #Employee Whatsapp notifications about Working Hours/Shift Timings
            try:
                whatsapp_data = {
                                'phone_number': employee.user.phone,
                                'subject': "Changes in Your Leave Rules",
                                "body_text1":"We wanted to inform you about some changes in your Leave Rules",
                                'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                'url': f"{domain}UserApplyLeave",
                                "company_name":employee.company.company_name.title()
                                }
                if check_alert_notification("Leave Management",'Employee Leave Rule Update', whatsapp=True):
                    WhatsappMessage.whatsapp_message(whatsapp_data)
            except Exception as e:
                logger.warning(f"Error while sending Whatsapp notificaton to {employee.user.username} in notifications in Leave Rule Update: {e}") 
        if prob_emps:
            raise serializers.ValidationError(
                {
                    "errors": f"Leave rules are not assigned to {','.join(prob_emps)} due to Probtion Period",
                    "status": HTTP_400_BAD_REQUEST,
                }
            )
        return final_leave_rel_data

    def create(self, validated_data):
        # if gen_null_objs := Employee.objects.filter(Q(id__in=[em.id for em in validated_data.get('employee', [])]) & ~(Q(gender='FEMALE')|Q(gender='MALE')|Q(gender='TRANSGENDER')|Q(roles__name='ADMIN'))):
        #     raise serializers.ValidationError(
        #         {
        #             "error": f"{', '.join(gen_null_objs.values_list('first_name', flat=True))} Employee's Dont Assign Gender."
        #         }
        #     )
        return self._create_relations(validated_data)

    def update(self, instance, validated_data):
        del_relations = validated_data.pop("del_relations", [])

        emps = [i.id for i in validated_data.pop('employee', [])]

        rules = [i.id for i in validated_data.pop('rules', [])]
        if LeaveRules.objects.filter(name='Loss Of Pay', company_id=Employee.objects.filter(id__in=emps).first().company.id).values_list('id', flat=True).first() in rules:
            raise serializers.ValidationError(
                {
                    "errors": "Cant remove Loss of pay to employee"
                }
            )
        if LeaveRules.objects.filter(name='Additional Leaves', company_id=Employee.objects.filter(id__in=emps).first().company.id).values_list('id', flat=True).first() in rules:
            raise serializers.ValidationError(
                {
                    "errors": "Cant remove Additional Leaves to employee"
                }
            )
        EmployeeLeaveRuleRelation.objects.filter(employee_id__in=emps, leave_rule_id__in=rules).exclude(leave_rule__name='Loss Of Pay').update(is_deleted=True)
        return self._create_relations(validated_data)


class EmpLeaveRuleRelationDetailSerializer(serializers.Serializer):
    """
    Get all employees leave rules

    AJAY, 22.02.2023
    """

    employee_data = serializers.SerializerMethodField()
    reporting_manager = serializers.SerializerMethodField()
    leave_rule_data = serializers.SerializerMethodField()

    class Meta:
        fields = ("employee_data", "leave_rule_data")

    def get_employee_data(self, obj):
        try:
            work_details = obj.work_details
            department = work_details.department if work_details else None
            sub_department = work_details.sub_department if work_details else None
            designation = work_details.designation if work_details else None
            employee_type = work_details.employee_type if work_details else None
            
            return {
                "id": obj.id,
                "name": obj.name,
                "gender":obj.gender,
                "emp_id": work_details.employee_number,
                "department": department.name if department else " ",
                "sub_department": sub_department.name if sub_department else " " ,
                "designation": designation.name if designation else " ",
                "location": work_details.work_location if work_details else " ",
                "date_of_joining": obj.date_of_join,
                "type": employee_type.get_employee_type_display()
                if employee_type
                else " ",
            }
        except Exception:
            logger.warn(
                f"Employee {obj} with id: {obj.id} don't have work details information."
            )
            return {"id": obj.id, "name": obj.name}

    def get_leave_rule_data(self, obj):
        rels = EmployeeLeaveRuleRelation.objects.filter(employee=obj)
        return [
            {
                "rel_id": rel.id,
                "leave_rule_id": rel.leave_rule.id,
                "name": rel.leave_rule.name,
                "no_of_employees": EmployeeLeaveRuleRelation.objects.filter(
                    leave_rule=rel.leave_rule
                ).count(),
                "remaining_leaves": rel.remaining_leaves,
                "earned_leaves": rel.earned_leaves,
                "used_leaves": rel.used_so_far,
            }
            for rel in rels
        ]

    def get_reporting_manager(self, obj):
        manager = EmployeeReportingManager.objects.filter(
            employee=obj.id,
            is_deleted=False,
            manager_type__manager_type=ManagerType.PRIMARY,
        )
        if manager.exists():
            manager = manager[0]
            if manager.is_multitenant:
                return { "name" : manager.multitenant_manager_name }
            else:
                if manager.manager:
                    return {"name" : manager.manager.name }
                else:
                    return None
        else:
            return None


class LeavesHistorySerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    leave_rule_name = serializers.SerializerMethodField()
    approver = serializers.CharField(
        required=False,
        write_only=True,
    )
    approved_by = serializers.SerializerMethodField()

    class Meta:
        model = LeavesHistory
        fields = (
            "id",
            "employee",
            "leave_rule",
            "leave_rule_name",
            "department",
            "start_date",
            "start_day_session",
            "end_date",
            "end_day_session",
            "reason",
            "reason_for_rejection",
            "approver",
            "approved_on",
            "approved_by",
            "status",
            "status_display",
            "no_of_leaves_applied",
            "attachment",
            "is_backdated",
            "backdated_approval_reason"
        )
        extra_kwargs = {
            "status": {"required": False},
            "attachment": {"required": False},
            "start_day_session": {"required": False},
            "end_day_session": {"required": False},
            "approved_on": {"required": False},
            "approved_by": {"required": False},
            "is_backdated": {"required": False},
        }

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_department(self, obj):
        return (
            obj.employee.work_details.department.name
            if (obj.employee.work_details and obj.employee.work_details.department)
            else "-"
        )

    def get_leave_rule_name(self, obj):
        return obj.leave_rule.name

    def get_approved_by(self, obj):
        return obj.approved_by.name if obj.approved_by else "-"

    def send_notification(
        self,
        leave: LeavesHistory,
        email: str,
        sub_template: str,
        body_template: str,
        manager: str = " - ",
    ):
        """
        It sends an email to the given email address with the given subject and body templates

        :param leave: LeavesHistory,
        :type leave: LeavesHistory
        :param email: The email address of the recipient
        :type email: str
        :param sub_template: The subject template for the email
        :type sub_template: str
        :param body_template: The template for the body of the email
        :type body_template: str
        :param manager: The manager's name, defaults to  -
        :type manager: str (optional)
        :return: A tuple of the email subject and the email message.

        AJAY, 14.03.2023
        """

        email_context = {
            "leave_type": leave.leave_rule.name,
            "start_date": leave.start_date,
            "end_date": leave.end_date,
            "days": leave.no_of_leaves_applied,
            "notes": leave.reason,
            "status": leave.get_status_display(),
            "employee": leave.employee.name,
            "manager": manager,
        }

        email_subject = email_render_to_string(
            template_name=f"mails/{sub_template}",
            context=email_context,
            strip=True,
        )
        email_message = email_render_to_string(
            template_name=f"mails/{body_template}", context=email_context
        )

        return send_email(email, email_subject, message=email_message)

    def validate(self, data):
        """
        Leave Validations

        AJAY, 27.02.2023
        """
        
        # check weather a absent approval is in pending
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        employee = data.get('employee')
        check_in_data = EmployeeCheckInOutDetails.objects.filter(action_status__in=[10, 20], date_of_checked_in__range = [start_date, end_date], 
                                                                 employee=employee, 
                                                                 absent_period__isnull=False)
        
        message = ''
        if ('start_day_session' and 'end_day_session') not in data and check_in_data.exists():
            message = 'Attendance Approval Is Recorded For The Day'
            
        if 'start_day_session' in data and check_in_data.exists() and check_in_data.first().absent_period != 'Second_Half':
            message = 'Attendance Approval Is Recorded For The Day'
        
        if 'end_day_session' in data and check_in_data.exists() and check_in_data.first().absent_period != 'First_Half':
            message = 'Attendance Approval Is Recorded For The Day'
        
        if message:
            raise serializers.ValidationError(
                {
                    "errors": message,
                    "status": HTTP_400_BAD_REQUEST,
                }
            )
        
        if self.instance and self.instance.status in [
            LeavesHistory.CANCELLED,
            LeavesHistory.REJECTED,
            # LeavesHistory.REVOKED,
        ]:
            raise serializers.ValidationError(
                {
                    "errors": "Leaves already cancelled!",
                    "history": {
                        "id": self.instance.id,
                        "employee": self.instance.employee.name,
                        "leave": self.instance.leave_rule.name,
                    },
                    "status": HTTP_400_BAD_REQUEST,
                }
            )

        if self.instance:
            return data
        start_date = data["start_date"]
        end_date = data["end_date"]
        is_backdated = data.get("is_backdated", False)
        history = LeavesHistory.objects.filter(
            employee=data["employee"],
            # leave_rule=data["leave_rule"],
            end_date__gte=start_date,
            start_date__lte=end_date,
            status=LeavesHistory.PENDING,
            # leave_rule__is_deleted=False,
            # employee__employeeleaverulerelation__is_deleted=False
        )
        employee = data["employee"]
        leave_rule = data["leave_rule"]

        # print("1", start_date > leave_rule.valid_to)
        # TODO add compoff logic if employee wants to apply leave is start date of leave instance is under apply leaves or not.
        if start_date > leave_rule.valid_to:
            raise serializers.ValidationError(
                {
                    "errors": f"Leave Rule: {leave_rule.name} Valid from {leave_rule.valid_from.strftime('%d-%m-%Y')} To {leave_rule.valid_to.strftime('%d-%m-%Y')}",
                    "status": HTTP_400_BAD_REQUEST,
                }
            )
        # print("2", end_date > leave_rule.valid_to)

        if end_date > leave_rule.valid_to:
            raise serializers.ValidationError(
                {
                    "errors": f"Leave Rule: {leave_rule.name} Valid from {leave_rule.valid_from.strftime('%d-%m-%Y')} To {leave_rule.valid_to.strftime('%d-%m-%Y')}",
                    "status": HTTP_400_BAD_REQUEST,
                }
            )
        # print("3", start_date < leave_rule.valid_from, start_date, leave_rule.valid_from)
        if start_date < leave_rule.valid_from:
            raise serializers.ValidationError(
                {
                    "errors": f"Leave Rule: {leave_rule.name} Valid from {leave_rule.valid_from.strftime('%d-%m-%Y')} To {leave_rule.valid_to.strftime('%d-%m-%Y')}",
                    "status": HTTP_400_BAD_REQUEST,
                }
            )
        # print("4", end_date < leave_rule.valid_from, end_date, leave_rule.valid_from)
        if end_date < leave_rule.valid_from:
            raise serializers.ValidationError(
                {
                    "errors": f"Leave Rule: {leave_rule.name} Valid from {leave_rule.valid_from.strftime('%d-%m-%Y')} To {leave_rule.valid_to.strftime('%d-%m-%Y')}",
                    "status": HTTP_400_BAD_REQUEST,
                }
            )
        
        relations = EmployeeLeaveRuleRelation.objects.filter(
            employee=data["employee"], leave_rule=data["leave_rule"], is_deleted=False
        )
        if not relations.exists():
            raise serializers.ValidationError(
                {
                    "errors": f"Leave Rule: {leave_rule.name} Not Assigned to the Employee: {employee.name}",
                    "status": HTTP_400_BAD_REQUEST,
                }
            )
        if not data["employee"].employeeworkrulerelation_set.all().exists():
            raise serializers.ValidationError(
                {"errors": "Employee Dont Have WorkRule", "status": HTTP_400_BAD_REQUEST}
            )
        if employee.date_of_join is None:
            raise serializers.ValidationError(
                {"errors": "Employee Dosen't Have Date of Join",
                "status": HTTP_400_BAD_REQUEST}
            )
        if employee.date_of_join > timezone_now().date():
            raise serializers.ValidationError(
                {"errors": "Employee Cant Apply Leave Before Date of JOIN",
                "status": HTTP_400_BAD_REQUEST}
            )
        
        if history.exists() and self.instance is None:
            raise serializers.ValidationError(
                {"errors": "Leave dates over lapping!", "status": HTTP_400_BAD_REQUEST}
            )
        history = LeavesHistory.objects.filter(
            employee=data["employee"],
            end_date__gte=start_date,
            start_date__lte=end_date,
            status=LeavesHistory.APPROVED,
            # leave_rule__is_deleted=False,
            # employee__employeeleaverulerelation__is_deleted=False
        )
        if history.exists() and self.instance is None:
            raise serializers.ValidationError(
                {"errors": "Leave dates over lapping!", "status": HTTP_400_BAD_REQUEST}
            )
        if employee.date_of_join is None:
            raise serializers.ValidationError(
                {
                    "errors": "Employee Dont have Date Of Joining",
                    "status": HTTP_400_BAD_REQUEST
                }
            )
        if not hasattr(employee, 'work_details'):
            raise serializers.ValidationError(
                {
                    "errors": "Employee Dont have Work Details",
                    "status": HTTP_400_BAD_REQUEST
                }
            )
        if employee.work_details.probation_period is None:
            raise serializers.ValidationError(
                {
                    "errors": "Employee Dont have Probation Period Details",
                    "status": HTTP_400_BAD_REQUEST
                }
            )
        if employee.date_of_join > start_date:
            raise serializers.ValidationError(
                {
                    "errors": "Employee Cant apply leave before joining date.",
                    "status": HTTP_400_BAD_REQUEST
                }
            )
        checked_in = EmployeeCheckInOutDetails.objects.filter(
                        employee = employee,
                        date_of_checked_in__range = [start_date, end_date],
                        anamolies__isnull=True
                    )
        if checked_in.exists() and not leave_rule.includes_check_in_leave:
            if not (data.get('end_day_session') or data.get('start_day_session')):
                raise serializers.ValidationError(
                    {
                        "errors": f"You have already checked in for the day({checked_in.first().date_of_checked_in.strftime('%d-%m-%Y')}), please check Start Date and End Date",
                        "status": HTTP_400_BAD_REQUEST
                    }
                )       
        no_of_leaves_applied = Decimal((end_date - start_date).days + 1)
        relation = relations[0]
        # if leave_rule.name.lower() == "Loss Of Pay".lower():
        #     data["no_of_leaves_applied"] = no_of_leaves_applied
        #     data["relation"] = relation
        #     return data

        if (
            relation.earned_leaves == 0 or relation.remaining_leaves == 0
        ) and not leave_rule.allowed_negative_rules:
            raise serializers.ValidationError("No Leaves Found!")

        today = timezone_now().date()
        if (
            ((today - employee.date_of_join).days)
            <= employee.work_details.probation_period
            and not leave_rule.allowed_under_probation
        ):
            raise serializers.ValidationError(
                "Not allowed to apply leaves during probation period"
            )
        if start_date > end_date:
            raise serializers.ValidationError(
                {
                    "errors": "End Date should be greater than start date",
                    "status": HTTP_400_BAD_REQUEST,
                }
            )
        if not is_backdated:
            if (
                ((start_date < relation.effective_date) or start_date < today) and not leave_rule.allow_backdated_leaves
            ):
                raise serializers.ValidationError(
                    {
                        "errors": "Backdated leaves are not allowed",
                        "status": HTTP_400_BAD_REQUEST,
                    }
                )
        # if start_date < relation.effective_date

        if data.get("start_day_session", " ") in ["FIRST_HALF", "SECOND_HALF"]:
            no_of_leaves_applied -= Decimal(0.5)
        if data.get("end_day_session", " ") in ["FIRST_HALF", "SECOND_HALF"]:
            no_of_leaves_applied -= Decimal(0.5)
        _days_applied = (end_date - start_date).days + 1
        date_weeks = [
            get_month_weeks(start_date + timedelta(days=i), combine=True)
            for i in range(_days_applied)
        ]
        date_weeks = {
            k: [d.get(k) for d in date_weeks if d.get(k)]
            for k in set().union(*date_weeks)
        }

        choices = WorkRuleChoices.objects.filter(
            work_rule__in=EmployeeWorkRuleRelation.objects.filter(
                employee=employee,
                effective_date__lte=start_date,
            ).values_list("work_rule", flat=True),
            week_number__in=date_weeks.keys(),
        )
        for week_number, week_dates in date_weeks.items():
            choice = choices.filter(week_number=week_number).first()
            if is_day_type(
                choice=choice,
                dt_input=start_date,
                work_type=WorkRuleChoices.WEEK_OFF
            ):
                raise serializers.ValidationError(
                    {
                        "error": "Leave Start date cannot be Weekend",
                        "status": HTTP_400_BAD_REQUEST,
                    }
                )
            if is_day_type(
                choice=choice,
                dt_input=end_date,
                work_type=WorkRuleChoices.WEEK_OFF
            ):
                raise serializers.ValidationError(
                    {
                        "error": "Leave End date cannot be Weekend",
                        "status": HTTP_400_BAD_REQUEST,
                    }
                )
            if is_day_type(
                choice=choice,
                dt_input=start_date,
                work_type=WorkRuleChoices.HALF_DAY
            ):
                raise serializers.ValidationError(
                    {
                        "error": "Leave Start date cannot be Weekend",
                        "status": HTTP_400_BAD_REQUEST,
                    }
                )
            if is_day_type(
                choice=choice,
                dt_input=end_date,
                work_type=WorkRuleChoices.HALF_DAY
            ):
                raise serializers.ValidationError(
                    {
                        "error": "Leave End date cannot be Weekend",
                        "status": HTTP_400_BAD_REQUEST,
                    }
                )
        holidays = Holidays.objects.filter(
            company=leave_rule.company, holiday_date__range=[start_date, end_date], is_deleted=False, holiday_type=False)
        if start_date in holidays.values_list("holiday_date", flat=True):
            raise serializers.ValidationError(
                    {
                        "error": "Leave Start date cannot be Holiday",
                        "status": HTTP_400_BAD_REQUEST,
                    }
                )
        if end_date in holidays.values_list("holiday_date", flat=True):
            raise serializers.ValidationError(
                    {
                        "error": "Leave End date cannot be Holiday",
                        "status": HTTP_400_BAD_REQUEST,
                    }
                )
        # handling optional holiday
        dates = [start_date + timedelta(i) for i in range(((end_date + timedelta(1)) - start_date).days)]
        is_optional = []
        for date in dates:
            optional_holidays = Holidays.objects.filter(
                company=leave_rule.company, holiday_date=date, is_deleted=False, holiday_type=True)
            is_optional.append('true' if optional_holidays.exists() else 'false')
        # if is_optional and 'true' in is_optional and data.get('leave_rule').name != 'Optional Holiday':
        #     raise serializers.ValidationError(
        #             {
        #                 "error": "Please Apply Leave From Optional Holiday",
        #                 "status": HTTP_400_BAD_REQUEST,
        #             }
        #         )
        if is_optional and 'false' in is_optional and data.get('leave_rule').name == 'Optional Holiday':
            raise serializers.ValidationError(
                    {
                        "error": "Please Apply Leave From Optional Holiday Date",
                        "status": HTTP_400_BAD_REQUEST,
                    }
                )
        if not ('false' in is_optional):
            no_of_leaves_applied = optional_holidays.count()
            if data.get("start_day_session", " ") in ["FIRST_HALF", "SECOND_HALF"]:
                no_of_leaves_applied -= Decimal(0.5)
            if data.get("end_day_session", " ") in ["FIRST_HALF", "SECOND_HALF"]:
                no_of_leaves_applied -= Decimal(0.5)
            
            
            
        if not leave_rule.holidays_between_leave:
            no_of_leaves_applied -= holidays.count()
        if not leave_rule.weekends_between_leave:
            for week_number, week_dates in date_weeks.items():
                choice = choices.filter(week_number=week_number).first()
                for week_date in week_dates:
                    if is_day_type(
                        choice=choice,
                        dt_input=week_date,
                        work_type=WorkRuleChoices.WEEK_OFF
                    ):
                        no_of_leaves_applied -= 1
                    if is_day_type(
                        choice=choice,
                        dt_input=week_date,
                        work_type=WorkRuleChoices.HALF_DAY
                    ):
                        no_of_leaves_applied -= Decimal(0.5)

        if no_of_leaves_applied == 0:
            raise serializers.ValidationError(
                {
                    "errors": "Leave Start date and End date cannot be Holiday or Weekend",
                    "status": HTTP_400_BAD_REQUEST,
                }
            )
        data["no_of_leaves_applied"] = no_of_leaves_applied
        data["relation"] = relation
        return data

    # @transaction.atomic()
    def create(self, validated_data):
        sid = transaction.set_autocommit(autocommit=False)
        try:
            # print(validated_data)
            # validated_data = {'employee': Employee.objects.get(id=15), 'leave_rule': LeaveRules.objects.get(id=8), 'reason': 'df', 'no_of_leaves_applied': decimal.Decimal('1'),  'status': 20, 'start_date': datetime.date(2024, 2, 13), 'end_date': datetime.date(2024, 2, 13), 'relation': EmployeeLeaveRuleRelation.objects.get(leave_rule_id=8, employee_id=15, session_year=2)}
            domain = self.context.get('domain','')
            validated_data["status"] = LeavesHistory.PENDING
            validated_data.pop("relation", None)
            l_st = validated_data.pop('start_date')
            l_ed = validated_data.pop('end_date')
            employee = validated_data["employee"]
            leave_rule = validated_data['leave_rule']
            emp_cid = employee.company_id
            att_settings = AttendanceRuleSettings.objects.filter(company=emp_cid)
            if att_settings.exists():
                attendance_rule_setting_instance = att_settings.first()
            else:
                raise serializers.ValidationError("attendance rule settings does not exists")
            at_cycle_from = attendance_rule_setting_instance.attendance_input_cycle_from
            at_cycle_to = attendance_rule_setting_instance.attendance_input_cycle_to
            if l_st.strftime('%m') == l_ed.strftime('%m'):
                # at_start_date, at_end_date = get_month_pay_cycle_start_end_dates(at_cycle_from, at_cycle_to, l_st)
                at_end_date = datetime.strptime(f"{l_st.strftime('%Y')}-{l_st.strftime('%m')}-{at_cycle_to}", '%Y-%m-%d')
                at_start_date = datetime.strptime(f"{l_st.strftime('%Y')}-{l_st.month - 1 if 1 < l_st.month else 12}-{at_cycle_from}", '%Y-%m-%d')
            else:
                leave_st_month_end_date = calendar.monthrange(int(l_st.strftime('%Y')), int(l_ed.strftime('%m')))[1]
                leave_ed_month_end_date = calendar.monthrange(int(l_ed.strftime('%Y')), int(l_ed.strftime('%m')))[1]
                try:
                    at_end_date =  datetime.strptime(
                            f"{l_st.strftime('%Y')}-{l_ed.strftime('%m')}-{at_cycle_to}", '%Y-%m-%d'
                        )
                    at_start_date = datetime.strptime(
                            f"{l_st.strftime('%Y')}-{l_st.strftime('%m')}-{at_cycle_from}", '%Y-%m-%d'
                        )
                except:
                    at_end_date =  datetime.strptime(
                            f"{l_st.strftime('%Y')}-{l_ed.strftime('%m')}-{leave_ed_month_end_date}", '%Y-%m-%d'
                        )
                    at_start_date = datetime.strptime(
                            f"{l_st.strftime('%Y')}-{l_st.strftime('%m')}-{leave_st_month_end_date}", '%Y-%m-%d'
                        )
            max_leaves_per_month = leave_rule.max_leaves_allowed_in_month if leave_rule.max_leaves_allowed_in_month else 0
            no_of_leaves_applied = validated_data['no_of_leaves_applied']
            cont_leaves = leave_rule.continuous_leaves_allowed
            attendance_settings = AttendanceRuleSettings.objects.get(company_id=employee.company_id)
            relation = EmployeeLeaveRuleRelation.objects.filter(
                employee=employee, leave_rule=leave_rule, is_deleted=False, session_year__session_year=l_ed.year
            ).first()
            if not relation:
                raise serializers.ValidationError(
                        "leave type is not defined in this year"
                    )
            if max_leaves_per_month != 0:
                months_to_count = (timezone_now().date() - relation.effective_date).days // 30
                leaves_can_be_taken_till_month = (months_to_count) * max_leaves_per_month if (months_to_count) * max_leaves_per_month <= relation.earned_leaves else float(relation.earned_leaves)
                if (months_to_count) == 0:
                    leaves_can_be_taken_till_month = max_leaves_per_month
            else:
                leaves_can_be_taken_till_month = relation.earned_leaves

            leave_list = []
            leave_list.append([l_st])
            for i in range(0, (l_ed - l_st).days+1):
                tmp_day = l_st + timedelta(days=i)
                if tmp_day.day == at_cycle_to:
                    leave_list[-1].append(tmp_day)
                if tmp_day.day == at_cycle_from:
                    leave_list.append([tmp_day])
            leave_list[-1].append(l_ed)
            t_leave_list = []
            for j in leave_list:
                if len(j) > 1:
                    t_leave_list.append(j)

            for dates in t_leave_list:
                start_date = dates[0]
                end_date = dates[1]
                generate_dates_between = lambda start_date, end_date: [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
                dates_to_consider = generate_dates_between(start_date, end_date)
                start_from_day = attendance_settings.attendance_input_cycle_from
                end_of_day = attendance_settings.attendance_input_cycle_to
                if float(validated_data['no_of_leaves_applied']) >= 1.0:
                    no_of_leaves_applied = (dates[1] - dates[0]).days + 1
                else:
                    no_of_leaves_applied = float(validated_data['no_of_leaves_applied']) 
                if start_from_day > start_date.day:
                    month_start_date = start_date.replace(month=start_date.month-1 if start_date.month != 1 else 12 ,
                                                        day=start_from_day, year=start_date.year if start_date.month != 1 else start_date.year - 1)
                    month_end_date = start_date.replace(day=end_of_day)
                else:
                    month_start_date = start_date.replace(day=start_from_day)
                    
                    month_end_date = start_date.replace(month= start_date.month+1 if start_date.month+1 <= 12 else 1, day=end_of_day)
                leaves_taken_till = LeavesHistory.objects.filter(
                    leave_rule=leave_rule,
                    start_date__gte=relation.effective_date,
                    start_date__year=start_date.year,
                    employee = employee,
                    status__in = [10,20],
                )
                if no_of_leaves_applied >= 1.0:
                    _days_applied = no_of_leaves_applied
                    date_weeks = [
                        get_month_weeks(start_date + timedelta(days=i), combine=True)
                        for i in range(_days_applied)
                    ]
                    date_weeks = {
                        k: [d.get(k) for d in date_weeks if d.get(k)]
                        for k in set().union(*date_weeks)
                    }

                    choices = WorkRuleChoices.objects.filter(
                        work_rule__in=EmployeeWorkRuleRelation.objects.filter(
                            employee=employee,
                            effective_date__lte=start_date,
                        ).values_list("work_rule", flat=True),
                        week_number__in=date_weeks.keys(),
                    )
                    if not leave_rule.holidays_between_leave:
                        holidays = Holidays.objects.filter(
                                company=leave_rule.company, holiday_date__range=[start_date, end_date], is_deleted=False, holiday_type=False)
                        for h_date in holidays.values_list('holiday_date', flat=True):
                            filtered_dates = [date_obj for date_obj in dates_to_consider if date_obj != h_date]
                            dates_to_consider = filtered_dates
                        no_of_leaves_applied -= holidays.count()
                    if not leave_rule.weekends_between_leave:
                        filtered_dates = dates_to_consider
                        for week_number, week_dates in date_weeks.items():
                            choice = choices.filter(week_number=week_number).first()
                            
                            for week_date in week_dates:
                                if is_day_type(
                                    choice=choice,
                                    dt_input=week_date,
                                    work_type=WorkRuleChoices.WEEK_OFF
                                ):
                                    no_of_leaves_applied -= 1
                                    filtered_dates = [date_obj for date_obj in dates_to_consider if date_obj != week_date]
                                if is_day_type(
                                    choice=choice,
                                    dt_input=week_date,
                                    work_type=WorkRuleChoices.HALF_DAY
                                ):
                                    no_of_leaves_applied -= Decimal(0.5)
                                    filtered_dates = [date_obj for date_obj in dates_to_consider if date_obj != week_date]
                                dates_to_consider = filtered_dates
                # print(no_of_leaves_applied, "Hiiii")
                if no_of_leaves_applied > relation.remaining_leaves:
                    raise serializers.ValidationError(
                        f"You are Not allowed to apply more than  {relation.remaining_leaves}  leaves"
                    )
                if max_leaves_per_month is not None:
                    leaves_taken_till = (
                        leaves_taken_till.annotate(
                            leaves_int=Cast("no_of_leaves_applied", FloatField()),
                        )
                        .aggregate(Sum("leaves_int"))["leaves_int__sum"]
                    )
                    leaves_taken_till = 0 if leaves_taken_till == None else leaves_taken_till
                    # print(leaves_taken_till)
                    max_leaves_can_taken = float(leaves_can_be_taken_till_month) - float(leaves_taken_till)
                    if max_leaves_per_month > 0 and max_leaves_can_taken < float(no_of_leaves_applied):
                        raise serializers.ValidationError(
                            f" You are Not allowed to apply more than {max_leaves_per_month}  leaves for this month"
                        )
                
                if cont_leaves > 0 and no_of_leaves_applied > cont_leaves:
                    raise serializers.ValidationError(
                        f"You are Not allowed to apply more than  {cont_leaves}  Continous leaves"
                    )
                if leave_rule.name == "Comp Off":
                    dates_can_apply = relation.compoff_added_details
                    temp_no_of_days = no_of_leaves_applied
                    op_dates_can_apply = []
                    for opd in dates_can_apply:
                        op_dates_can_apply.append(json.loads(opd))
                    for opd in op_dates_can_apply :
                        for considering_date in dates_to_consider:
                            # print(2, considering_date, datetime.strptime(opd.get('valid_from'), "%Y-%m-%d").date() <= considering_date <=  datetime.strptime(opd.get('valid_to'), "%Y-%m-%d").date())
                            if datetime.strptime(opd.get('valid_from'), "%Y-%m-%d").date() <= considering_date <=  datetime.strptime(opd.get('valid_to'), "%Y-%m-%d").date():
                                temp_no_of_days -= opd.get('leave_count')
                                # print(3, temp_no_of_days, opd.get('leave_count'))
                                break
                        if temp_no_of_days <= 0:
                            break
                    if temp_no_of_days > 0:
                        op_string = " ".join([f'Valid From: {i["valid_from"]}, Valid To: {i["valid_to"]}, no of leaves can apply: {i["leave_count"]}' for i in op_dates_can_apply])
                        raise serializers.ValidationError(
                            f"7 You Have CompOff leaves in {op_string}"
                        )
                instance = LeavesHistory(**validated_data)
                instance.start_date = start_date
                instance.end_date = end_date
                if instance.no_of_leaves_applied >= 1:
                    instance.no_of_leaves_applied = no_of_leaves_applied
                instance.save()
                # relation = EmployeeLeaveRuleRelation.objects.filter(
                #     employee=instance.employee, leave_rule=instance.leave_rule
                # ).first()
                if instance.leave_rule.name == "Loss Of Pay":
                    relation.used_lop_leaves += instance.no_of_leaves_applied
                    relation.remaining_leaves -= instance.no_of_leaves_applied
                else:
                    relation.remaining_leaves -= instance.no_of_leaves_applied
                    relation.used_so_far += instance.no_of_leaves_applied
                relation.save()
                transaction.commit()
                # Send email Notification to the manager
                try:
                    if manager := EmployeeReportingManager.objects.filter(
                        employee=instance.employee,
                        manager_type__manager_type=ManagerType.PRIMARY,
                        is_deleted=False
                    ).first():
                        man_emp_number = manager.manager.work_details.employee_number
                        body1=f'Hello {manager.manager.name.title()} [{man_emp_number}],\n\n{instance.employee.user.username.title()} has applied for the leave. Connect to your HRMS application to find more details.\n\nLeave Type : {instance.leave_rule.name}\nReference dates : {instance.start_date.strftime("%d-%m-%Y")} to {instance.end_date.strftime("%d-%m-%Y")}\nNo Of Days : {instance.no_of_leaves_applied}\nReason : {instance.reason}\nPlease refer the link for more information {domain}adminLeaveLogs\n\nThanks & Regards,\n{instance.employee.company.company_name.title()}'  
                        body = email_render_to_string(
                                template_name="mails/leave_templates/manager_leave.html", 
                                context={"emp_name":instance.employee.user.username.title(), 
                                            "man_name":manager.manager.user.username.title(),
                                            "leave_rule_name":instance.leave_rule.name, 
                                            "start_date":instance.start_date.strftime("%d-%m-%Y"),
                                            "end_date":instance.end_date.strftime("%d-%m-%Y"),
                                            "no_of_leaves_applied":instance.no_of_leaves_applied,
                                            "reason":instance.reason, "company_name":instance.employee.company.company_name.title(),"domain":domain,
                                            "emp_code":man_emp_number, "employee_code":manager.employee.work_details.employee_number
                                            }
                            )
                        data={
                            'subject':'Leave Requested',
                            'body':body,
                            'to_email':manager.manager.official_email
                        }
                        if check_alert_notification("Leave Management",'Apply Leave', email=True): 
                            Util.send_email(data,is_content_html=True)
                        
                except Exception as e:
                    logger.warning(f"Error while sending email notificaton : {e}")
                
                # Manager Whatsapp notifications
                try:
                    whatsapp_data = {
                                    'phone_number': manager.manager.user.phone,
                                    'subject': 'Leave Requested',
                                    "body_text1":f"{instance.employee.user.username}[{manager.employee.work_details.employee_number}] is requesting to approve leave from {instance.start_date.strftime('%d-%m-%Y')} to {instance.end_date.strftime('%d-%m-%Y')}",
                                    'body_text2': "Login to Bharat Payroll to approve/reject the request",
                                    'url': f"{domain}adminLeaveLogs",
                                    "company_name":instance.employee.company.company_name.title()
                                    }
                    if check_alert_notification("Leave Management",'Apply Leave', whatsapp=True): 
                        WhatsappMessage.whatsapp_message(whatsapp_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to {instance.employee.user.username} in notifications about Leave request: {e}")       
            
                #Send email Notification to the employee
                try:
                    if instance.employee.official_email:
                        emp_code = instance.employee.work_details.employee_number
                        # body=f'Hello Mr/Ms {instance.employee.name},\n\nLeave successfully applied, Connect to your HRMS application to find more details.\n\nLeave Type : {instance.leave_rule.name}\nReference dates : {instance.start_date.strftime("%d-%m-%Y")} to {instance.end_date.strftime("%d-%m-%Y")}\nNo Of Days : {instance.no_of_leaves_applied}\nReason : {instance.reason}\n\nThanks,\n{instance.employee.company.company_name}'  
                        body = email_render_to_string(
                                template_name="mails/leave_templates/employee_leave_applied.html", 
                                context={"emp_name":instance.employee.name.title(), 
                                            "leave_rule_name":instance.leave_rule.name, 
                                            "start_date":instance.start_date.strftime("%d-%m-%Y"),
                                            "end_date":instance.end_date.strftime("%d-%m-%Y"),
                                            "no_of_leaves_applied":instance.no_of_leaves_applied,
                                            "reason":instance.reason, "company_name":instance.employee.company.company_name.title(),
                                            "domain":domain, "emp_code":emp_code
                                            }
                            )
                        data={
                            'subject':'Leave Requested',
                            'body':body,
                            'to_email':instance.employee.official_email
                        }
                        if check_alert_notification("Leave Management",'Apply Leave', email=True): 
                            Util.send_email(data,is_content_html=True)
                except Exception as e:
                    logger.warning(f"Error while sending email notificaton : {e}")
                
                # employee Whatsapp notifications
                try:
                    whatsapp_data = {
                                        'phone_number': instance.employee.user.phone,
                                    'subject': 'Leave Requested',
                                    "body_text1":f"You have successfully applied leaves from {instance.start_date.strftime('%d-%m-%Y')} to {instance.end_date.strftime('%d-%m-%Y')}",
                                    'body_text2': " ",
                                    'url': f"{domain}userLeaveLogsTable",
                                    "company_name":instance.employee.company.company_name.title()
                                    }
                    if check_alert_notification("Leave Management",'Apply Leave', whatsapp=True): 
                        WhatsappMessage.whatsapp_message(whatsapp_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to {instance.employee.user.username} in notifications about Leave apply: {e}")   
                
                
                #Send email Notification to the HR to Inform About BAckdated Leaves
                if instance.is_backdated:
                    try:
                        hr_emails = list(Employee.objects.filter(roles__name ='HR', work_details__employee_status='Active'
                                                    ).values('official_email','user__username','work_details__employee_number','user__phone'))
                        for data in hr_emails:
                            hr_email = data['official_email']
                            hr_name = data['user__username']
                            hr_emp_code = data['work_details__employee_number']
                            emp_code = instance.employee.work_details.employee_number
                            body = email_render_to_string(
                                template_name="mails/leave_templates/manager_leave.html", 
                                context={"emp_name":instance.employee.user.username.title(), 
                                            "hr_name":hr_name.title(),
                                            "leave_rule_name":instance.leave_rule.name, 
                                            "start_date":instance.start_date.strftime("%d-%m-%Y"),
                                            "end_date":instance.end_date.strftime("%d-%m-%Y"),
                                            "no_of_leaves_applied":instance.no_of_leaves_applied,
                                            "reason":instance.reason, "company_name":instance.employee.company.company_name.title(),"domain":domain,
                                            "hr_emp_code":hr_emp_code, "employee_code":emp_code
                                            }
                            )
                            data={
                                'subject':f'Backdated Leave Requested By:- {instance.employee.user.username.title()} [{emp_code}]',
                                'body':body,
                                'to_email':hr_email
                            }
                            if check_alert_notification("Leave Management",'Backdated Leave Apply', email=True): 
                                Util.send_email(data,is_content_html=True)
                            #Send whstapp Notification to the HR to Inform About BAckdated Leaves
                            try:
                                whatsapp_data = {
                                                'phone_number': data['user__phone'],
                                                'subject': f'Backdated Leave Requested By:- {instance.employee.user.username.title()} [{emp_code}]',
                                                "body_text1":f"{instance.employee.user.username.title()} [{emp_code}] has applied for the backdated leave",
                                                'body_text2': f"from {instance.start_date.strftime('%d-%m-%Y')} to {instance.end_date.strftime('%d-%m-%Y')}",
                                                'url': f"{domain}adminLeaveLogs",
                                                "company_name":instance.employee.company.company_name.title()
                                                }
                                if check_alert_notification("Leave Management",'Backdated Leave Apply', whatsapp=True): 
                                    WhatsappMessage.whatsapp_message(whatsapp_data)
                            except Exception as e:
                                logger.warning(f"Error while sending Whatsapp notificaton to {instance.employee.user.username} in notifications about Backdated Leave apply: {e}") 
                    except Exception as e:
                        logger.warning(f"Error while sending email notificaton to HR about Backdated Leave apply: {e}")

            return instance
        except Exception as e:
            transaction.rollback(sid)
            raise serializers.ValidationError(f'{e} Error: {traceback.format_exc()}')

    @transaction.atomic()
    def update(self, instance, validated_data):
        # sid = transaction.set_autocommit(autocommit=False)
        try:
            # print(validated_data)
            domain = self.context.get('domain','')
            relation = EmployeeLeaveRuleRelation.objects.filter(
                employee=instance.employee, leave_rule=instance.leave_rule
            )
            if not relation.exists():
                raise serializers.ValidationError({
                        "errors": f"Leave Rule: {instance.leave_rule.name} Not Assigned to the Employee: {instance.employee.name}",
                        "status": HTTP_400_BAD_REQUEST,
                })
            status_check = int(validated_data.get('status', 0))
            relation = relation.first()
            if status_check in [30, 50] and instance.status == 10:
                if timezone_now().date() > instance.start_date:
                    raise serializers.ValidationError(
                        {
                            "errors": "Leave Is already approved and Taken date is over Cant cancle Now.",
                            "status": HTTP_400_BAD_REQUEST
                        }
                    )
            attendance_start_day, attendace_end_day = fetch_attendace_rule_start_end_dates(instance.employee.company_id)
            if (
                validated_data.get("status", LeavesHistory.PENDING)
                == LeavesHistory.CANCELLED
            ):
                # print("Coming Here Canclled")
                if instance.leave_rule.name == "Loss Of Pay":
                    relation.used_lop_leaves -= instance.no_of_leaves_applied
                no_of_leaves_for_rule = instance.employee.employeeleaverulerelation_set.filter(leave_rule=instance.leave_rule).first().earned_leaves
                if no_of_leaves_for_rule > relation.remaining_leaves + instance.no_of_leaves_applied:
                    relation.remaining_leaves += instance.no_of_leaves_applied
                else:
                    relation.remaining_leaves = no_of_leaves_for_rule
                    
                relation.used_so_far = relation.used_so_far - instance.no_of_leaves_applied if relation.used_so_far - instance.no_of_leaves_applied > 0 else 0
                relation.save()
                if instance.status == LeavesHistory.APPROVED:
                    # print("Coming inside Approved")
                    for dt_chk in list(range((instance.end_date - instance.start_date).days + 1)):
                        try:
                            date_of_checked_in = (instance.start_date + timedelta(days=dt_chk))
                            check_month = get_monthly_record_obj_month(attendance_start_day, attendace_end_day, date_of_checked_in)
                            week_number = get_month_weeks(date_of_checked_in)[date_of_checked_in.day]
                            week_off = custom_is_day_type(week_number, 0, date_of_checked_in, instance.employee)
                            holiday = Holidays.objects.filter(holiday_date=date_of_checked_in, company_id=instance.employee.company_id, holiday_type=False)
                            month_record_obj, is_created = EmployeeMonthlyAttendanceRecords.objects.get_or_create(
                                employee_id=instance.employee.id, year=date_of_checked_in.year, month=check_month
                            )
                            l_data = month_record_obj.attendance_data
                            if l_data.get(str(date_of_checked_in)):
                                del l_data[str(date_of_checked_in)]
                            penalty_data = month_record_obj.penalty_details
                            if penalty_data[str(date_of_checked_in)]:
                                del penalty_data[str(date_of_checked_in)]
                            month_record_obj.attendance_data = l_data
                            month_record_obj.penalty_details = penalty_data
                            if instance.leave_rule.name == "Additional Leaves":
                                # print("P1")
                                month_record_obj.lop_count -= 0.5 if float(instance.no_of_leaves_applied) < 0 else 1
                            elif not ((not instance.leave_rule.weekends_between_leave and week_off) or (not instance.leave_rule.holidays_between_leave and holiday.exists())):
                                # print("P2")
                                month_record_obj.leaves_count -= 0.5 if float(instance.no_of_leaves_applied) < 0 else 1.0
                            month_record_obj.save()
                        except Exception as e:
                            logger.info(f'{traceback.format_exc()} Error: {e}')
                
            elif (
                validated_data.get("status", LeavesHistory.PENDING)
                == LeavesHistory.APPROVED
            ):
                # print("Coming Approved")
                # if instance.leave_rule.name == "Loss Of Pay":
                #     relation.used_lop_leaves += instance.no_of_leaves_applied
                # else:
                # print("Coming Here 2")
                if instance.status != 50:
                    # print("Coming inside Not Revoke")
                    validated_data["approved_on"] = timezone_now()
                    for dt_chk in list(range((instance.end_date - instance.start_date).days + 1)):
                        try:
                            date_of_checked_in = (instance.start_date + timedelta(days=dt_chk))
                            check_month = get_monthly_record_obj_month(attendance_start_day, attendace_end_day, date_of_checked_in)
                            week_number = get_month_weeks(date_of_checked_in)[date_of_checked_in.day]
                            week_off = custom_is_day_type(week_number, 0, date_of_checked_in, instance.employee)
                            holiday = Holidays.objects.filter(holiday_date=date_of_checked_in, company_id=instance.employee.company_id, holiday_type=False)
                            month_record_obj, is_created = EmployeeMonthlyAttendanceRecords.objects.get_or_create(
                                employee_id=instance.employee.id, year=date_of_checked_in.year, month=check_month
                            )
                            if is_created:
                                month_record_obj.penalty_details = {}
                            month_record_obj.attendance_data[str(date_of_checked_in)] = {
                                'breaks': None,
                                'reason': instance.reason,
                                'status': 'L',
                                'time_in': None,
                                'time_out': None,
                                'anamolies': {'count': 0},
                                'present_count': 0,
                                'work_duration': None,
                                'break_duration': None,
                                'over_time_data': None,
                                'approval_status': 'Approved'
                            }
                            if instance.leave_rule.name == "Additional Leaves":
                                month_record_obj.lop_count +=  0.5 if float(instance.no_of_leaves_applied) < 0 else 1
                            else:
                                month_record_obj.leaves_count +=  0.5 if float(instance.no_of_leaves_applied) < 0 else 1
                            penalty_data = month_record_obj.penalty_details
                            penalty_data[str(date_of_checked_in)] = {
                                "reason":  instance.reason,
                                "no_of_days_deducted": 0.5 if float(instance.no_of_leaves_applied) < 0 else 1,
                                "deducted_from": instance.leave_rule.name
                            }
                            if not instance.leave_rule.weekends_between_leave and week_off:
                                month_record_obj.attendance_data[str(date_of_checked_in)] = {
                                    'breaks': None,
                                    'reason': 'Week OFF',
                                    'status': 'WO',
                                    'time_in': None,
                                    'time_out': None,
                                    'anamolies': {'count': 0},
                                    'present_count': 0,
                                    'work_duration': None,
                                    'break_duration': None,
                                    'over_time_data': None,
                                    'approval_status': ''
                                }
                                if penalty_data[str(date_of_checked_in)]:
                                    del penalty_data[str(date_of_checked_in)]
                                month_record_obj.leaves_count -=  0.5 if float(instance.no_of_leaves_applied) < 0 else 1
                            elif not instance.leave_rule.holidays_between_leave and holiday.exists():
                                month_record_obj.attendance_data[str(date_of_checked_in)] = {
                                    'breaks': None,
                                    'reason': holiday.first().holiday_name,
                                    'status': 'H',
                                    'time_in': None,
                                    'time_out': None,
                                    'anamolies': {'count': 0},
                                    'present_count': 0,
                                    'work_duration': None,
                                    'break_duration': None,
                                    'over_time_data': None,
                                    'approval_status': ''
                                }
                                if penalty_data[str(date_of_checked_in)]:
                                    del penalty_data[str(date_of_checked_in)]
                                month_record_obj.leaves_count -=  0.5 if float(instance.no_of_leaves_applied) < 0 else 1
                            month_record_obj.penalty_details = penalty_data
                            month_record_obj.save()
                            logger.info(month_record_obj.attendance_data)
                        except Exception as e:
                            logger.info(f'{traceback.format_exc()} Error: {e}')
                else:
                    # print("Coming inside Revoked")
                    validated_data['status'] = LeavesHistory.CANCELLED
                    relation.remaining_leaves += instance.no_of_leaves_applied
                    relation.used_so_far -= instance.no_of_leaves_applied
                    
                    for dt_chk in list(range((instance.end_date - instance.start_date).days + 1)):
                        try:
                            date_of_checked_in = (instance.start_date + timedelta(days=dt_chk))
                            check_month = get_monthly_record_obj_month(attendance_start_day, attendace_end_day, date_of_checked_in)
                            week_number = get_month_weeks(date_of_checked_in)[date_of_checked_in.day]
                            week_off = custom_is_day_type(week_number, 0, date_of_checked_in, instance.employee)
                            holiday = Holidays.objects.filter(holiday_date=date_of_checked_in, company_id=instance.employee.company_id, holiday_type=False)
                            month_record_obj, is_created = EmployeeMonthlyAttendanceRecords.objects.get_or_create(
                                employee_id=instance.employee.id, year=date_of_checked_in.year, month=check_month
                            )
                            l_data = month_record_obj.attendance_data
                            penalty_data = month_record_obj.penalty_details
                            if l_data.get(str(date_of_checked_in)):
                                del l_data[str(date_of_checked_in)]
                            if penalty_data[str(date_of_checked_in)]:
                                del penalty_data[str(date_of_checked_in)]
                            month_record_obj.attendance_data = l_data
                            month_record_obj.penalty_details = penalty_data
                            if instance.leave_rule.name == "Additional Leaves":
                                month_record_obj.leaves_count -= 0.5 if float(instance.no_of_leaves_applied) < 0 else 1
                            elif not ((not instance.leave_rule.weekends_between_leave and week_off) or (not instance.leave_rule.holidays_between_leave and holiday.exists())):
                                month_record_obj.leaves_count -= 0.5 if float(instance.no_of_leaves_applied) < 0 else 1.0
                            
                            month_record_obj.save()
                        except Exception as e:
                            logger.info(f'{traceback.format_exc()} Error: {e}')
                relation.save()

            elif (
                validated_data.get("status", LeavesHistory.PENDING)
                == LeavesHistory.REJECTED
            ):
                # print("Coming Rejected")
                if instance.status != 50:
                    # print("Coming Inside not revoked")
                    if instance.leave_rule.name != 'Comp Off':
                        if instance.leave_rule.name == "Loss Of Pay":
                            relation.used_lop_leaves -= instance.no_of_leaves_applied
                        relation.remaining_leaves += instance.no_of_leaves_applied
                        relation.used_so_far -= instance.no_of_leaves_applied
                        relation.save()
                    if instance.status == LeavesHistory.APPROVED:
                        for dt_chk in list(range((instance.end_date - instance.start_date).days + 1)):
                            try:
                                date_of_checked_in = (instance.start_date + timedelta(days=dt_chk))
                                check_month = get_monthly_record_obj_month(attendance_start_day, attendace_end_day, date_of_checked_in)
                                week_number = get_month_weeks(date_of_checked_in)[date_of_checked_in.day]
                                week_off = custom_is_day_type(week_number, 0, date_of_checked_in, instance.employee)
                                holiday = Holidays.objects.filter(holiday_date=date_of_checked_in, company_id=instance.employee.company_id, holiday_type=False)
                                month_record_obj, is_created = EmployeeMonthlyAttendanceRecords.objects.get_or_create(
                                    employee_id=instance.employee.id, year=date_of_checked_in.year, month=check_month
                                )
                                l_data = month_record_obj.attendance_data
                                penalty_data = month_record_obj.penalty_details
                                if l_data.get(str(date_of_checked_in)):
                                    del l_data[str(date_of_checked_in)]
                                if penalty_data[str(date_of_checked_in)]:
                                    del penalty_data[str(date_of_checked_in)]
                                month_record_obj.attendance_data = l_data
                                month_record_obj.penalty_details = penalty_data
                                if instance.leave_rule.name == "Additional Leaves":
                                    month_record_obj.leaves_count -= 0.5 if float(instance.no_of_leaves_applied) < 0 else 1
                                elif not ((not instance.leave_rule.weekends_between_leave and week_off) or (not instance.leave_rule.holidays_between_leave and holiday.exists())):
                                    # print("P1", date_of_checked_in)
                                    month_record_obj.leaves_count -= 0.5 if float(instance.no_of_leaves_applied) < 0 else 1.0

                                month_record_obj.save()
                            except Exception as e:
                                logger.info(f'{traceback.format_exc()} Error: {e}')
                else:
                    # print("Coming inside revoked")
                    validated_data['status'] = 10
                    # for dt_chk in list(range((instance.end_date - instance.start_date).days + 1)):
                    #     try:
                    #         date_of_checked_in = (instance.start_date + timedelta(days=dt_chk))
                    #         check_month = get_monthly_record_obj_month(attendance_start_day, attendace_end_day, date_of_checked_in)
                    #         week_number = get_month_weeks(date_of_checked_in)[date_of_checked_in.day]
                    #         week_off = custom_is_day_type(week_number, 0, date_of_checked_in, instance.employee)
                    #         holiday = Holidays.objects.filter(holiday_date=date_of_checked_in, company_id=instance.employee.company_id)
                    #         month_record_obj, is_created = EmployeeMonthlyAttendanceRecords.objects.get_or_create(
                    #             employee_id=instance.employee.id, year=date_of_checked_in.year, month=check_month
                    #         )
                    #         l_data = month_record_obj.attendance_data
                    #         if l_data.get(str(date_of_checked_in)):
                    #             del l_data[str(date_of_checked_in)]
                    #         month_record_obj.attendance_data = l_data
                    #         if instance.leave_rule.name == "Additional Leaves":
                    #             month_record_obj.leaves_count -= 0.5 if float(instance.no_of_leaves_applied) < 0 else 1
                    #         elif not ((not instance.leave_rule.weekends_between_leave and week_off) or (not instance.leave_rule.holidays_between_leave and holiday.exists())):
                    #             print("P1", date_of_checked_in)
                    #             month_record_obj.leaves_count -= 0.5 if float(instance.no_of_leaves_applied) < 0 else 1.0

                    #         month_record_obj.save()
                    #     except Exception as e:
                    #         logger.info(f'{traceback.format_exc()} Error: {e}')
            # Send email Notification to the employee
            if validated_data.get("status", LeavesHistory.PENDING) == LeavesHistory.REVOKED:
                validated_data['is_revoked'] = True
            status = ''
            emp_code = instance.employee.work_details.employee_number
            manager_name = self.context.get('user_name','')
            # if manager := EmployeeReportingManager.objects.filter(
            #             employee=instance.employee,
            #             manager_type__manager_type=ManagerType.PRIMARY,
            #         ).first():
            #     manager_name = manager.manager.user.username
            if validated_data.get("status") == 10:
                status = 'Approved'
                # body=f'Hello Mr/Ms {instance.employee.name},\n\nYour applied leave has been Approved. Connect to your HRMS application to find more details.\n\nLeave Type : {instance.leave_rule.name}\nLeave for : {instance.no_of_leaves_applied} days\nStart date : {instance.start_date.strftime("%d-%m-%Y")}\nEnd date : {instance.end_date.strftime("%d-%m-%Y")}\n\nThanks,\n{instance.employee.company.company_name}'
                body = email_render_to_string(
                                    template_name="mails/leave_templates/employee_leave_approvals.html", 
                                    context={"emp_name":instance.employee.name,
                                             "status": status,
                                             "leave_rule_name":instance.leave_rule.name, 
                                              "start_date":instance.start_date.strftime("%d-%m-%Y"),
                                              "end_date":instance.end_date.strftime("%d-%m-%Y"),
                                              "no_of_leaves_applied":instance.no_of_leaves_applied,
                                              "company_name":instance.employee.company.company_name,
                                              "domain":domain, "emp_code":emp_code, "manager_name":manager_name
                                              }
                                )
            elif validated_data.get("status") == 40:
                status = 'Rejected'
                rejection_reason = validated_data.get("reason_for_rejection",'')
                # body=f'Hello Mr/Ms {instance.employee.name},\n\nYour applied leave has been Rejected. Connect to your HRMS application to find more details.\n\nLeave Type : {instance.leave_rule.name}\nLeave for : {instance.no_of_leaves_applied} days\nStart date : {instance.start_date.strftime("%d-%m-%Y")}\nEnd date : {instance.end_date.strftime("%d-%m-%Y")}\nReason For Rejection : {rejection_reason}\n\nThanks,\n{instance.employee.company.company_name}' 
                body = email_render_to_string(
                                    template_name="mails/leave_templates/employee_leave_rejected.html", 
                                    context={"emp_name":instance.employee.name,
                                             "status": status,
                                             "leave_rule_name":instance.leave_rule.name, 
                                              "start_date":instance.start_date.strftime("%d-%m-%Y"),
                                              "end_date":instance.end_date.strftime("%d-%m-%Y"),
                                              "no_of_leaves_applied":instance.no_of_leaves_applied,
                                              "reason":rejection_reason,
                                              "company_name":instance.employee.company.company_name,
                                              "domain":domain, "emp_code":emp_code,"manager_name":manager_name
                                              }
                                )
            elif validated_data.get("status") == 30:
                status = 'Cancelled'
                # body=f'Hello Mr/Ms {instance.employee.name},\n\nYour applied leave has been Cancelled. Connect to your HRMS application to find more details.\n\nLeave Type : {instance.leave_rule.name}\nLeave for : {instance.no_of_leaves_applied} days\nStart date : {instance.start_date.strftime("%d-%m-%Y")}\nEnd date : {instance.end_date.strftime("%d-%m-%Y")}\n\nThanks,\n{instance.employee.company.company_name}'
                body = email_render_to_string(
                                    template_name="mails/leave_templates/employee_leave_cancelled.html", 
                                    context={"emp_name":instance.employee.name.title(),
                                             "status": status,
                                             "leave_rule_name":instance.leave_rule.name, 
                                              "start_date":instance.start_date.strftime("%d-%m-%Y"),
                                              "end_date":instance.end_date.strftime("%d-%m-%Y"),
                                              "no_of_leaves_applied":instance.no_of_leaves_applied,
                                              "company_name":instance.employee.company.company_name.title(),
                                              "domain":domain, "emp_code":emp_code
                                              }
                                )
            if status:    
                try:
                    # body=f'Hello Mr/Ms {instance.employee.name},\n\nYour applied leave has been {instance.get_status_display()}. Connect to your HRMS application to find more details.\n\nLeave Type : {instance.leave_rule.name}\nLeave for : {instance.no_of_leaves_applied} days\nStart_date : {instance.start_date}\nEnd_date : {instance.end_date}'
                    data={
                        'subject':f'Leave {status}',
                        'body':body,
                        'to_email':instance.employee.official_email
                    }
                    if check_alert_notification("Leave Management",'Leave Approvals', email=True): 
                        Util.send_email(data, is_content_html=True)
                except Exception as e:
                    logger.warning(f"Error while sending email notificaton : {e}")
                    
                # employee Whatsapp notifications
                try:
                    whatsapp_data = {
                                    'phone_number': instance.employee.user.phone,
                                    'subject': f'Leave {status}',
                                    "body_text1":f"Your applied leave has been {status.lower()} for the dates from {instance.start_date.strftime('%d-%m-%Y')} to {instance.end_date.strftime('%d-%m-%Y')}.",
                                    'body_text2': " ",
                                    'url': f"{domain}userLeaveLogsTable",
                                    "company_name":instance.employee.company.company_name.title()
                                    }
                    if check_alert_notification("Leave Management",'Leave Approvals', whatsapp=True): 
                        WhatsappMessage.whatsapp_message(whatsapp_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to {instance.employee.user.username} in notifications about leave approvals: {e}") 
            op = super().update(instance, validated_data)
            # transaction.commit()
        except Exception as e:
            # transaction.rollback(sid)
            raise e
        return op


class LeavesHistoryDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    designation = serializers.SerializerMethodField()
    leave_rule_name = serializers.SerializerMethodField()
    employee_name = serializers.SerializerMethodField()
    employee_number = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    approved_by = serializers.SerializerMethodField()
    """
    Leave Rule Detail Serializer

    SURESH, 03.06.2023
    """

    class Meta:
        model = LeavesHistory
        fields = (
            "id",
            "employee",
            "employee_name",
            "employee_number",
            "leave_rule_name",
            "department",
            "designation",
            "start_date",
            "start_day_session",
            "end_date",
            "end_day_session",
            "reason",
            "reason_for_rejection",
            "approved_on",
            "approved_by",
            "reason_for_rejection",
            "status",
            "status_display",
            "no_of_leaves_applied",
            "balance",
            "created_at",
        )

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_department(self, obj):
        return (
            obj.employee.work_details.department.name
            if (obj.employee.work_details and obj.employee.work_details.department)
            else "-"
        )

    def get_designation(self, obj):
        return (
            obj.employee.work_details.designation.name
            if (obj.employee.work_details and obj.employee.work_details.designation)
            else "-"
        )

    def get_employee_name(self, obj):
        return obj.employee.name if obj.employee else "-"

    def get_employee_number(self, obj):
        return (
            obj.employee.work_details.employee_number
            if (obj.employee.work_details and obj.employee.work_details.employee_number)
            else "-"
        )

    def get_leave_rule_name(self, obj):
        return obj.leave_rule.name

    def get_balance(self, obj):
        if balance_leaves := EmployeeLeaveRuleRelation.objects.filter(
            leave_rule=obj.leave_rule.id, employee=obj.employee.id
        ):
            return {"balance_leaves": balance_leaves[0].remaining_leaves}

        return {"balance_leaves": "-"}

    def get_approved_by(self, obj):
        return obj.approved_by.name if obj.approved_by else "-"


class EmployeeGetLeaveRuleRelationSerializer(serializers.ModelSerializer):
    """
    Employee LeaveRule Relation Serializer

    SURESH, 07.06.2023
    """

    class Meta:
        model = EmployeeLeaveRuleRelation
        fields = (
            "id",
            "employee",
            "leave_rule",
            "effective_date",
            "remaining_leaves",
            "earned_leaves",
            "used_so_far",
        )


class GetEmployeeLeaveRuleRelationDetailSerializer(serializers.ModelSerializer):
    """
    Employee LeaveRule Relation Serializer

    SURESH, 07.06.2023
    """

    leave_rule = LeaveRulesDetailSerializer(read_only=True)
    monthly_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EmployeeLeaveRuleRelation
        fields = (
            "id",
            "employee",
            "effective_date",
            "remaining_leaves",
            "earned_leaves",
            "used_so_far",
            "penalty_deduction",
            "used_lop_leaves",
            "monthly_data",
            "leave_rule",
        )

    def get_monthly_data(self, obj):
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        extra_data = obj.extra_data or {}
        return {month: extra_data.get(month, 0) for month in months}

# lrs = EmployeeLeaveRuleRelation.objects.using(db_con).filter(session_year__session_year=2024).order_by('leave_rule_id').distinct('leave_rule_id').values_list('leave_rule_id', flat=True)
# LeaveRules.objects.using(db_con).filter(id__in=lrs).update(valid_from='2023-12-21', valid_to='2024-12-20')
# err_d = []

# for elr in EmployeeLeaveRuleRelation.objects.using(db_con).filter(is_deleted=False).exclude(leave_rule__name='Loss Of Pay'):
#     print(elr.earned_leaves, elr)
#     taken_ls = LeavesHistory.objects.using(db_con).filter(employee=elr.employee,leave_rule=elr.leave_rule,status__in=[LeavesHistory.APPROVED, LeavesHistory.PENDING]).aggregate(t_s=Sum('no_of_leaves_applied'))['t_s']
#     print(elr.earned_leaves, taken_ls, elr)
#     if elr.remaining_leaves != elr.earned_leaves - taken_ls if taken_ls else 0:
#         err_d.append(
#             {
#                 'emp': elr.employee.user.username,
#                 'lr': elr.leave_rule.name,
#                 'rem_l': elr.remaining_leaves,
#                 'ori_rem_l': elr.earned_leaves - taken_ls if taken_ls else 0,
#                 'take_l': taken_ls
#             }
#         )
#     elr.remaining_leaves = elr.earned_leaves - taken_ls if taken_ls else 0
#     elr.save()


# for elr in EmployeeLeaveRuleRelation.objects.using(db_con).filter(is_deleted=False).exclude(leave_rule__name='Loss Of Pay'):
#     taken_ls = LeavesHistory.objects.using(db_con).filter(
#         employee=elr.employee,leave_rule=elr.leave_rule,status__in=[LeavesHistory.APPROVED, LeavesHistory.PENDING]
#     ).aggregate(
#         t_s=Sum('no_of_leaves_applied')
#     )['t_s']
#     taken_ls = taken_ls if taken_ls else 0
#     elr.remaining_leaves = elr.earned_leaves - taken_ls
#     elr.save()
#     print(elr.earned_leaves, elr.remaining_leaves, taken_ls, elr)
import logging
from datetime import datetime, timedelta
import decimal
import math
import json

from django.db import transaction

from rest_framework import serializers, status

from HRMSApp.utils import Util

from attendance.models import (
    AnamolyHistory,
    AssignedAttendanceRules,
    AttendanceRules,
    AttendanceRuleSettings,
    EmployeeCheckInOutDetails,
    PenaltyRules, EmployeeMonthlyAttendanceRecords
)
from attendance.services import calculate_work_time, fetch_attendace_rule_start_end_dates, get_monthly_record_obj_month
from core.utils import get_month_weeks, localize_dt, strftime, strptime, mins_to_hrs, hrs_to_mins, timezone_now
from directory.models import Employee, EmployeeReportingManager, ManagerType
from directory.services import get_manager
from leave.models import EmployeeWorkRuleRelation, LeavesHistory, WorkRuleChoices
from leave.services import is_day_type
from pss_calendar.models import Holidays
from HRMSApp.models import CompanyCustomizedConfigurations
from alerts.utils import check_alert_notification
from core.whatsapp import WhatsappMessage

logger = logging.getLogger(__name__)


class PenaltyRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PenaltyRules
        fields = (
            "id",
            "attendance_rule",
            "in_time",
            "late_coming_allowed",
            "in_penalty_interval",
            "in_penalty",
            "in_leave_deduction",
            "out_time",
            "early_leaving_allowed",
            "out_penalty_interval",
            "out_penalty",
            "out_leave_deduction",
            "work_duration",
            "shortfall_in_wd_allowed",
            "work_penalty_interval",
            "work_penalty",
            "work_leave_deduction",
            "outstanding_breaks_penalty",
            "excess_breaks_allowed",
            "break_penalty_interval",
            "break_penalty",
            "break_leave_deduction",
        )


class PenaltyRuleDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PenaltyRules
        fields = (
            "id",
            "attendance_rule",
            "in_time",
            "late_coming_allowed",
            "in_penalty_interval",
            "in_penalty",
            "in_leave_deduction",
            "out_time",
            "early_leaving_allowed",
            "out_penalty_interval",
            "out_penalty",
            "out_leave_deduction",
            "work_duration",
            "shortfall_in_wd_allowed",
            "work_penalty_interval",
            "work_penalty",
            "work_leave_deduction",
            "outstanding_breaks_penalty",
            "excess_breaks_allowed",
            "break_penalty_interval",
            "break_penalty",
            "break_leave_deduction",
        )
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not isinstance(data['in_leave_deduction'], list):
            data["in_leave_deduction"] = []
        if not isinstance(data["out_leave_deduction"], list):
            data["out_leave_deduction"] = []
        if not isinstance(data["work_leave_deduction"], list):
            data["work_leave_deduction"] = []
        if not isinstance(data["break_leave_deduction"], list):
            data["break_leave_deduction"] = []
        return data

class AttendanceRulesSerializer(serializers.ModelSerializer):
    """
    Company AttendenceRules Serializer

    SURESH, 24.02.2023
    """

    penalty_rules = PenaltyRuleDetailsSerializer(
        many=True,
        required=False,
    )
    no_of_employees = serializers.SerializerMethodField()
    attendance_settings = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AttendanceRules
        fields = (
            "id",
            "company",
            "name",
            "description",
            "shift_in_time",
            "shift_out_time",
            "auto_deduction",
            "grace_in_time",
            "grace_out_time",
            "full_day_work_duration",
            "half_day_work_duration",
            "max_break_duration",
            "max_breaks",
            "auto_clock_out",
            "is_default",
            "effective_date",
            "created_at",
            "enable_over_time",
            "enable_attendance_selfie",
            "enable_geo_fencing",
            "location_address",
            "distance",
            "longitude",
            "latitude",
            "is_deleted",
            "enable_comp_off",
            "enable_penalty_rules",
            "enable_anomaly_tracing",
            "no_of_employees",
            "penalty_rules",
            "attendance_settings",
            "comp_off_full_day_work_duration",
            "comp_off_half_day_work_duration",
            "minimum_hours_to_consider_ot",
            "selected_time_zone"
        )
        extra_kwargs = {
            "comp_off_full_day_work_duration": {'required': False},
            "comp_off_half_day_work_duration": {'required': False},
            "minimum_hours_to_consider_ot": {'required': False},
            "selected_time_zone": {"required": False}
        }

    def get_penalty_rules(self, obj):
        try:
            return PenaltyRuleDetailsSerializer(obj.penalty_rules.all(), many=True).data
        except PenaltyRules.DoesNotExist:
            return None
    
    def get_attendance_settings(self, obj):
        try:
            return AttendanceRuleSettings.objects.filter(company_id=obj.company_id).values(
                'attendance_input_cycle_from', 'attendance_input_cycle_to'
            ).first()
        except Exception:
            return None

    def get_no_of_employees(self, obj):
        return AssignedAttendanceRules.objects.filter(attendance_rule=obj).count()

    def create(self, validated_data):
        sid =transaction.set_autocommit(autocommit=False)
        try:
            penalty_rules = validated_data.pop("penalty_rules", [])
            if AttendanceRules.objects.filter(company=validated_data.get('company'), name=validated_data.get('name')).exists():
                raise serializers.ValidationError(
                    {
                        "error": "Attendance Rule Already Exists"
                    }
                ) 
            if not validated_data.get('enable_penalty_rules') and (validated_data.get('auto_deduction') or validated_data.get('enable_anomaly_tracing')):
                transaction.rollback(sid)
                raise serializers.ValidationError(
                    {
                        "error": "If Autodeduction or Anomaly Tracking is Enable, Please Provide Penalty Rule Also"
                    }
                )
            instance = super().create(validated_data)
            if instance.enable_penalty_rules:
                for i in penalty_rules:
                    # PenaltyRules.objects.update_or_create(attendance_rule=instance, defaults=i)
                    if PenaltyRules.objects.filter(attendance_rule=instance).exists():
                        PenaltyRules.objects.filter(attendance_rule=instance).update(**i)
                    else:
                        PenaltyRules.objects.create(attendance_rule=instance, **i)
            transaction.commit()
        except Exception as e:
            transaction.rollback(sid)
            raise e
        return instance

    def update(self, instance, validated_data):
        sid =transaction.set_autocommit(autocommit=False)
        try:
            penalty_rules = validated_data.pop("penalty_rules", [])
            check = super().update(instance, validated_data)
            if not instance.enable_penalty_rules and (instance.auto_deduction or instance.enable_anomaly_tracing):
                transaction.rollback(sid)
                raise serializers.ValidationError(
                    {
                        "error": "If Autodeduction or Anomaly Tracking is Enable, Please Provide Penalty Rule Also"
                    }
                )
            if instance.enable_penalty_rules:
                for i in penalty_rules:
                    # PenaltyRules.objects.update_or_create(attendance_rule=instance, defaults=i)
                    if PenaltyRules.objects.filter(attendance_rule=instance).exists():
                        PenaltyRules.objects.filter(attendance_rule=instance).update(**i)
                    else:
                        PenaltyRules.objects.create(attendance_rule=instance, **i)
            transaction.commit()
        except Exception as e:
            transaction.rollback(sid)
            raise e
        return check

class AttendanceRulesDetailsSerializer(serializers.ModelSerializer):
    """
    Company AttendenceRules Detail Serializer

    SURESH, 24.02.2023
    """

    no_of_employees = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRules
        fields = (
            "id",
            "company",
            "name",
            "no_of_employees",
            "description",
            "shift_in_time",
            "shift_out_time",
            "auto_deduction",
            "grace_in_time",
            "grace_out_time",
            "full_day_work_duration",
            "half_day_work_duration",
            "max_break_duration",
            "max_breaks",
            "auto_clock_out",
            "is_default",
            "effective_date",
            "created_at",
            "enable_over_time",
            "enable_attendance_selfie",
            "enable_geo_fencing",
            "location_address",
            "distance",
            "longitude",
            "latitude",
            "is_deleted",
            "enable_comp_off",
            "enable_penalty_rules",
            "enable_anomaly_tracing",
            "penalty_rules",
        )

    def get_no_of_employees(self, obj):
        return AssignedAttendanceRules.objects.filter(attendance_rule=obj).count()


class AssignedAttendanceRulesSerializer(serializers.ModelSerializer):
    """
    Employee Attendence Rule Relation Serializer

    SURESH, 24.02.2023
    """

    employee_data = serializers.SerializerMethodField()
    attendance_rule_data = serializers.SerializerMethodField()

    class Meta:
        model = AssignedAttendanceRules
        fields = (
            "id",
            "employee",
            "attendance_rule",
            "effective_date",
            "resend_reminder",
            "employee_data",
            "attendance_rule_data",
            "is_deleted",
        )
        extra_kwargs = {
            "id": {"read_only": True},
            "is_deleted": {"required": False},
            "employee": {"write_only": True},
            "attendance_rule_data": {"write_only": True},
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

    def get_attendance_rule_data(self, obj):
        return {"id": obj.attendance_rule.id, "name": obj.attendance_rule.name}


class EmployeeAttendaceRuleRelationSerializer(serializers.Serializer):
    employee_data = serializers.SerializerMethodField()
    reporting_manager = serializers.SerializerMethodField()
    attendance_rule_data = serializers.SerializerMethodField()

    class Meta:
        fields = ("employee_data", "attendance_rule_data")

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
                "emp_id": work_details.employee_number,
                "department": department.name if department else " ",
                "sub_department": sub_department.name if sub_department else " ",
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

    def get_attendance_rule_data(self, obj):
        if rel := AssignedAttendanceRules.objects.filter(employee=obj).first():
            return {
                "rel_id": rel.id,
                "work_rule_id": rel.attendance_rule.id,
                "name": rel.attendance_rule.name,
            }
        else:
            return {}

    def get_reporting_manager(self, obj):
        if manager_details := EmployeeReportingManager.objects.filter(
            employee=obj.id,
            is_deleted=False,
            manager_type__manager_type=ManagerType.PRIMARY,
        ):
            return {"name": manager_details[0].manager.name}

        return {"name": "-"}


class AssignedAttendanceRulesDetailsSerializer(serializers.ModelSerializer):
    """
    Employee Attendence Rule Relation Serializer

    SURESH, 24.02.2023, 17.04.2023
    """

    attendance_rule = AttendanceRulesDetailsSerializer(read_only=True)
    penalty_rule = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AssignedAttendanceRules
        fields = (
            "id",
            "employee",
            "attendance_rule",
            "penalty_rule",
            "effective_date",
            "resend_reminder",
            "is_deleted",
        )

    def get_penalty_rule(self, obj):
        if att_rules := AssignedAttendanceRules.objects.filter(
            employee=obj.employee.id
        ).first():
            rel_id = att_rules.attendance_rule.id
            try:
                if rel := PenaltyRules.objects.filter(attendance_rule=rel_id)[0]:
                    return {
                        "rel_id": rel.id,
                        "in_time": rel.in_time,
                        "late_coming_allowed": rel.late_coming_allowed,
                        "in_penalty_interval": rel.in_penalty_interval,
                        "in_penalty": rel.in_penalty,
                        "in_leave_deduction": rel.in_leave_deduction,
                        "out_time": rel.out_time,
                        "early_leaving_allowed": rel.early_leaving_allowed,
                        "out_penalty_interval": rel.out_penalty_interval,
                        "out_penalty": rel.out_penalty,
                        "out_leave_deduction": rel.out_leave_deduction,
                        "work_duration": rel.work_duration,
                        "shortfall_in_wd_allowed": rel.shortfall_in_wd_allowed,
                        "work_penalty_interval": rel.work_penalty_interval,
                        "work_penalty": rel.work_penalty,
                        "work_leave_deduction": rel.work_leave_deduction,
                        "outstanding_breaks_penalty": rel.outstanding_breaks_penalty,
                        "excess_breaks_allowed": rel.excess_breaks_allowed,
                        "break_penalty_interval": rel.break_penalty_interval,
                        "break_penalty": rel.break_penalty,
                        "break_leave_deduction": rel.break_leave_deduction,
                    }
            except Exception:
                return {}
        else:
            return {}


class EmployeeAttendanceRuleBulkSerializer(serializers.Serializer):
    """
    Serializesr to make relations between employee and attendance rules.

    SURESH, 02.03.2023
    """

    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), many=True, required=False
    )
    attendance_rule = serializers.PrimaryKeyRelatedField(
        queryset=AttendanceRules.objects.all(), required=False
    )
    effective_date = serializers.DateField(required=False)
    is_deleted = serializers.BooleanField(required=False)

    def create(self, validate_data):
        objs = [
            AssignedAttendanceRules(employee=employee, **validate_data)
            for employee in validate_data.pop("employee", [])
        ]
        try:
            return AssignedAttendanceRules.objects.bulk_create(objs)
        except Exception as e:
            raise serializers.ValidationError(
                {"errors": e, "status": status.HTTP_400_BAD_REQUEST}
            ) from e

    def update(self, instance, validated_data):
        # return [
        #     AssignedAttendanceRules.objects.update_or_create(
        #         employee=employee, defaults=validated_data
        #     )
        #     for employee in validated_data.pop("employee", [])
        # ]
        
        for employee in validated_data.pop("employee", []):
            obj = AssignedAttendanceRules.objects.filter(employee=employee)
            existing_att_rule = ''
            if obj.exists():
                existing_att_rule = obj.first().attendance_rule.name
                obj.update(**validated_data)
                obj = obj.first()
            else:
                obj = AssignedAttendanceRules.objects.create(employee=employee, **validated_data)
                
            # Email Content
            hr_query = Employee.objects.filter(is_deleted=False,work_details__employee_status='Active',roles__name='HR',
                    company_id=employee.company.id)
            hr_email =  list(hr_query.values_list('official_email',flat=True))  
            hr_phone =  list(hr_query.values_list('user__phone',flat=True))  
            manager_ins = employee.employee.filter(is_deleted=False, manager_type__manager_type=ManagerType.PRIMARY).first()
            # existing_att_rule = existing_att_rule if existing_att_rule else obj.attendance_rule.name
            new_att_rule = validated_data.get('attendance_rule').name
            # email to Manager
            if existing_att_rule != new_att_rule:
                domain = self.context.get('domain','')
                logged_in_user = self.context.get('logged_in_user','')
                try:
                    man_em_id = manager_ins.manager.work_details.employee_number
                    body=f"""
    Hello {manager_ins.manager.user.username.title()} [{man_em_id}],

    I hope this email finds you well. I wanted to inform you about some changes in the working hours/shift timings of {employee.user.username.title()} [{employee.work_details.employee_number}] to ensure smooth operations.

    Attendacne Rule Name : {obj.attendance_rule.name},
    Attendacne Rule Description : {obj.attendance_rule.description},
    Shift In Time : {obj.attendance_rule.shift_in_time.strftime("%I:%M %p")},
    Shift Out Time : {obj.attendance_rule.shift_out_time.strftime("%I:%M %p")},
    Is Anomaly Tracing Enabled : {obj.attendance_rule.enable_anomaly_tracing},
    Time Zone : {obj.attendance_rule.selected_time_zone},

    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},
        
    Please ensure that your team members are aware of these changes and that they can adjust their schedules accordingly.
    
    If you have any questions or need further assistance, please feel free to reach out the HR department.

    Thanks & Regards,
    {employee.company.company_name.title()}.
                """
                    data={
                            'subject': f"Changes in {employee.user.username}'s Working Hours/Shift Timings",
                            'body':body,
                            'to_email': manager_ins.manager.official_email,
                            'cc':hr_email
                        }
                    if check_alert_notification("Attendance",'Employee Attendance Rule Update', email=True):
                        Util.send_email(data)
                except Exception as e:
                    pass
                #HR-manager Whatsapp notifications about Working Hours/Shift Timings
                try:
                    hr_phone.append(manager_ins.manager.user.phone) if manager_ins.manager.user.phone else hr_phone
                    whatsapp_data = {
                                    'phone_number': hr_phone,
                                    'subject': "Changes in Working Hours/Shift Timings",
                                    "body_text1":f"{employee.user.username.title()}'s working hours/shift timings has been changed",
                                    'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                    'url': f"{domain}attendanceRules",
                                    "company_name":employee.company.company_name.title()
                                    }
                    if check_alert_notification("Attendance",'Employee Attendance Rule Update', whatsapp=True):
                        WhatsappMessage.whatsapp_message(whatsapp_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to {manager_ins.manager.user.username} in notifications about Working Hours/Shift Timings: {e}") 
                # email to Employee
                try:
                    body=f"""
    Hello {employee.user.username.title()} [{employee.work_details.employee_number}],

    I hope this email finds you well. We wanted to inform you about some changes in your working hours/shift timings to ensure that you can plan your schedule accordingly.

    Attendacne Rule Name : {obj.attendance_rule.name},
    Attendacne Rule Description : {obj.attendance_rule.description},
    Shift In Time : {obj.attendance_rule.shift_in_time.strftime("%I:%M %p")},
    Shift Out Time : {obj.attendance_rule.shift_out_time.strftime("%I:%M %p")},
    Is Anomaly Tracing Enabled : {obj.attendance_rule.enable_anomaly_tracing},
    Time Zone : {obj.attendance_rule.selected_time_zone},

    Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime("%I:%M %p")} updated by {logged_in_user.title()},

    Please refer the link for more information {domain}userAttendancelogs

    If you have any concern or changes, please don't hesitate to reach out to your manager or the HR department for clarification.
    
    Thanks & Regards,
    {employee.company.company_name.title()}.
                """
                    data={
                            'subject': 'Changes to Your Working Hours/Shift Timings',
                            'body':body,
                            'to_email': employee.official_email,
                            'cc':hr_email
                        }
                    if check_alert_notification("Attendance",'Employee Attendance Rule Update', email=True):
                        Util.send_email(data)
                except Exception as e:
                    pass    
                #Employee Whatsapp notifications about Working Hours/Shift Timings
                try:
                    whatsapp_data = {
                                    'phone_number': employee.user.phone,
                                    'subject': "Changes in Working Hours/Shift Timings",
                                    "body_text1":"We wanted to inform you about some changes in your working hours/shift timings to ensure that you can plan your schedule accordingly",
                                    'body_text2': f"Effective from {timezone_now().strftime('%d-%m-%Y')} at {timezone_now().strftime('%I:%M %p')}",
                                    'url': f"{domain}userAttendancelogs",
                                    "company_name":employee.company.company_name.title()
                                    }
                    if check_alert_notification("Attendance",'Employee Attendance Rule Update', whatsapp=True):
                        WhatsappMessage.whatsapp_message(whatsapp_data)
                except Exception as e:
                    logger.warning(f"Error while sending Whatsapp notificaton to {employee.user.username} in notifications about Working Hours/Shift Timings: {e}") 
        return None


class AttendanceRuleSettingsSerializer(serializers.ModelSerializer):
    """
    Attendence Rule Setting Serializer

    SURESH, 24.02.2023
    """

    class Meta:
        model = AttendanceRuleSettings
        fields = (
            "id",
            "company",
            "attendance_input_cycle_from",
            "attendance_input_cycle_to",
            "limit_backdated_ar_application",
            "limit_number_of_ar_application_per_month",
            "daily_attendance_report_reminder",
            "late_early_punch_reminder",
            "pending_regularization_reminder",
            "ip_restriction",
            "is_deleted",
            "attendance_start_month",
            "attendance_paycycle_end_date",
            "calendar_type"
        )


class AttendanceRuleSettingsDetailsSerializer(serializers.ModelSerializer):
    """
    Attendence Rule Setting Serializer

    SURESH, 24.02.2023
    """

    class Meta:
        model = AttendanceRuleSettings
        fields = (
            "id",
            "company",
            "attendance_input_cycle_from",
            "attendance_input_cycle_to",
            "limit_backdated_ar_application",
            "limit_number_of_ar_application_per_month",
            "daily_attendance_report_reminder",
            "late_early_punch_reminder",
            "pending_regularization_reminder",
            "ip_restriction",
            "is_deleted",
            "attendance_start_month",
            "attendance_paycycle_end_date",
            "calendar_type",
        )


class CheckInOutSerializer(serializers.ModelSerializer):
    time_in_format = serializers.SerializerMethodField(read_only=True)
    time_out_format = serializers.SerializerMethodField(read_only=True)
    action = serializers.ChoiceField(
        choices=EmployeeCheckInOutDetails.ACTION_CHOICES, required=False
    )
    action_display = serializers.ChoiceField(
        choices=EmployeeCheckInOutDetails.ACTION_CHOICES,
        source="get_action_display",
        read_only=True,
    )
    action_status = serializers.ChoiceField(
        choices=EmployeeCheckInOutDetails.ACTION_STATUS_CHOICES, required=False
    )    
    action_status_display = serializers.ChoiceField(
        choices=EmployeeCheckInOutDetails.ACTION_STATUS_CHOICES,
        source="get_action_status_display",
        read_only=True,
    )
    status = serializers.CharField(required=False)
    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), required=False
    )
    punch_history = serializers.SerializerMethodField(required=False)
    valid_from  = serializers.DateField(required=False)
    valid_to  = serializers.DateField(required=False)
    
    
    class Meta:
        model = EmployeeCheckInOutDetails
        fields = (
            "id",
            "employee",
            "status",
            "date_of_checked_in",
            "time_in",
            "time_in_format",
            "latest_time_in",
            "time_out",
            "time_out_format",
            "punch_history",
            "work_duration",
            "overtime_hours",
            "break_duration",
            "breaks",
            "employee_selfie",
            "action",
            "action_display",
            "action_status",            
            "action_status_display",
            "extra_data",
            "approval_reason",
            "reject_reason",
            "action_reason",
            "valid_from",
            "valid_to"
        )

    def validate(self, data):
        # TODO: implement below validation when roles are defined
        # instance = self.instance
        # if instance and instance.action_status != EmployeeCheckInOutDetails.OK:
        #     raise serializers.ValidationError("Request already raised !!")

        if "action" in data and data["action"] not in [
            EmployeeCheckInOutDetails.MARK_AS_EXACT_TIME,
            EmployeeCheckInOutDetails.MARK_AS_PRESENT,
            EmployeeCheckInOutDetails.MARK_AS_LOP,
            EmployeeCheckInOutDetails.MARK_AS_LEAVE,
            EmployeeCheckInOutDetails.MARK_AS_OT,
            EmployeeCheckInOutDetails.MARK_AS_COMPOFF
        ]:
            raise serializers.ValidationError("Invalid Action Choices !!")

        return data

    def get_time_in_format(self, obj):
        return localize_dt(obj.time_in).strftime("%I:%M %p")

    def get_time_out_format(self, obj):
        return (
            strftime(localize_dt(obj.time_out), mode="TIME", fmt="%I:%M %p")
            if obj.time_out
            else "-"
        )

    def get_punch_history(self, obj):
        return obj.extra_data.get("punch_history", [])

    def update(self, instance, validated_data):
        rule = (
                AssignedAttendanceRules.objects.filter(employee=instance.employee)
                .first()
                .attendance_rule
            )
        company_config, _ = CompanyCustomizedConfigurations.objects.get_or_create(company_id=instance.employee.company.id)
        attendance_start_day, attendace_end_day = fetch_attendace_rule_start_end_dates(instance.employee.company_id)
        check_month = get_monthly_record_obj_month(attendance_start_day, attendace_end_day, instance.date_of_checked_in)
        month_record_obj, is_created = EmployeeMonthlyAttendanceRecords.objects.get_or_create(
            employee_id=instance.employee.id, year=instance.date_of_checked_in.year, month=check_month
        )
        print("update",instance,validated_data)
        #attendance approval approved.
        if validated_data.get("action_status", 0) == EmployeeCheckInOutDetails.APPROVED:
            # print("Anamoly Approved")
            instance.anamolies.all().update(status=10)
            
            #doing actions for MARK_AS_COMPOFF
            if instance.action == 50:
                elr = instance.employee.employeeleaverulerelation_set.filter(leave_rule__name='Comp Off').first()
                # TODO  : COMP OFF APPROVAL need to add date.
                if elr:
                    # current_date = timezone_now().date()
                    valid_from = instance.date_of_checked_in 
                    valid_to = instance.date_of_checked_in + timedelta(days=company_config.max_days_to_utilize_compoff)
                    how_much_added = 0.5
                    # if validated_data.get('valid_from'):
                    #     valid_from = validated_data.pop('valid_from')
                    # if validated_data.get('valid_to'):
                    #     valid_to = validated_data.pop('valid_to')
                    if instance.compoff_added == 'full_day':
                        how_much_added = 1
                        elr.remaining_leaves += decimal.Decimal(1)
                        elr.earned_leaves += decimal.Decimal(1)
                    elif instance.compoff_added == 'half_day':
                        elr.remaining_leaves += decimal.Decimal(0.5)
                        elr.earned_leaves += decimal.Decimal(0.5)
                    elr.compoff_added_details.append(json.dumps({"valid_from": str(valid_from), "valid_to":str(valid_to), "leave_count": how_much_added, "used": False}))
                    elr.save()
            
            #doing actions for MARK_AS_OT
            if instance.action == 60:
                fullday_duration = hrs_to_mins(
                    rule.full_day_work_duration.split(":")[0],
                    rule.full_day_work_duration.split(":")[1]
                )
                month_record_obj.overtime_count = round(((month_record_obj.overtime_count*fullday_duration) + instance.overtime_hours)/fullday_duration, 2)
            
            #doinf actions for exact time or present
            if 10 in instance.anamolies.all().values_list('action', flat=True) or 20 in instance.anamolies.all().values_list('action', flat=True):
                print("Absent approval")
                extra_data = instance.extra_data
                
                validated_data["time_in"] = instance.time_in # localize_dt(strptime(time_in, mode="DATETIME"), tz=rule.selected_time_zone)
                validated_data["time_out"] = instance.time_out
                if 20 in instance.anamolies.all().values_list('action', flat=True):
                    validated_data["time_in"] = (
                        str(instance.date_of_checked_in)
                        + " "
                        + extra_data.get(
                            "time_in",
                            localize_dt(
                                datetime.combine(
                                    instance.date_of_checked_in, rule.shift_in_time
                                ), tz=rule.selected_time_zone
                            ).strftime("%H:%M"),
                        )
                    )
                    validated_data["time_out"] = (
                        str(instance.date_of_checked_in)
                        + " "
                        + extra_data.get(
                            "time_out",
                            localize_dt(
                                datetime.combine(
                                    instance.date_of_checked_in, rule.shift_out_time
                                ), tz=rule.selected_time_zone
                            ).strftime("%H:%M"),
                        )
                    )
                
                # localize_dt(
                #     strptime(time_out, mode="DATETIME"), tz=rule.selected_time_zone
                # )
                # Handle OT if have
                minimum_hours_to_consider_ot = rule.minimum_hours_to_consider_ot
                ot_basic_mins = hrs_to_mins(minimum_hours_to_consider_ot.split(":")[0], minimum_hours_to_consider_ot.split(":")[1])
                work_duration = instance.work_duration.split(":")
                worked_mins = hrs_to_mins(work_duration[0],work_duration[1])
                expected_working_mins = 0
                choice = WorkRuleChoices.objects.filter(
                    work_rule__in=EmployeeWorkRuleRelation.objects.filter(
                        employee=instance.employee,
                        effective_date__lte=instance.date_of_checked_in,
                    ).values_list("work_rule", flat=True),
                    week_number=get_month_weeks(instance.date_of_checked_in, need_week_number_only=True),
                ).first()
                if is_day_type(
                    choice=choice,
                    dt_input=instance.date_of_checked_in,
                    work_type=WorkRuleChoices.HALF_DAY,
                ):
                    expected_working_mins = hrs_to_mins(rule.half_day_work_duration.split(':')[0], rule.half_day_work_duration.split(':')[1])

                if is_day_type(
                    choice=choice,
                    dt_input=instance.date_of_checked_in,
                    work_type=WorkRuleChoices.FULL_DAY,
                ):
                    expected_working_mins = hrs_to_mins(rule.full_day_work_duration.split(':')[0], rule.full_day_work_duration.split(':')[1])
                if expected_working_mins and (worked_mins - expected_working_mins) >= ot_basic_mins and rule.enable_over_time:
                    validated_data['overtime_hours'] = worked_mins - expected_working_mins
                    validated_data["action_status"] = 50
                else:
                    validated_data["status"] = "P"

                print("serializer - ",month_record_obj)
                print("date - ",str(instance.date_of_checked_in))
                month_record_obj.attendance_data[
                    str(instance.date_of_checked_in)
                ] = {
                    'breaks': instance.breaks,
                    'reason': '',
                    'status': 'P',
                    'time_in': datetime.strftime(localize_dt(instance.time_in, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p"),
                    'time_out':datetime.strftime(localize_dt(instance.time_out, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p") if instance.time_out else None,
                    'anamolies': {'count': 0},
                    'present_count': month_record_obj.attendance_data[str(instance.date_of_checked_in)]['present_count'],
                    'work_duration': instance.work_duration,
                    'break_duration': instance.break_duration,
                    'over_time_data': mins_to_hrs(instance.overtime_hours) ,
                    'approval_status': 'APPROVED'
                }
                if month_record_obj.anamoly_count > 0:
                    month_record_obj.anamoly_count -= 1
                month_record_obj.present_days += month_record_obj.attendance_data[str(instance.date_of_checked_in)]['present_count'],
            
            #doing actions for leaves or lops
            elif 30 in instance.anamolies.all().values_list('action', flat=True) or 40 in instance.anamolies.all().values_list('action', flat=True):
                leaves = LeavesHistory.objects.filter(
                    employee_id=instance.employee_id,
                    start_date__lte=instance.date_of_checked_in,
                    end_date__gte=instance.date_of_checked_in
                )
                if leaves:
                    leave = leaves.first()
                    leave.status=LeavesHistory.APPROVED
                    elr = leave.leave_rule.employeeleaverulerelation_set.filter(employee_id=instance.employee, leave_rule__is_deleted=False).first()
                    validated_data["status"] = "L"
                    elr.remaining_leaves = float(elr.remaining_leaves) - float(leave.no_of_leaves_applied)
                    elr.used_lop_leaves = float(elr.used_lop_leaves) + float(leave.no_of_leaves_applied)
                    elr.used_so_far = float(elr.used_so_far) + float(leave.no_of_leaves_applied)
                    elr.save()
                    leave.save()
                p_count = 0
                month_record_obj.leaves_count += 1.0
                if float(leave.no_of_leaves_applied) < 1.0:
                    p_count = 0.5
                    month_record_obj.present_days += 0.5
                    month_record_obj.leaves_count += 0.5
                month_record_obj.attendance_data[
                    str(instance.date_of_checked_in)
                ] = {
                    'breaks': instance.breaks,
                    'reason': leave.reason,
                    'status': 'L',
                    'time_in': datetime.strftime(localize_dt(instance.time_in, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p"),
                    'time_out':datetime.strftime(localize_dt(instance.time_out, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p") if instance.time_out else None,
                    'anamolies': {'count': 0},
                    'present_count': p_count,
                    'work_duration': instance.work_duration,
                    'break_duration': instance.break_duration,
                    'over_time_data': mins_to_hrs(instance.overtime_hours) ,
                    'approval_status': 'APPROVED'
                }
                if month_record_obj.anamoly_count > 0:
                    month_record_obj.anamoly_count -= 1
        
            elif instance.action == 10 and (not instance.anamolies.exists()):
                minimum_hours_to_consider_ot = rule.minimum_hours_to_consider_ot
                ot_basic_mins = hrs_to_mins(minimum_hours_to_consider_ot.split(":")[0], minimum_hours_to_consider_ot.split(":")[1])
                work_duration = instance.work_duration.split(":")
                worked_mins = hrs_to_mins(work_duration[0],work_duration[1])
                expected_working_mins = 0
                choice = WorkRuleChoices.objects.filter(
                    work_rule__in=EmployeeWorkRuleRelation.objects.filter(
                        employee=instance.employee,
                        effective_date__lte=instance.date_of_checked_in,
                    ).values_list("work_rule", flat=True),
                    week_number=get_month_weeks(instance.date_of_checked_in, need_week_number_only=True),
                ).first()
                if is_day_type(
                    choice=choice,
                    dt_input=instance.date_of_checked_in,
                    work_type=WorkRuleChoices.HALF_DAY,
                ):
                    expected_working_mins = hrs_to_mins(rule.half_day_work_duration.split(':')[0], rule.half_day_work_duration.split(':')[1])

                if is_day_type(
                    choice=choice,
                    dt_input=instance.date_of_checked_in,
                    work_type=WorkRuleChoices.FULL_DAY,
                ):
                    expected_working_mins = hrs_to_mins(rule.full_day_work_duration.split(':')[0], rule.full_day_work_duration.split(':')[1])
                if expected_working_mins and (worked_mins - expected_working_mins) >= ot_basic_mins and rule.enable_over_time:
                    validated_data['overtime_hours'] = worked_mins - expected_working_mins
                    validated_data["action_status"] = 50
                else:
                    validated_data["status"] = "P"

                print("serializer - ",month_record_obj)
                print("date - ",str(instance.date_of_checked_in))
                print(month_record_obj.attendance_data[str(instance.date_of_checked_in)]['present_count'])
                month_record_obj.attendance_data[
                    str(instance.date_of_checked_in)
                ] = {
                    'breaks': instance.breaks,
                    'reason': instance.absent_period,
                    'status': 'P',
                    'time_in': datetime.strftime(localize_dt(instance.time_in, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p"),
                    'time_out':datetime.strftime(localize_dt(instance.time_out, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p") if instance.time_out else None,
                    'anamolies': {'count': 0},
                    'present_count': month_record_obj.attendance_data[str(instance.date_of_checked_in)]['present_count'],
                    'work_duration': instance.work_duration,
                    'break_duration': instance.break_duration,
                    'over_time_data': mins_to_hrs(instance.overtime_hours) ,
                    'approval_status': 'APPROVED'
                }                
                month_record_obj.present_days += float(month_record_obj.attendance_data[str(instance.date_of_checked_in)]['present_count'])                
        #in attendance appproval is rejected
        else:
            # print("Anamoly Rejected")
            validated_data["action_status"] = validated_data.get(
                "action_status", EmployeeCheckInOutDetails.PENDING
            )
            if validated_data.get('action'):
                #just doing in processing
                instance.anamolies.all().update(status=30, action=validated_data.get('action'))
            if instance.anamolies.all().exists():
                validated_data["status"] = "AN"
            if validated_data.get("action_status", 0) == 40:
                
                #anamoly is rejected
                instance.anamolies.all().update(status=40)
                if instance.anamolies.all().exists():
                    month_record_obj.attendance_data[
                        str(instance.date_of_checked_in)
                    ] = {
                        'breaks': instance.breaks,
                        'reason': 'Rejected',
                        'status': 'A',
                        'time_in': datetime.strftime(localize_dt(instance.time_in, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p"),
                        'time_out':datetime.strftime(localize_dt(instance.time_out, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p") if instance.time_out else None,
                        'anamolies': {'count': 0},
                        'present_count': 0,
                        'work_duration': instance.work_duration,
                        'break_duration': instance.break_duration,
                        'over_time_data': mins_to_hrs(instance.overtime_hours) ,
                        'approval_status': 'Rejected'
                    }
                    month_record_obj.absent_count += 1
                    month_record_obj.lop_count += 1
                    if month_record_obj.anamoly_count > 0:
                        month_record_obj.anamoly_count -= 1
                
                # overtime is rejected
                if instance.action == 60:
                    validated_data['overtime_hours'] = 0
                    ans = instance.anamolies.all()
                    ans.delete()
                    validated_data["status"] = "P"
                    month_record_obj.attendance_data[
                        str(instance.date_of_checked_in)
                    ] = {
                        'breaks': instance.breaks,
                        'reason': '',
                        'status': 'P',
                        'time_in': datetime.strftime(localize_dt(instance.time_in, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p"),
                        'time_out':datetime.strftime(localize_dt(instance.time_out, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p") if instance.time_out else None,
                        'anamolies': {'count': 0},
                        'present_count': 1,
                        'work_duration': instance.work_duration,
                        'break_duration': instance.break_duration,
                        'over_time_data': 0,
                        'approval_status': ''
                    }
                
                # compoff is rejected
                if instance.action == 50:
                    validated_data['compoff_added'] = None
                    month_record_obj.attendance_data[
                        str(instance.date_of_checked_in)
                    ] = {
                        'breaks': instance.breaks,
                        'reason': '',
                        'status': 'H' if Holidays.objects.filter(holiday_date=instance.date_of_checked_in, company_id=instance.employee.company_id).exists() else 'WO',
                        'time_in': datetime.strftime(localize_dt(instance.time_in, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p"),
                        'time_out':datetime.strftime(localize_dt(instance.time_out, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p") if instance.time_out else None,
                        'anamolies': {'count': 0},
                        'present_count': 1,
                        'work_duration': instance.work_duration,
                        'break_duration': instance.break_duration,
                        'over_time_data': 0,
                        'approval_status': ''
                    }
                    
            if "time_in" in validated_data:
                validated_data["latest_time_in"] = validated_data["time_in"]
            if 30 in instance.anamolies.all().values_list('action', flat=True) or 40 in instance.anamolies.all().values_list('action', flat=True):
                leaves = LeavesHistory.objects.filter(
                    employee_id=instance.employee_id,
                    start_date__lte=instance.date_of_checked_in,
                    end_date__gte=instance.date_of_checked_in
                )
                if validated_data["action_status"] == 40:
                    leaves.update(status=LeavesHistory.REJECTED, reason_for_rejection=validated_data.get("reject_reason", ""))
                    month_record_obj.attendance_data[
                        str(instance.date_of_checked_in)
                    ] = {
                        'breaks': instance.breaks,
                        'reason': validated_data.get("reject_reason", ""),
                        'status': 'A',
                        'time_in': datetime.strftime(localize_dt(instance.time_in, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p"),
                        'time_out':datetime.strftime(localize_dt(instance.time_out, tz=rule.selected_time_zone), "%Y-%m-%d %I:%M %p") if instance.time_out else None,
                        'anamolies': {'count': instance.anamolies.count()},
                        'present_count': 1,
                        'work_duration': instance.work_duration,
                        'break_duration': instance.break_duration,
                        'over_time_data': mins_to_hrs(instance.overtime_hours) ,
                        'approval_status': 'Rejected'
                    }
                    month_record_obj.absent_count += 1
                    month_record_obj.lop_count += 1
        # ext_data = validated_data.get("extra_data", instance.extra_data) 

        month_record_obj.save()
        validated_data["extra_data"] = validated_data.get("extra_data", instance.extra_data) 
        # | (
        #     instance.extra_data or {}
        # )
        instance = super().update(instance, validated_data)
        # if "time_out" in validated_data:
        #     calculate_work_time(instance, instance.time_out, save=True)
        return instance


class CheckInOutDetailSerializer(serializers.ModelSerializer):
    anamolies = serializers.SerializerMethodField(required=False)
    status = serializers.SerializerMethodField(required=False)
    time_in_format = serializers.SerializerMethodField(read_only=True)
    time_out_format = serializers.SerializerMethodField(read_only=True)
    action = serializers.ChoiceField(choices=EmployeeCheckInOutDetails.ACTION_CHOICES)
    action_display = serializers.ChoiceField(
        choices=EmployeeCheckInOutDetails.ACTION_CHOICES, source="get_action_display"
    )
    # action_status = serializers.ChoiceField(
    #     choices=EmployeeCheckInOutDetails.ACTION_STATUS_CHOICES
    # )
    action_status = serializers.SerializerMethodField(read_only=True)
    action_status_display = serializers.ChoiceField(
        choices=EmployeeCheckInOutDetails.ACTION_STATUS_CHOICES,
        source="get_action_status_display",
    )
    punch_history = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EmployeeCheckInOutDetails
        fields = (
            "id",
            "status",
            "date_of_checked_in",
            "time_in",
            "time_in_format",
            "latest_time_in",
            "time_out",
            "time_out_format",
            "punch_history",
            "work_duration",
            "overtime_hours",
            "break_duration",
            "breaks",
            "employee_selfie",
            "action",
            "action_display",
            "action_status",
            "action_status_display",
            "extra_data",
            "anamolies",
            "action_reason",
            "approval_reason",
            "reject_reason",
            "is_logged_out"
        )
        extra_kwargs = {"status": {"read_only": True}}

    def get_time_in_format(self, obj):
        return localize_dt(obj.time_in).strftime("%I:%M %p")

    def get_time_out_format(self, obj):
        return (
            strftime(localize_dt(obj.time_out), mode="TIME", fmt="%I:%M %p")
            if obj.time_out
            else "-"
        )

    def get_employee_details(self, obj):
        employee: Employee = obj.employee
        work_details = employee.work_details
        manager = get_manager(employee)
        return {
            "name": employee.name,
            "department": work_details.department.name
            if work_details.department
            else "-",
            "manager": manager.name if manager else "-",
            "location": work_details.work_location,
        }

    def get_status(self, obj: EmployeeCheckInOutDetails):
        employee = obj.employee

        lh_qs = LeavesHistory.objects.filter(
            employee=employee,
            start_date__lte=obj.date_of_checked_in,
            end_date__gte=obj.date_of_checked_in,
            status=LeavesHistory.APPROVED,
        )
        if lh_qs.exists():
            return "L"

        if Holidays.objects.filter(
            holiday_date=obj.date_of_checked_in, company=employee.company, holiday_type=False
        ).exists():
            return "H"

        if work_rule_relation := EmployeeWorkRuleRelation.objects.filter(
            employee=employee, effective_date__lte=obj.date_of_checked_in
        ).first():
            work_rule = work_rule_relation.work_rule
            week_number = get_month_weeks(
                obj.date_of_checked_in, need_week_number_only=True
            )
            rule_choice = WorkRuleChoices.objects.filter(
                work_rule=work_rule, week_number=week_number
            ).first()
            if is_day_type(choice=rule_choice, dt_input=obj.date_of_checked_in):
                return "WO"

        if obj.status == "AN":
            return obj.status

        if obj.status.lower() == "p" and obj.action_status == obj.APPROVED:
            return obj.status

        if obj.anamolies.all().exists():
            return "AN"
        return "P"

    def get_anamolies(self, obj):
        anamolies = obj.anamolies.all()
        result = {"count": anamolies.count(), "data": []}
        if anamolies.exists():
            for anamoly in anamolies:
                result["data"].append(
                    {
                        "id": anamoly.id,
                        "type": anamoly.get_choice_display(),
                        "discrepancy": anamoly.result,
                        "status": anamoly.get_status_display(),
                        "action": anamoly.get_action_display(),
                    }
                )
        return result

    def get_punch_history(self, obj):
        return obj.extra_data.get("punch_history", [])

    def get_action_status(self, obj):
        return obj.action_status if  obj.status == "AN"  else ""
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['auto_clocked_out'] = 'AC' if data['time_out'] and not data['is_logged_out'] and instance.employee.assignedattendancerules_set.first().attendance_rule.auto_clock_out else ''
        return data

class AnamolyHistorySerializer(serializers.ModelSerializer):
    """
    Anamoly History Serializer

    AJAY, 27.03.2023
    """

    choice = serializers.ChoiceField(
        choices=AnamolyHistory.ANAMOLY_CHOICES, source="get_choice_display"
    )
    action = serializers.ChoiceField(
        choices=AnamolyHistory.ACTION_CHOICES, source="get_action_display"
    )
    status = serializers.ChoiceField(
        choices=AnamolyHistory.STATUS_CHOICES, source="get_status_display"
    )

    class Meta:
        model = AnamolyHistory
        fields = (
            "id",
            "clock",
            "request_date",
            "choice",
            "result",
            "reason",
            "action",
            "status",
        )

    def update(self, instance, validated_data):
        # TODO: Send notification to the Manager
        return super().update(instance, validated_data)


class AnamolyHistoryDetailSerializer(serializers.ModelSerializer):
    """
    Anamoly History Serializer

    AJAY, 27.03.2023
    """

    class Meta:
        model = AnamolyHistory
        fields = (
            "id",
            "employee",
            "request_date",
            "Reason",
            "Action",
        )


from attendance.models import KeyloggerAttendanceLogs, EmployeeSystemMapping
import requests
from geopy.geocoders import Nominatim
class KeyloggerAttendanceLogsSerializer(serializers.ModelSerializer):
    instance_duration = serializers.ReadOnlyField()
    class Meta:
        model = KeyloggerAttendanceLogs
        fields ="__all__"
    
    def to_internal_value(self, data): #for initial data modifying or adding
        emp_obj = EmployeeSystemMapping.objects.filter(system_name=data['logged_user']).first()
        if hasattr(emp_obj, 'emp') and hasattr(emp_obj.emp, 'work_details') and hasattr(emp_obj.emp.work_details, 'employee_number'):
            data['emp_id'] = emp_obj.emp.work_details.employee_number
        else:
            data['emp_id'] = "unknown user"
        return super().to_internal_value(data)

    def create(self, validated_data):
        #for internet location
        if validated_data.get("internet_ip"):
            location_data = requests.get(f"http://ip-api.com/json/{validated_data['internet_ip']}").json()
            internet_location = location_data.get("city","") +" "+location_data.get("regionName","") +" "+ location_data.get("zip","")\
                +" "+ location_data.get("country","") +" lat "+ str(location_data.get("lat","")) +" lon "+ str(location_data.get("lon",""))
        else:
            internet_location = "on offline"
        validated_data['internet_location']=internet_location
        
        #for system location
        if validated_data.get("system_location"):
            if len(eval(validated_data.get("system_location"))) == 2:
                lat, lon = eval(validated_data.get("system_location"))[0], eval(validated_data.get("system_location"))[1]
                print("lat", lat)
                print("lon", lon)
                geolocator = Nominatim(user_agent="HRMSProject")
                address = geolocator.reverse((lat, lon))
            else:
                address = eval(validated_data.get("system_location"))[0]
        else:
            address = ""
        validated_data['system_location'] = address
        return super().create(validated_data)
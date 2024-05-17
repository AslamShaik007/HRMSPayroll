from datetime import date
from decimal import Decimal as D

from leave.models import LeaveRules, WorkRuleChoices, LeaveRuleSettings
import datetime
from core.utils import timezone_now

def init_leaverules(self, company, rules=[]):
    if not company:
        return
    if not rules:
        rules = [
            {"name": "Casual Leave", "leaves_allowed_in_year": 12, "weekends_between_leave": False, "holidays_between_leave": False, "creditable_on_accrual_basis": True, "accrual_frequency": "MONTHLY", "accruel_period": "Start", "allowed_under_probation": False, "continuous_leaves_allowed": 0, "max_leaves_allowed_in_month": 3, "is_leave_encashment_enabled": True, "all_remaining_leaves_for_encash": True},
            
            {"name": "Sick Leave", "leaves_allowed_in_year": 6, "allowed_under_probation": False, "is_leave_encashment_enabled": True, "all_remaining_leaves_for_encash": True,
            "continuous_leaves_allowed": 0, "max_leaves_allowed_in_month": 6},
            
            {"name": "Maternity Leave", "leaves_allowed_in_year": 182, "allowed_under_probation": False, "max_leaves_allowed_in_month": None,},
            {"name": "Bereavement Leave", "leaves_allowed_in_year": 5, "allowed_under_probation": False, "max_leaves_allowed_in_month": None,
            "is_leave_encashment_enabled": True, "all_remaining_leaves_for_encash": True,
            },
            {"name": "Paternity Leave",  "leaves_allowed_in_year": 5, "allowed_under_probation": True, "max_leaves_allowed_in_month": None,
            "is_leave_encashment_enabled": True, "all_remaining_leaves_for_encash": True,},
            {"name": "Marriage Leave",  "leaves_allowed_in_year": 5, "allowed_under_probation": True, "max_leaves_allowed_in_month": None,
            "is_leave_encashment_enabled": True, "all_remaining_leaves_for_encash": True,},
            
            {"name": "Loss Of Pay", "leaves_allowed_in_year": 160},
            {"name": "Additional Leaves", "leaves_allowed_in_year": 60, "allowed_under_probation": True, "max_leaves_allowed_in_month":31, "weekends_between_leave": True, "holidays_between_leave": True},
            {"name": "Comp Off", "leaves_allowed_in_year": 0, "allowed_under_probation": True,}
        ]
    leaves = []
    for rule in rules:
        leave = LeaveRules(
            company=company,
            name=rule["name"],
            leaves_allowed_in_year=rule["leaves_allowed_in_year"],
            max_leaves_allowed_in_month=rule.get("max_leaves_allowed_in_month",4),
            allowed_under_probation=rule.get('allowed_under_probation', False),
            weekends_between_leave=rule.get('weekends_between_leave', False),
            holidays_between_leave=rule.get('holidays_between_leave', False),
            valid_from=datetime.datetime.now().date().replace(month=1, day=1),
            valid_to=datetime.datetime.now().date().replace(month=12, day=31),
        )
        leaves.append(leave)
    if leaves:
        LeaveRules.objects.bulk_create(leaves)

def init_leaverule_settings(self="", company=""):
    if not company:
        return
    current_year = timezone_now().date().year
    calendar_type="calendaryear"
    start_date = f"{current_year}-01-01"
    end_date = f"{current_year}-12-31"
    LeaveRuleSettings.objects.create(company=company,
                                     calendar_type=calendar_type,
                                     start_date=start_date,
                                     end_date=end_date,
                                    )

def is_day_type(
    choice: WorkRuleChoices,
    work_type: int = WorkRuleChoices.WEEK_OFF,
    dt_input: date = None,
    day: str = None,
) -> bool:
    """
    > It returns `True` if the day is a day off, `False` otherwise

    :param choice: WorkRuleChoices,
    :type choice: WorkRuleChoices
    :param work_type: This is the type of day off. It can be a week off, a holiday, or a weekend
    :type work_type: int
    :param dt_input: date = None
    :type dt_input: date
    :param day: The day of the week to check
    :type day: str
    :return: A boolean value

    AJAY, 30.03.2023
    """

    if (dt_input is None and day is None) or not choice:
        return False

    if day is None:
        day = dt_input.strftime("%A")

    if day.lower() not in [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]:
        raise ValueError("Invalid day of the week")

    return getattr(choice, day.lower()) == work_type


def get_accruel_leaves(
    accruel_days,
    leaves_per_year: int = 0,
):
    accruel_days += 1

    print(f"accruel_days:{accruel_days}\n")
    print(f"leaves_per_year:{leaves_per_year}\n")

    # calculate the number of accrued leaves for the accrual period
    accrued_leaves = 0

    if accruel_days > 0:
        if accruel_days >= 365:
            # yearly accrual
            accrued_leaves = leaves_per_year
        elif accruel_days >= 183:
            # half-yearly accrual
            accrued_leaves = leaves_per_year / 2
        elif accruel_days >= 92:
            # quarterly accrual
            accrued_leaves = leaves_per_year / 4
        else:
            # monthly accrual
            accrued_leaves = leaves_per_year / 12

        accrued_leaves = round(accrued_leaves * 2) / 2
        # if the rounded value is between 0.6 and 0.9, round it to 1.0
        if 0.6 <= accrued_leaves < 1.0:
            accrued_leaves = 1.0
        # if the rounded value is between 0.1 and 0.4, round it to 0.5
        elif 0.1 <= accrued_leaves < 0.5:
            accrued_leaves = 0.5

    return D(accrued_leaves)


class Exporter:
    """
    Used to export employee leave logs

    AJAY, 14.03.2023
    """

    ...


class Importer:
    """
    Used to import employee leaves information

    AJAY, 14.03.2023
    """

    def handle(self, *args, **kwargs):
        """
        Default handler to handle leave information

        AJAY, 14.03.2023
        """
        ...

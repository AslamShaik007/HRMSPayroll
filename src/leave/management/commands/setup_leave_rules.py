from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from core.utils import timezone_now
from directory.models import Employee
from HRMSApp.models import CompanyDetails
from leave.models import EmployeeLeaveRuleRelation, LeaveRules


class Command(BaseCommand):
    """
    Generate default leave rules and assign it to all the employees of the company

    AJAY, 02.04.2023
    """

    help = "manage.py setup_leave_rules --commit --assign"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "-c", "--commit", dest="commit", action="store_true", default=False
        )
        parser.add_argument(
            "-nr", "--new_rule", type=str, dest="new_rule", default="Loss Of Pay"
        )
        parser.add_argument(
            "-a", "--assign", dest="assign", action="store_true", default=False
        )
        parser.add_argument("-cp", "--company", type=int, dest="company")
        parser.add_argument("-e", "--employee", type=int, dest="employee")

    def handle_assign_rule(self, rule: LeaveRules, employee: Employee) -> None:
        """
        Assigning leave rules to the employee

        AJAY, 02.04.2023
        """

        if not EmployeeLeaveRuleRelation.objects.filter(
            employee=employee, leave_rule=rule
        ).exists():
            EmployeeLeaveRuleRelation.objects.create(
                employee=employee,
                leave_rule=rule,
                effective_date=timezone_now().date(),
            )

    # @transaction.atomic()
    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        sid = transaction.set_autocommit(autocommit=False)

        companies = CompanyDetails.objects.all()
        if options.get("company", None):
            companies = companies.filter(id=options["company"])

        leave_rules = LeaveRules.objects.filter(name=options["new_rule"])
        for company in companies:
            if not leave_rules.exists():
                LeaveRules.objects.create(
                    company=company,
                    name=options["new_rule"],
                    description=options["new_rule"],
                )
            if options["assign"]:
                rule = leave_rules.first()
                emps = Employee.objects.filter(company=company)
                if options.get("employee", None):
                    emps = emps.filter(id=options["employee"])
                for emp in emps:
                    self.handle_assign_rule(rule, emp)

        if options["commit"]:
            transaction.commit()
            self.stdout.write(self.style.SUCCESS("Successful commit !"))
        else:
            transaction.rollback(sid)
            self.stdout.write(self.style.WARNING("Dry Run !"))

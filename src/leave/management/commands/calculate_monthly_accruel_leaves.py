from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from core.utils import timezone_now
from directory.models import Employee
from HRMSApp.models import CompanyDetails
from leave.models import EmployeeLeaveRuleRelation
from leave.services import get_accruel_leaves


class Command(BaseCommand):

    help = "manage.py calculate_monthly_accruel_leaves --commit"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "-c", "--commit", dest="commit", action="store_true", default=False
        )
        parser.add_argument("-cp", "--company", type=str, dest="company")

    # @transaction.atomic()
    def handle(self, **options: Any) -> None:
        sid = transaction.set_autocommit(autocommit=False)

        companies = CompanyDetails.objects.all()
        if options.get("company", None):
            companies = companies.filter(company_name=options["company"])

        today = timezone_now().date()
        for company in companies:
            for emp in Employee.objects.filter(company=company):
                emp_start_date = emp.date_of_join
                for rel in EmployeeLeaveRuleRelation.objects.filter(employee=emp):
                    rule = rel.leave_rule
                    if not rule.creditable_on_accrual_basis:
                        continue

                    if emp_start_date.year < today.year:
                        if rule.accrual_frequency.lower() == "monthly":
                            accruel_days = 30
                    elif (
                        emp_start_date.year == today.year
                        and emp_start_date.month <= today.month
                    ):
                        if rule.accrual_frequency.lower() == "monthly":
                            accruel_days = 30
                    else:
                        accruel_days = 0

                    accrued_leaves = get_accruel_leaves(
                        accruel_days, rule.leaves_allowed_in_year
                    )

                    rel.earned_leaves += accrued_leaves
                    rel.remaining_leaves += accrued_leaves
                    rel.extra_data[today.strftime("%b")] = float(accrued_leaves)
                    print(f"earned_leaves: {rel.earned_leaves}")
                    rel.save()

        if options["commit"]:
            transaction.commit()
            self.stdout.write(self.style.SUCCESS("Succesful commit!"))
        else:
            transaction.rollback(sid)
            self.stdout.write(self.style.WARNING("Dry-Run!"))

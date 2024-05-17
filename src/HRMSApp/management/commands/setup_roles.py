from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from HRMSApp.models import Roles


class Command(BaseCommand):
    help = "manage.py setup_roles --commit"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--commit",
            "-c",
            action="store_true",
            dest="commit",
            default=False,
            help="Confirmation to save",
        )

    # @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        sid = transaction.set_autocommit(autocommit=False)

        roles = [
            ("CEO", "CEO"),
            ("HR_ADMIN", "HR ADMIN"),
            ("FINANCE_ADMIN", "FINANCE ADMIN"),
            ("HR_EXECUTIVE", "HR EXECUTIVE"),
        ]

        roles = [
            {
                "name": "CEO",
                "code": "CEO",
                "description": (
                    "CEO is the head of the organization.\r\n\r\nFor Organisation Chart, addition of CEO is required."
                    "\r\n\r\nCEO is also the HR Admin.\r\n\r\nCEO's permissions apply to all employees.\r\n\r\n"
                    "CEO can:\r\n\r\nView all employee profile information\r\n"
                    "View sensitive employee information (such as PAN Card, IDs and salary)\r\nEdit employee profiles"
                    "\r\nEdit, Upload and Approve Attendance and Leaves\r\nCreate and remove admins, and edit admin "
                    "permissions"
                ),
            },
            {
                "name": "HR ADMIN",
                "code": "HR_ADMIN",
                "description": (
                    "HR Admin's permissions apply to all employees.\r\n\r\nThis admin can:\r\n\r\n"
                    "View all employee profile information\r\n"
                    "View sensitive employee information (such as PAN Card, IDs and salary)\r\nEdit employee profiles"
                    "\r\nEdit, Upload and Approve Attendance and Leaves\r\n"
                    "Create and remove admins, and edit admin permissions"
                ),
            },
            {
                "name": "FINANCE ADMIN",
                "code": "FINANCE_ADMIN",
                "description": (
                    "Finance admin's permissions apply to all employees.\r\n\r\n"
                    "This admin can:\r\n\r\nView salary and bank details of employee profiles\r\n"
                    "View sensitive employee information (such as PAN Card and IDs"
                ),
            },
            {
                "name": "HR EXECUTIVE",
                "code": "HR_EXECUTIVE",
                "description": (
                    "HR Executive's permissions apply to all employees.\r\n\r\nThis admin can:\r\n\r\n"
                    "View all employee profile information (Non-payroll)\r\n"
                    "View sensitive employee information (such as PAN Card, IDs, DOB etc)\r\n"
                    "Add and edit employee profiles\r\nEdit, Upload and Approve Attendance and Leaves\r\n"
                    "This Admin will not have any payroll access."
                ),
            },
        ]

        for role in roles:
            role["slug"] = role["code"].lower()
            Roles.objects.update_or_create(code=role["code"], defaults=role)

        if options["commit"]:
            transaction.commit()
            self.stdout.write(self.style.SUCCESS("Roles were created successfully"))
        else:
            transaction.rollback(sid)
            self.stdout.write(self.style.WARNING("Dry-Run !!"))

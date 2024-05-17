from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from directory.models import EmployeeTypes


class Command(BaseCommand):
    """
    Command to generate Employee type choices

    AJAY, 09.01.2023
    """

    help = "manage.py setup_employee_types --commit"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "-c",
            "--commit",
            dest="commit",
            default=False,
            action="store_true",
            help=("Flag to save the information"),
        )

    # @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        """
        Default Handler

        AJAY, 09.01.2023
        """
        sid = transaction.set_autocommit(autocommit=False)

        choices = (10, 20, 30, 40, 50)

        for choice in choices:
            EmployeeTypes.objects.get_or_create(employee_type=choice)
            self.stdout.write(self.style.SUCCESS(f"Employee type: {choice} is created"))

        if options["commit"]:
            transaction.commit()
            self.stdout.write(self.style.SUCCESS("Scuccessful commit"))
        else:
            transaction.rollback(sid)
            self.stdout.write(self.style.WARNING("Successful Dry-Run"))

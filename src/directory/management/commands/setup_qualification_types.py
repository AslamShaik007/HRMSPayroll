from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from directory.models import QualificationTypes


class Command(BaseCommand):
    """
    Command to generate Manager type choices

    SURESH, 13.01.2023
    """

    help = "manage.py setup_qualification_types --commit"

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

        SURESH, 13.01.2023
        """
        sid = transaction.set_autocommit(autocommit=False)

        choices = (10, 20, 30, 40, 50, 60, 70)

        for choice in choices:
            QualificationTypes.objects.get_or_create(qualification_type=choice)
            self.stdout.write(
                self.style.SUCCESS(f"Qualification type: {choice} is created")
            )

        if options["commit"]:
            transaction.commit()
            self.stdout.write(self.style.SUCCESS("Scuccessful commit"))
        else:
            transaction.rollback(sid)
            self.stdout.write(self.style.WARNING("Successful Dry-Run"))

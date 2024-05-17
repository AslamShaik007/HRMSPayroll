from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from investment_declaration.models import FormChoices


class Command(BaseCommand):
    """
    Command to generate form choices

    """

    help = "manage.py setup_form_choices --commit"

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
        """
        sid = transaction.set_autocommit(autocommit=False)

        choices = ("Standard declaration of 50000 under section 16", "Deduction under section 80C", "Deduction for medical premium under section 80D", "Interest payable on Housing Loan max (2 Lakh)", "HRA Allowances Exempt under Section 10(5), 10(13A), 10(14), 10(17)", "LTA", "Any Other")

        for choice in choices:
            FormChoices.objects.get_or_create(formtype=choice)
            self.stdout.write(
                self.style.SUCCESS(f"Saving declaration form Choices: {choice} is created")
            )

        if options["commit"]:
            transaction.commit()
            self.stdout.write(self.style.SUCCESS("Scuccessful commit"))
        else:
            transaction.rollback(sid)
            self.stdout.write(self.style.WARNING("Successful Dry-Run"))

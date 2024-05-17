from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.shortcuts import get_object_or_404

from investment_declaration.models import SubFormChoices, FormChoices


class Command(BaseCommand):
    """
    Command to generate form choices

    """

    help = "manage.py setup_subform_choices --commit"

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

        choices = [
            {"parentform":2, "formtype":"Life Insurance Premium"}, {"parentform":2, "formtype":"Investment in Fixed Deposits"}, 
            {"parentform":2, "formtype":"Equity Linked Savings Scheme (ELSS)"}, {"parentform":2, "formtype":"Unit Linked Insurance Plan (ULIP)"}, 
            {"parentform":2, "formtype":"Employee Provident Fund (EPF)"}, {"parentform":2, "formtype":"Public Provident Fund (PPF)"}, 
            {"parentform":2, "formtype":"National Savings Certificate (NSC)"}, {"parentform":2, "formtype":"Home Loan - Principal Repayment"}, 
            {"parentform":2, "formtype":"Contribution to Pension Fund"},{"parentform":2, "formtype":"Children's Tuition Fee"}, 
            {"parentform":2, "formtype":"Sukanya Samriddhi Scheme"}, {"parentform":2, "formtype":"NABARD Bonds"},
            {"parentform":3, "formtype":"Medical Insurance Premium - Self/Spouse/Children 80D 25,000"},
            {"parentform":3, "formtype":"Medical Insurance Premium - Parents 80D 25,000"}, 
            {"parentform":3, "formtype":"Medical Insurance Premium - Parents - Sr. Citizen----- 50,000"},
            {"parentform":7, "formtype":"Additional deduction of interest payment on home loan 80EEA ---- 1,50,000"}, {"parentform":7, "formtype":"National Pension Scheme (NPS) 80CCD (1B) ---- 50,000"},
            {"parentform":7, "formtype":"Employer's Contribution to NPS Account 80CCD (2)--- No Limit"}, {"parentform":7, "formtype":"Rajiv Gandhi Equity Scheme 80CCG ---- 25,000"}, 
            {"parentform":7, "formtype":"Rehabilitation of Handicapped Dependent 80DD --- 1,25,000"},{"parentform":7, "formtype":"Medical Expenditure on Specified Disease 80DDB ---- 1,00,000"}, 
            {"parentform":7, "formtype":"Interest on Education Loan 80E ---- No Limit"}, {"parentform":7, "formtype":"Donation towards Exempted Social Causes 80G----- No Limit"},
            {"parentform":7, "formtype":"Deduction in place of HRA 80GG ---- 60,000"}, {"parentform":7, "formtype":"Donation to Political Party 80GGC----- No Limit"}, 
            {"parentform":7, "formtype":"Interest Income from Savings Account 80TTA--- 10,000"}, {"parentform":7, "formtype":"Disability 80U----- 1,25,000"}, {"parentform":7, "formtype":"Other Deductions"}
        ]

        for choice_data in choices:
            obj = get_object_or_404(FormChoices, id=choice_data["parentform"])
            SubFormChoices.objects.get_or_create(parentform=obj, formtype=choice_data["formtype"])
            self.stdout.write(
                self.style.SUCCESS(f"Saving declaration subform choices is created")
            )
        if options["commit"]:
            transaction.commit()
            self.stdout.write(self.style.SUCCESS("Scuccessful commit"))
        else:
            transaction.rollback(sid)
            self.stdout.write(self.style.WARNING("Successful Dry-Run"))
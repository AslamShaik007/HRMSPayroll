from typing import Any, Optional

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from choices.models import Choices, ChoiceType
from HRMSApp.models import CompanyDetails
from investment_declaration.models import DeclarationForms


class Command(BaseCommand):
    """
    Command to generate Employee Investment Declaration Type choices

    SURESH, 02.05.2023
    """

    help = "manage.py setup_investment_declaration_anyother --commit"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "-c",
            "--commit",
            dest="commit",
            default=False,
            action="store_true",
            help=("Flag to save the information"),
        )

        parser.add_argument(
            "-cp",
            "--company",
            dest="company",
            type=int,
            default=1,
            help="Company id to populate the choices",
        )

    # @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        """
        Default Handler

        SURESH, 10.05.2023
        """
        sid = transaction.set_autocommit(autocommit=False)

        form_types = {
            # 10: "Standard declaration of 50000 under section 16",
            # 50: "Life Insurance Premium",
            # 60: "Investment in Fixed Deposits",
            # 70: "Equity Linked Savings Scheme (ELSS)",
            # 80: "Unit Linked Insurance Plan (ULIP)",
            # 90: "Employee Provident Fund (EPF)",
            # 100: "Public Provident Fund (PPF)",
            # 110: "National Savings Certificate (NSC)",
            # 120: "Home Loan - Principal Repayment",
            # 130: "Contribution to Pension Fund",
            # 140: "Children's Tuition Fee",
            # 150: "Sukanya Samriddhi Scheme",
            # 160: "NABARD Bonds",
            # 140: "Medical Insurance Premium - Self/Spouse/Children 80D  25,000",
            # 150: "Medical Insurance Premium - Parents 80D    25,000",
            # 160: "Medical Insurance Premium - Parents - Sr. Citizen----- 50,000",
            # 170: "Interest payable on Housing Loan max (2 Lakh)",
            # 180: "HRA Allowances Exempt under Section 10(5), 10(13A), 10(14), 10(17)",
            # 190: "LTA",
            230: "Additional deduction of interest payment on home loan 80EEA ---- 1,50,000",
            240: "National Pension Scheme (NPS) 80CCD (1B) ---- 50,000",
            250: "Employer's Contribution to NPS Account 80CCD (2)--- No Limit",
            260: "Rajiv Gandhi Equity Scheme 80CCG  ---- 25,000",
            270: "Rehabilitation of Handicapped Dependent 80DD --- 1,25,000",
            280: "Medical Expenditure on Specified Disease 80DDB  ---- 1,00,000",
            290: "Interest on Education Loan 80E ---- No Limit",
            300: "Donation towards Exempted Social Causes 80G----- No Limit",
            310: "Deduction in place of HRA 80GG ---- 60,000",
            320: "Donation to Political Party 80GGC----- No Limit",
            330: "Interest Income from Savings Account 80TTA--- 10,000",
            340: "Disability 80U----- 1,25,000",
            350: "Other Deductions",
        }

        qs = ChoiceType.objects.filter(
            slug="investment_declaration_anyother",
            company__id=options["company"],
            content_type=ContentType.objects.get_for_model(DeclarationForms),
        )
        if qs.exists():
            choice_type = qs.first()
        else:
            choice_type = ChoiceType(
                slug="investment_declaration_anyother",
                name="Investment Declaration Anyother",
                content_type=ContentType.objects.get_for_model(DeclarationForms),
                company=CompanyDetails.objects.get(id=options["company"]),
            )

        choice_type.is_deleted = False
        choice_type.save()

        for k, v in form_types.items():
            Choices.objects.update_or_create(
                key=k, value=v, choice_type=choice_type, defaults={"is_active": True}
            )

        if options["commit"]:
            transaction.commit()
            self.stdout.write(self.style.SUCCESS("Scuccessful commit"))
        else:
            transaction.rollback(sid)
            self.stdout.write(self.style.WARNING("Successful Dry-Run"))

import os
import sys
import django
sys.path.append('./')
if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]
from django.db import transaction

from investment_declaration.models import FormChoices


class SetupFormChoices:

    # @transaction.atomic
    def handle(self):
        sid = transaction.set_autocommit(autocommit=False)

        choices = ("Standard declaration of 50000 under section 16", "Deduction under section 80C", "Deduction for medical premium under section 80D", "Interest payable on Housing Loan max (2 Lakh)", "HRA Allowances Exempt under Section 10(5), 10(13A), 10(14), 10(17)", "LTA", "Any Other")

        for choice in choices:
            FormChoices.objects.get_or_create(formtype=choice)
            print(f"Saving declaration form Choices: {choice} is created")

        if "commit" in sys.argv:
            transaction.commit()
            print("Scuccessful commit")
        else:
            transaction.rollback(sid)
            print("Successful Dry-Run")
            
if __name__ == "__main__":
    SetupFormChoices().handle()

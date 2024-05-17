import sys
import os
import django
sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]
from django.db import transaction

from company_profile.models import AuditorTypes


class AuditorTypesSetUp:

    # @transaction.atomic
    def handle(self):
        sid = transaction.set_autocommit(autocommit=False)

        choices = (10, 20)

        for choice in choices:
            AuditorTypes.objects.get_or_create(auditor_type=choice)
            print(f"Auditor type: {choice} is created")

        if "commit" in sys.argv:
            transaction.commit()
            print("Scuccessful commit")
        else:
            transaction.rollback(sid)
            print("Successful Dry-Run")
            
if __name__ == "__main__":
    AuditorTypesSetUp().handle()
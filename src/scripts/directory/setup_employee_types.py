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

from directory.models import EmployeeTypes


class SetupEmployeeTypes:

    # @transaction.atomic
    def handle(self):
        sid = transaction.set_autocommit(autocommit=False)

        choices = (10, 20, 30, 40, 50)

        for choice in choices:
            EmployeeTypes.objects.get_or_create(employee_type=choice)
            print(f"Employee type: {choice} is created")

        if "commit" in sys.argv:
            transaction.commit()
            print("Scuccessful commit")
        else:
            transaction.rollback(sid)
            print("Successful Dry-Run")
if __name__ == "__main__":
    SetupEmployeeTypes().handle()
import sys
import os
import django

from typing import Any, Optional
sys.path.append('./')
if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]
from django.db import transaction

from company_profile.models import EntityTypes


class SetupStatutoryEntityTypes:
    # @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        sid = transaction.set_autocommit(autocommit=False)

        choices = (10, 20, 30, 40, 50, 60, 70, 80, 90)

        for choice in choices:
            EntityTypes.objects.get_or_create(entity_type=choice)
            print(f"Statutory Entity type: {choice} is created")

        if "commit" in sys.argv:
            transaction.commit()
            print("Scuccessful commit")
        else:
            transaction.rollback(sid)
            print("Successful Dry-Run")
            
if __name__ == "__main__":
    SetupStatutoryEntityTypes().handle()
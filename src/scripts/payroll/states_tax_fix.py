import sys
import os
import django
import traceback


sys.path.append('./')


if __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()

from django.db import transaction
from payroll.models import StatesTaxConfig
from payroll.management.commands.tax_config_json import state_taxes_dict


class StateTaxFix:
    """
    this class is used to fix the state tax config if any new state is added
    """
    # @transaction.atomic
    def main(self, commit):
        try:
            sid = transaction.set_autocommit(autocommit=False)
            for state in StatesTaxConfig.state_choices:
                obj, created = StatesTaxConfig.objects.get_or_create(state = state[0], defaults={'tax_config':{state[0]:state_taxes_dict.get(state[0],{})}})
                print(f"state {state[0]} is {created} ")

            if commit=="commit":
                print("in commit")
                transaction.commit()
                # self.stdout.write(self.style.SUCCESS("Scuccessful commit"))
                print("in commit")
            else:
                transaction.rollback(sid)
                # self.stdout.write(self.style.WARNING("Successful Dry-Run"))
                print("in dry run")        
        
        except Exception as e:
            print(f'{e} Error: {traceback.format_exc()}')


if __name__ == "__main__":
    commit = sys.argv[2]
    StateTaxFix().main(commit)
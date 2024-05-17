from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from payroll.models import StatesTaxConfig,  Regime, HealthEducationCess, ProfessionTax
from .tax_config_json import state_taxes_dict
from core.utils import timezone_now

class Command(BaseCommand):


    help = "manage.py for payroll initial setup --commit"

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
        sid = transaction.set_autocommit(autocommit=False)

        #HealthEducationCess data setup
        HealthEducationCess.objects.all().delete()
        
        HealthEducationCess.objects.create(health_education_name="hec", health_education_cess= "0.04", health_education_month_year = timezone_now().date())

        #Regime data setup
        Regime.objects.all().delete()
        old_regime_data = {"1000000" : 0.30, "500000" : 0.20, "250000" : 0.05}
        new_regime_data = {"1500000" : 0.30, "1200000" : 0.20, "900000": 0.15, "600000": 0.10, "300000": 0.05,}
        Regime.objects.create(regime_name="new",regime_month_year='2023-04-01', salary_range_tax = new_regime_data)
        Regime.objects.create(regime_name="old",regime_month_year='2022-04-01', salary_range_tax = old_regime_data)
        
        #states tax config data setup
        StatesTaxConfig.objects.all().delete()
        state_tax_config_lst=[]
        for state in StatesTaxConfig.state_choices:
            state_tax_config_lst.append(StatesTaxConfig(state=state[0], tax_config = state_taxes_dict.get(state[0],{})))
        StatesTaxConfig.objects.bulk_create(state_tax_config_lst)
        # ProfessionTax.objects.all().delete()


        if options["commit"]:
            transaction.commit()
            self.stdout.write(self.style.SUCCESS("Scuccessful commit"))
        else:
            transaction.rollback(sid)
            self.stdout.write(self.style.WARNING("Successful Dry-Run"))

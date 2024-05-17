import traceback
from typing import Any, Optional

from django.apps import apps
from django.core.management.base import BaseCommand, CommandParser

from core.utils import load_class, timezone_now
from HRMSApp.models import FutureModule
from directory.models import EmployeeReportingManager, ManagerType, Employee
from django.db import transaction

class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--commit",
            "-c",
            default=False,
            action="store_true",
            dest="commit",
            help="Commit into DB",
        )

    # @transaction.atomic()
    def handle(self, *args: Any, **options: Any):
        sid = transaction.set_autocommit(autocommit=False)
        futures = FutureModule.objects.filter(
            status=FutureModule.QUEUE, effective_date__lte=timezone_now().date()
        )

        for module in futures:
            try:
                ct = module.content_type
                payload = module.payload
                model = apps.get_model(app_label=ct.app_label, model_name=ct.model)  #model coming
                qs: Employee = model.objects.filter(id__in=payload["id"])
                if "manager_details" in payload:
                    if payload['manager_details'].get("reporting_manager"):
                        reporting_manager_id = int(payload["manager_details"]["reporting_manager"])
                        employee_ids = payload["id"]
                        manager_type_first = ManagerType.objects.filter(manager_type=10).first()
                        EmployeeReportingManager.objects.filter(id__in = employee_ids).delete()
                        if reporting_manager_id in employee_ids: employee_ids.remove(reporting_manager_id)
                        objs = [EmployeeReportingManager(manager_type=manager_type_first,employee_id=employee_id,manager_id=reporting_manager_id) for employee_id in employee_ids]
                        EmployeeReportingManager.objects.bulk_create(objs)
                for instance in qs:
                    serializer = load_class(module.serializer)(
                        instance=instance, data=payload, partial=True
                    )
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()
                    module.status = FutureModule.SUCCESS

            except Exception:
                traceback.print_exc()
                module.logs = traceback.format_exc()
                module.status = FutureModule.FAIL

            module.save()

        if options["commit"]:
            transaction.commit()
            self.stdout.write(self.style.SUCCESS("future modules run created successfully!"))
        else:
            transaction.rollback(sid)
            self.stdout.write(self.style.WARNING("Dry Run!"))
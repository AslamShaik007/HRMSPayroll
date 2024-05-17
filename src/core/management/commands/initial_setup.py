from typing import Any, Optional

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser
from django.db import connections
from django.conf import settings


class Command(BaseCommand):
    help = "manage.py initial_setup --commit"

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
            "--db_name",
            "-dname",
            dest="Database name",
            default=False,
            help="company to Run initial Setup",
        )

    def handle(self, *args: Any, **options: Any):
        try:
            commit = options["commit"]
            db_name = options.get('db_name', settings.DATABASES['default']['NAME'])
            connections.databases['default']['NAME'] = db_name
            print("Database: ", db_name)
            call_command("tax_config",commit=commit)
            call_command("setup_form_choices", commit=commit)
            call_command("setup_employee_types", commit=commit)
            call_command("setup_statutory_entity_types", commit=commit)
            call_command("setup_bank_account_types", commit=commit)
            call_command("setup_auditor_types", commit=commit)
            # call_command("setup_roles", commit=commit)
            call_command("setup_manager_types", commit=commit)
            call_command("setup_relationship_types", commit=commit)
            call_command("setup_qualification_types", commit=commit)
            call_command("setup_course_types", commit=commit)
            call_command("setup_document_types", commit=commit)
            call_command("setup_certification_course_types", commit=commit)
            # call_command("setup_investment_declaration_types", commit=commit)
            call_command("setup_subform_choices", commit=commit)
            
            self.stdout.write(
                self.style.SUCCESS("Intials Setup was executed successfully")
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Something went wrong: \n {e}"))

from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction


UserModel = get_user_model()


class Command(BaseCommand):
    """
    Command to setup superuser

    AJAY, 02.01.2023
    """

    help = "manage.py setup_superuser --commit"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--password",
            "-p",
            default="pss@2023!",
            help="Password for super user. (Default: `pss@2023!`)",
        )

        parser.add_argument(
            "--email",
            "-e",
            default="hrms_support@pss.com",
            help="username/email for super user. (Default: `hrms_support@pss.com`)",
        )

        parser.add_argument(
            "--commit",
            "-c",
            action="store_true",
            dest="commit",
            default=False,
            help="Confirmation to save super user.",
        )

    # @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        """
        Default Handler

        Returns:
            Optional[str]: _description_
        """
        sid = transaction.set_autocommit(autocommit=False)
        email = options["email"]

        try:
            UserModel.objects.create_superuser(
                email=email, username=email, password=options["password"]
            )
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Error while creating super user: \n {e} \n ")
            )

        if options["commit"]:
            transaction.commit()
            self.stdout.write("Super user created successfully!")
        else:
            transaction.rollback(sid)
            self.stdout.write("Dry - Run!")

import sys
import os
import django
import logging
import psycopg2

sys.path.append('./')
if __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
from django.core.management import call_command
from django.conf import settings

logger = logging.getLogger('django')

class MigrationRun:
    def main(self):
        logger.critical(f"Called Migrations: {django.db.connections.databases['default']['NAME']}")
        
        commit = "commit"


        call_command('migrate')
        logger.critical("Migrations Were DONE")
        try:
            call_command("setup_form_choices", commit=commit)
            call_command("tax_config",commit=commit)
            
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
            logger.critical("Migrations Done")
        except Exception as e:
            logger.critical(f'Error in Run Migrations {e}')

if __name__ == "__main__":
    environment = sys.argv[1]
    print(environment, sys.argv)
    if len(sys.argv) == 2:
        
        conn = psycopg2.connect(
            host=settings.DATABASES['default']['HOST'],
            database=settings.DATABASES['default']['NAME'],
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD']
        )
        cursor = conn.cursor()
        cursor.execute("SELECT datname FROM pg_database;")
        database_list = cursor.fetchall()
        chek_name = 'indianpayrollservice' if environment == 'qa' else 'bharatpayroll'
        for db in database_list:
            db_name = db[0]
            if chek_name in db_name:
                django.db.connections.databases['default']['NAME'] = db_name

                django.db.connections.databases['default']['PASSWORD'] = settings.DATABASES["default"]["PASSWORD"]
                MigrationRun().main()
        cursor.close()
        conn.close()
    else:
        db_name = sys.argv[2]
        print(db_name)
        django.db.connections.databases['default']['NAME'] = db_name
        django.db.connections.databases['default']['PASSWORD'] = settings.DATABASES["default"]["PASSWORD"]
        MigrationRun().main()
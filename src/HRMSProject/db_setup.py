import sys
import os
import django
import logging
import requests
import time
import subprocess
import psycopg2
import requests
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from godaddypy import Client, Account
from rest_framework.views import APIView
from rest_framework import status, response, permissions

import django
from django.core.management import call_command
from django.conf import settings
from django.db import transaction
from django.utils.text import slugify

from HRMSProject.company_setup import get_domain
from HRMSApp.serializers import CompanyDetailsSerializer
from HRMSApp.renderers import UserRenderer
from HRMSApp.utils import Util
from billing.models import PlanDetail
from company_profile.models import CompanyDetails
from django.contrib.auth.models import User
from scripts.run_migrations import MigrationRun
from core.nginx_content import return_react_nginx_subdomain, return_django_nginx_subdomain
from alerts.utils import check_alert_notification
from HRMSProject.module_creation_script import module_sub_creation
from roles.models import SubModuleModelLeavelMapping

logger = logging.getLogger('django')


# curl -X GET -H "Authorization: sso-key 3mM44UdBRnDiFQ_VKppoRouVejewwwwbnw8g2:Nae55fXG7q1UuhKsTiy4Sp" "https://api.ote-godaddy.com/v1/domains/available?domain=mycv.ltd"
"""


api_key = 'gHzjd1fuHCAX_ErEMR2wAV1EiGKzdJxXGKb'
api_secret = 'WSMvxuR9nAdSgTdfzdULQg'
domain = 'mycv.ltd'  # Replace with your domain
subdomain_name = 'aslam'  # Replace with your desired subdomain

# Authenticate with GoDaddy API
account = Account(api_key, api_secret)
client = Client(account)

# Create the subdomain record
subdomain_payload = {
    'data': '38.143.106.25',  # Replace with the IP or destination for your subdomain
    'name': subdomain_name,
    'type': 'A',
    'ttl': 3600  # TTL (time to live) in seconds
}

try:
    client.add_record(domain, subdomain_payload)
    print(f"Subdomain '{subdomain_name}.{domain}' created successfully!")
except Exception as e:
    print(f"Failed to create subdomain: {e}")
"""

class DBCreation(APIView):
    permission_classes = (permissions.AllowAny, )
    renderer_classes = [UserRenderer]

    def create_connection(self, db_name):
        return psycopg2.connect(dbname=db_name,
            user=django.db.connections.databases['default']['USER'], host=django.db.connections.databases['default']['HOST'],
            password=django.db.connections.databases['default']['PASSWORD'])

    def post(self, request):
        # logger.critical(f'Parmeters: {params}')

        # company_name = params.get('company')
        # organization_name = params.get('org')
        # tenant_type = params.get('tenant_type', 'single_tenant')
        # logger.critical("Coming Here from central")
        # con = self.create_connection('indianhrms_db')
        # con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        # cur = con.cursor()
        # if tenant_type == 'single_tenant':
        #     sql_create = f"""CREATE DATABASE {organization_name}_db"""
        # else:
        #     sql_create = f"""CREATE DATABASE {company_name}_db"""
        # logger.critical(f'SQL_COMMAND: {sql_create}')

        # # DB is created and need to do migrations"
        # try:
        #     cur.execute(sql_create)
        # except Exception as e:
        #     logger.critical(e)
        # con.commit()
        # db_checks = """SELECT d.datname FROM pg_catalog.pg_database d ORDER BY 1;"""
        # db_tabels = """SELECT table_catalog, table_name  FROM information_schema.tables WHERE table_schema='public';"""
        # cur.execute(db_checks)
        # db_data = [i[0] for i in cur.fetchall()]
        # logger.critical(f"DBS Present {db_data}")
        # if f'{organization_name}_db' not in db_data:
        #     try:
        #         cur.execute(sql_create)
        #     except Exception as e:
        #         logger.critical(e)
        #     logger.critical("Second Attempt to create DB")
        # con.commit()
        # con.close()
        # con = self.create_connection(f'{organization_name}_db')
        # cur = con.cursor()
        # logger.critical(f'DATABASE BEFORE {settings.DATABASES}')

        # if tenant_type == 'single_tenant':
        #     django.db.connections.databases['default']['NAME'] = f'{organization_name}_db'
        # else:
        #     django.db.connections.databases['default']['NAME'] = f'{company_name}_db'
        # logger.critical(f'DATABASE AFTER {settings.DATABASES}')

        # #if tenant_type != 'single_tenant':
        # #    django.db.connections.databases['default']['OPTIONS'] = {
        # #        'options': f"-c search_path={organization_name}_schema"
        # #   }
        # time.sleep(20)
        # try:
        #     call_command('migrate')
        #     cur.execute(db_tabels)
        #     table_data = [i for i in cur.fetchall()]
        #     logger.critical(f"DB Migrated {table_data}")
        # except Exception as e:
        #     logger.critical(f"Some Error: {e}")

        # try:
        #     MigrationRun().main()
        #     cur.execute(db_tabels)
        #     table_data = [i for i in cur.fetchall()]
        #     logger.critical(f"DB Migrated {table_data}")
        # except Exception as e:
        #     logger.critical(f"Some Error: {e}")
        # if len(table_data) == 0:
        #     time.sleep(5)
        #     logger.critical('first migration')
        #     try:
        #         MigrationRun().main()
        #         cur.execute(db_tabels)
        #         table_data = [i for i in cur.fetchall()]
        #         logger.critical(f"DB Migrated {table_data}")
        #     except Exception as e:
        #         logger.critical(f"Some Error: {e}")
        #     time.sleep(5)

        #     logger.critical('second migration')
        #     try:
        #         MigrationRun().main()
        #         cur.execute(db_tabels)
        #         table_data = [i for i in cur.fetchall()]
        #         logger.critical(f"DB Migrated {table_data}")
        #     except Exception as e:
        #         logger.critical(f"Some Error: {e}")
        #     time.sleep(5)

        #     logger.critical('third migration')

        # con.close()
        # django.db.connections.close_all()

        return response.Response(
            # f'{organization_name}_db', status=status.HTTP_200_OK
        )

class CentralCompanyCreationAPIView(APIView):
    permission_classes = (permissions.AllowAny, )
    renderer_classes = [UserRenderer]

    def post(self, request):
        logger.critical(f'req URL {request.get_host()}')
        serializer = CompanyDetailsSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            instance = serializer.save()
            logger.critical(f'Company Details {instance}')
        else:
            logger.critical(f'SERIALIZER ERROR: {serializer.errors}')
            return response.Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )


class CreateCompany(APIView):
    """
    * on entering company data please check is given subdomain is already existed or not from main central.
    * get company data to create.
    * Create SubDomain First.
        Note: API KEY, Secret key, domain IP address required.
    -> if subdomain not added successfully
        show flag to customer, team will contact and in central create flag particualr compnay subdomain not added.
    -> else subdomain added successfully
        * Create Database with subdomain, domain.
            eg: subdomain: xyz, domain: abc, db_name: xyz_abc_db
        * DB name should be Copy of base_db.
        * with company data call CompanyDetailsSerializer(data=request.data)
        -> if error occurs
            show flag to customer, team will contact and in central create flag particualr compnay details not added but subdomain and db were created.
        -> else
            * Nginx Files should be add
            * Company and Main user will be created.
            * Run Roles script python roles/module_sub_creation.py {env} {db_name}
            * provide credentials to enrolled customer
            * if any needed things to update in central portal do things here.
            * Happy Hacking!!!
            '
    """


    def get_public_ip(self):
        try:
            response = requests.get('https://api.ipify.org?format=json')
            if response.status_code == 200:
                data = response.json()
                return data['ip']
            else:
                return "Failed to fetch IP"
        except requests.RequestException as e:
            return f"Request Exception: {e}"

    def add_subdomain(self, domain, subdomain_name, public_ip):
        api_key = '9EJWgbJVhWL_HWG954vVhC2FDAsA91WXAL'
        api_secret = 'GbZmU93rRw86yXwo6Jmuqt'

        account = Account(api_key, api_secret)
        client = Client(account)

        # Create the subdomain record
        subdomain_payload = {
            'data': public_ip,
            'name': subdomain_name,
            'type': 'A',
            'ttl': 600
        }

        try:
            client.add_record(domain, subdomain_payload)
            logger.critical(f"Subdomain '{subdomain_name}.{domain}' created successfully!")
            return True
        except Exception as e:
            logger.critical(f"Failed to create subdomain: {e}")
            return False

    def create_connection(self):
        return psycopg2.connect(dbname='postgres',
            user=django.db.connections.databases['default']['USER'], host=django.db.connections.databases['default']['HOST'],
            password=django.db.connections.databases['default']['PASSWORD'])

    def nginx_files_configure(self, sub_domain, domain, extension):
        # Nginx File Creations
        # for frontend
        front_end_file_name = f"/etc/nginx/sites-available/{sub_domain}_{domain}_react"
        back_end_file_name = f"/etc/nginx/sites-available/{sub_domain}_{domain}_django"
        front_end_nginx = return_react_nginx_subdomain(f'{sub_domain}.{domain}.{extension}')
        back_end_nginx = return_django_nginx_subdomain(f'{sub_domain}.{domain}.{extension}')
        front_end_command = f"sudo sh -c 'echo \"{front_end_nginx}\" >> {front_end_file_name} && sudo touch {front_end_file_name}'"
        back_end_command = f"sudo sh -c 'echo \"{back_end_nginx}\" >> {back_end_file_name} && sudo touch {back_end_file_name}'"
        subprocess.run(front_end_command, shell=True)
        subprocess.run(back_end_command, shell=True)
        subprocess.run(f'sudo chmod +x {front_end_file_name}', shell=True)
        subprocess.run(f'sudo chmod +x {back_end_file_name}', shell=True)
        subprocess.run(f'sudo ln -s {front_end_file_name} /etc/nginx/sites-enabled/', shell=True)
        subprocess.run(f'sudo ln -s {back_end_file_name} /etc/nginx/sites-enabled/', shell=True)

    def calling_central(self, customer_id, setup_status, flag, calling_flag):
        try:
            url = f'http://54.210.248.129:85/apiV1/customer-status-update/{customer_id}/'

            headers = {
                # Add any headers if needed
            }

            data = {
                'current_setup_status': setup_status,
            }
            data[calling_flag] = flag

            # response = requests.patch(url, data=data, headers=headers)

            print(response.status_code)
            print(response.text)
        except Exception as e:
            print(e)

    def create_company(self, com_url, data):
        logger.info(com_url)
        response = requests.post(f'http://{com_url}/api/user/register/', json=data)
        logger.critical(f"Company {response.status_code}")


    def post(self, request, *args, **kwargs):
        environ = os.environ.get('APP_ENV', 'prod')
        data = request.data
        # if environ == "prod":
        #    requested_domain = request.get_host()
        # else:
        #    requested_domain = "mycv.ltd"
        # host name:: test.indianhr.in default
        # domain = slugify(requested_domain.split('.')[-2])
        # extension = requested_domain.split('.')[-1]
        domain, extension = get_domain(environ)
        environ = 'prod'
        public_ip = self.get_public_ip()
        logger.critical(f"Public IP: {public_ip}")
        if domain is None:
            return response.Response(
                "Domain Can be added in Production and QA environments only."
            )
        """
        data = {
                "company_name": "Test PVT LTD",
                "sub_domain": "test",
                "brand_name": "TES",
                "is_multitenant": True,
                
                "plan_type": "hrms" / " " / "integrated",
                "reg_details": {
                    "email": "test@admin.com",
                    "name": "Admin",
                    "terms_and_conditions": true,
                    "phone": "7013111555",
                    "company_size": "11-20",
                    "password": "Test@123"
                }
            }
        """
        logger.critical(data)
        sub_domain = slugify(data.pop('sub_domain'))
        customer_id = None
        op = {
            "message": "Failed",
            "is_subdomain_added": False,
            "is_db_created": False,
            "is_company_created": False,
            "redirection_link": None
        }
        if "customer_id" in data:
            customer_id = data.pop('customer_id')
        plan_type = None
        if "plan_type" in data:
            plan_type = data.pop("plan_type")
            logger.critical(plan_type)
            if 'hrms' in plan_type.lower() and 'integrate' not in plan_type.lower():
                plan_type = 'hrms'
            elif 'payroll' in plan_type.lower() and 'integrate' not in plan_type.lower():
                plan_type = 'payroll'
            else:
                plan_type = 'integrated'
        data['plan_type'] = plan_type
        logger.info(domain)
        logger.info(extension)
        logger.info(sub_domain)
        is_subdomain_added = self.add_subdomain(f'{domain}.{extension}', sub_domain, public_ip)
        if not is_subdomain_added:
            logger.critical("show flag to customer, team will contact and in central create flag particualr compnay subdomain not added")
            logger.critical("Call some central API, when domain added from central Call this API.")            
            return response.Response(
                op, status=400
            )
        op['is_subdomain_added'] = True

        new_db_name = f"{sub_domain}_{domain}_db"
        pg_connection = self.create_connection()
        pg_connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = pg_connection.cursor()
        sql_create = f"""CREATE DATABASE {new_db_name} WITH TEMPLATE base_db OWNER {django.db.connections.databases['default']['USER']};"""
        logger.critical(f'SQL_COMMAND: {sql_create}')

        try:
            cursor.execute(sql_create)
            cursor.execute(f"""ALTER DATABASE {new_db_name} OWNER TO {django.db.connections.databases['default']['USER']};""")
            op['is_db_created'] = True

        except Exception as e:
            print(e)
            logger.critical(e)
            return response.Response(
                op, status=400
            )
        pg_connection.commit()
        pg_connection.close()
        logger.critical(f"DB Created {new_db_name}")
        self.nginx_files_configure(sub_domain, domain, extension)
        subprocess.run('sudo systemctl reload nginx', shell=True)
        # time.sleep(5)
        logger.critical("Nginx Were Loaded")
        django.db.connections.databases['default']['NAME'] = new_db_name
        settings.DATABASES["default"]["NAME"] = new_db_name
        logger.critical(f"Current DB {django.db.connections.databases['default']['NAME']}")
        call_command('migrate', '--fake')
        subprocess.run(f'python scripts/run_migrations.py {environ} {new_db_name}', shell=True)
        """
        call_command('migrate', 'contenttypes', 'zero')
        call_command('makemigrations', 'contenttypes')
        call_command('migrate', 'contenttypes')

        call_command('migrate', '--fake-initial',  'contenttypes')
        """
        # DATABASE CREATION COMPLETED
        unique_company_id = "%s%s" % (
            sub_domain.capitalize(),
            "001"
        )
        uid = 1
        while True:
            cmps = CompanyDetails.objects.filter(
                company_id = unique_company_id
            )
            if cmps.exists():
                uid += 1
            else:
                break
        cmp_id = "{:02d}".format(uid)
        unique_company_id = "%s%s" % (
            sub_domain.capitalize(),
            cmp_id
        )
        data["company_uid"] = unique_company_id
        data["company_id"] = unique_company_id
        context = {"plan_type": plan_type }
        logger.info(data)
        serializer = CompanyDetailsSerializer(data=data,context=context)
        if serializer.is_valid(raise_exception=True):
            try:
                instance = serializer.save(company_uid=unique_company_id)
                logger.critical(f'Company Details {instance}')
            except Exception as e:
                logger.critical(f'{e}')
                logger.info(sub_domain)
                logger.info(domain)
                logger.info(extension)
                logger.info(data)
                self.create_company(f'{sub_domain}.{domain}.{extension}', data)
        else:
            # time.sleep(10)
            try:
                company_status = self.create_company(f'{sub_domain}.{domain}.{extension}', data)
            except Exception as e:
                logger.critical(f'SERIALIZER ERROR: {serializer.errors} WEB ERROR :: {e}')
                
                return response.Response(
                    op, status=400
                )
            logger.critical(f'SERIALIZER ERROR: {serializer.errors}')
            return response.Response(
                op, status=400
            )
        op['is_company_created'] = True
        self.calling_central(customer_id, "company_created", True, "is_company_created")
        logger.critical(CompanyDetails.objects.all())
        logger.critical("module submodule creation started")
        module_sub_creation(
            environ,
            new_db_name
        )
        logger.critical("module submodule creation ended")
        logger.critical(SubModuleModelLeavelMapping.objects.filter().count())
        # logger.critical(f"Current Plan type {plan_type}, DB:: {django.db.connections.databases['default']['NAME']}")
        # django.db.connections.databases['default']['NAME'] = new_db_name
        # PlanDetail.objects.get_or_create(plan_type=plan_type)
        # logger.critical(PlanDetail.objects.all())
        # fstring = f"python roles/module_sub_creation.py {environ} {new_db_name}"
        # logger.critical("fstring things", fstring)
        # process = subprocess.Popen(
        #     f"python roles/module_sub_creation.py {environ} {new_db_name}", 
        #     shell=True, 
        #     stdout=subprocess.PIPE, 
        #     stderr=subprocess.PIPE
        # )
        # stdout, stderr = process.communicate()
        # logger.critical(stdout.decode())
        # logger.critical(stderr.decode())
        # subprocess.run(f"python roles/module_sub_creation.py {environ} {new_db_name}", shell=True)
        # Email Sending
        mail_data = {
            'to_email': data['reg_details']['email'],
            'body': f"""
    Dear {data['reg_details']['name']}, <br><br>

    Thank you for registering with  <a href="https://bharatpayroll.com">BharatPayroll.com</a>! We are thrilled to welcome you on board. You are now set to streamline your HRMS and Payroll processes with ease. <br><br>

    Your account has been successfully created, and you are all set to access our comprehensive suite of tools and features designed to make your HR and payroll management as efficient as possible. <br><br>

    Here are your login details:<br>
    Username: {data['reg_details']['email']}<br>
    Login link: https://{sub_domain}.{domain}.{extension}<br><br>

    To get started, simply log in at subdomain.bharatpayroll.com. This link will take you directly to the company setup page where you can enter your mandatory information and dive into our applications.<br><br>

    We are committed to providing you with a seamless and productive experience. If you have any questions or need assistance, our support team is just an email or phone call away. We're here to ensure your HRMS and Payroll operations run smoothly.<br><br>

    Thank you for choosing BharatPayroll.com. We look forward to supporting your business's growth and success.<br><br><br>


    Best regards,<br>
    <a href="https://bharatpayroll.com">BharatPayroll.com</a> Team<br><br>

""",
            'subject': 'Welcome Aboard! Your BharatPayroll.com Account is Ready to Use',
        }
        try:
            # if check_alert_notification("Company Profile",'Sign Up', email=True):
            Util.send_email(mail_data, is_content_html=True)
        except Exception as e:
            logger.critical(f'Error in sending Email :: {e}')
            pass
        op['message'] = 'success'
        op['redirection_link'] = f'http://{sub_domain}.{domain}.com'
        op["company_uid"] = unique_company_id
        return response.Response(
            op, status=200
            )

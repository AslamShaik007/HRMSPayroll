import os
from django.conf import settings
from django.db import connections
import logging
from django.http import Http404
from directory.models import Employee

logger = logging.getLogger('django')


class MultitenantSetup:
    """
    create_to_connection
    go_to_old_connection
    replace_request_user
    """
    
    def fetching_env(self):
        # return None
        return os.environ.get('APP_ENV', 'prod')
    
    
    def create_to_connection(self, request):
        headers = request.headers
        env = self.fetching_env()
        domain = headers.get('X-SELECTED-COMPANY')
        logger.info(domain)
        db_to_connect = connections['default'].settings_dict['NAME']
        if domain != '' and domain is not None:
            if env == 'local' or env == 'prod':
                db_to_connect = f'{domain}_indianpayroll_db'
            if env == 'qa':
                db_to_connect = f'{domain}_indianpayrollservice_db'
        logger.info(db_to_connect)
            
        connections['default'].settings_dict['NAME'] = db_to_connect
        settings.DATABASES["default"]["NAME"] = db_to_connect
        # # print("default",settings.DATABASES["default"] )
        connections['default'].close()
        
    def get_domain_connection(self, request=None, domain=None):
        #return None
        env = self.fetching_env()
        db_to_connect = connections['default'].settings_dict['NAME']
        if domain != '' and domain is not None:
            if env == 'local' or env == 'prod':
                db_to_connect = f'{domain}_indianpayroll_db'
            if env == 'qa':
                db_to_connect = f'{domain}_indianpayrollservice_db'
        print("db to connect", db_to_connect)
            
        connections['default'].settings_dict['NAME'] = db_to_connect
        settings.DATABASES["default"]["NAME"] = db_to_connect
        # print("default",settings.DATABASES["default"] )
        connections['default'].close()
        
        
    
        # connections['default'].close()
    
    
    def go_to_old_connection(self, request):
        headers = request.headers
        env = self.fetching_env()
        domain = headers.get('X-CURRENT-COMPANY')
        db_to_connect = connections['default'].settings_dict['NAME']
        if domain != '' and domain is not None:
            if env == 'local' or env == 'prod':
                db_to_connect = f'{domain}_indianpayroll_db'
            if env == 'qa':
                db_to_connect = f'{domain}_indianpayrollservice_db'
        connections.databases['default']['NAME'] = db_to_connect
        settings.DATABASES["default"]["NAME"] = db_to_connect
        connections['default'].close()
        return None
    
    def replace_request_user(self, request):
        headers = request.headers
        employee_id = headers.get('X-CURRENT-EMPLOYEE')
        emp = Employee.objects.filter(work_details__employee_number=employee_id).first()
        # print("empdsd", emp)
        if emp is not None:
            return emp.user
        return None
        #return None
    
    def main(self, request):
        # return None
        
        return

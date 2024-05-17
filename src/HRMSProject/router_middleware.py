import os
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.db import connections
import logging
from django.http import Http404

logger = logging.getLogger('django')

def get_user_ip(request):
    # Iterate through request.META to find the relevant keys
    for key, value in request.META.items():
        if 'HTTP_' in key and 'IP' in key:
            # Print keys containing 'HTTP_' and 'IP' for inspection
            print(f"{key}: {value}")
    
    # If the IP address is found, return it or handle it accordingly
    # Otherwise, return a message indicating the IP address couldn't be retrieved
    user_ip = "User's IP address not found"
    return user_ip

class XHeaderMiddleware(MiddlewareMixin):
    
    @staticmethod
    def hostname_from_request(request):
        """ Extracts hostname from request. Used for custom requests filtering.
            By default removes the request's port and common prefixes.
        """
        # hostname = request.headers.get('X-Csrftoken')
        # if hostname is None:
        """
        
        env prod
        indianhr_db
        # domain = mycompdomain
        # orgs = vitelglobal, pss
        
        # pss.indianhr.in
        # mycompdomain.indianhr.in
        
        mycompdomain_indianhr_db
            - pss_indianhr_db
        
        """
        hostname = None
        env = os.environ.get('APP_ENV', 'local')
        if 'whytelglobal' in request.get_host() or 'indianhr' in  request.get_host() or 'indianpayrollservice' in request.get_host() or 'bharatpayroll' in request.get_host():
            hostname = request.get_host()
            
        if not hostname:
            # logging.warning(f"schema name not found - {hostname}")
            return settings.DATABASES['default']['NAME'], None
            # return settings.DATABASES['pss']['NAME'], None
            # return settings.DATABASES['vg']['NAME'], None
            # return settings.DATABASES['vd']['NAME'], None
            # return settings.DATABASES['vgts']['NAME'], None
        split_schema = hostname.split('.')
        if env == 'local' or env == 'dev':
            return settings.DATABASES['default']['NAME'], None
        if env == 'qa':
            if len(split_schema) == 2:
                return 'indianhrms_db', None
            elif len(split_schema) == 3:
                return f'{split_schema[0]}_{split_schema[-2]}_db', None
            elif len(split_schema) == 4:
                # kumar.raju.ihr.com
                return f'{split_schema[1]}_whytelglobal_db', f'{split_schema[1]}_{split_schema[0]}_ihr_schema'
        if env == 'prod':
            # TODO write api to fetch orgs and domains if domain name matches it should be major Dashboard if org name matches have 
            # TODO fetch domain and combination with db name
            return f'{split_schema[0]}_{split_schema[-2]}_db', None

        raise Http404(f"schema name not found - {request.get_host()}")

    def process_request(self, request):
        db_creds = self.hostname_from_request(request)
        # logger.critical(f"ENV: {os.environ.get('APP_ENV', 'local')} Connecting DB: {db_creds}")
        connections.databases['default']['NAME'] = db_creds[0]
        settings.DATABASES["default"]["NAME"] = db_creds[0]
        if db_creds[1] is not None:
            connections.databases['default']['OPTIONS'] = {
            'options': f"-c search_path={db_creds[1]}"
        }
        return None

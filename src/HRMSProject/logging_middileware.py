import datetime
import logging
import json

from django.utils.deprecation import MiddlewareMixin

from company_profile.models import LoggingRecord
from core.utils import get_ip_address

logger = logging.getLogger('django')

class LogggingMiddleware(MiddlewareMixin):
    """
    Get Request At mid and Add Record in AuditLog
    """
    
    def process_request(self, request):
        try:
            if request.method in ["GET"] and 'db_setup' not in request.build_absolute_uri():
                temp_resp = {}
                try:
                    temp_resp['user'] = request.user
                    temp_resp['user_name'] = request.user.username
                    temp_resp['end_point'] = request.build_absolute_uri()
                    temp_resp['ip_address'] = get_ip_address(request)
                    temp_resp['method'] = request.method
                    try:
                        if request.method == "GET":
                            temp_resp['payload'] = "[]"
                        else:
                            temp_resp['payload'] = f'{json.loads(request.body)}'
                    except Exception:
                        temp_resp['payload'] = "[]"
                    temp_resp['is_success_entry'] = True
                    temp_resp['company_name'] = request.user.employee_details.first().company.company_name
                    
                except Exception as e:
                    temp_resp['user_name'] = ''
                    temp_resp['end_point'] = request.build_absolute_uri()
                    temp_resp['ip_address'] = get_ip_address(request)
                    temp_resp['method'] = request.method
                    try:
                        if request.method == "GET":
                            temp_resp['payload'] = "[]"
                        else:
                            temp_resp['payload'] = f'{json.loads(request.body)}'
                    except Exception:
                        temp_resp['payload'] = "[]"
                    temp_resp['is_success_entry'] = False
                    temp_resp['error_details'] = str(e)
                    temp_resp['company_name'] = ''
                LoggingRecord.objects.create(**temp_resp)
        except Exception:
            pass
        return None

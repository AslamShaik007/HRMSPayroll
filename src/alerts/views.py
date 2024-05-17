import os
import psycopg2

from django.db import connections
from django.db import models as db_models
from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.utils.text import slugify

from rest_framework.views import APIView
from rest_framework import status, response

from core.utils import error_response, success_response

from alerts.models import Alert
from alerts.utils import INITIAL_ALERTS_DATA, NOTIFICATION_ALERTS_DATA
from HRMSApp.models import Roles

class AlertApiView(APIView):
    
    model = Alert
    
    def get(self, request, *args, **kwargs):
        op_data = {}
        initial_data = INITIAL_ALERTS_DATA['alerts']
        existed_data = list(self.model.objects.all().values_list('name', flat=True))
        op_data.update(initial_data)
        exist_mods = self.model.objects.filter(name__in=existed_data).annotate(
            role_names=ArrayAgg('roles__name')
        ).values(
            'desc_name', 'path', 'name', 'description', 'role_names', 'interval', 'days', 'week_days', 'is_active', 'run_time'
        )
        for mod in exist_mods:
            op_data[mod['name']] = {
                "desc_name": mod['desc_name'],
                'path': str(mod['path']),
                'description': mod['description'], # 'Some Desc',
                'roles': mod['role_names'], # [],
                'interval': mod['interval'], # '',
                'run_time': mod['run_time'], # [],
                'days': mod['days'], # [],
                'week_days': mod['week_days'], # [],
                'is_active': mod['is_active'], 
            }        
        return response.Response(
            success_response(op_data, "Successfully fetched details", 200), status=status.HTTP_200_OK)

    def put(self, request):
        init_data = INITIAL_ALERTS_DATA['alerts']
        data = request.data
        db_name = connections.databases['default']['NAME']
        company = slugify(request.user.employee_details.first().company.company_name)
        alert_conn = psycopg2.connect(dbname='alert_cron_db',
            user=connections.databases['default']['USER'],
            host=connections.databases['default']['HOST'],
            password=connections.databases['default']['PASSWORD']
        )
        for data_val in data:
            obj, is_created = self.model.objects.get_or_create(name=data_val['name'])
            existing_roles = obj.roles.all().values_list('id', flat=True)
            new_roles = Roles.objects.filter(name__in=data_val['roles']).values_list('id', flat=True)
            # if is_created:
            f_name = str(init_data[obj.name]['path']).split('/')[-1].split('.')[0]
            if not os.path.exists(f"{settings.BASE_DIR.parent}/logs/{company}/"):
                os.mkdir(f"{settings.BASE_DIR.parent}/logs/{company}/", mode = 0o777)
            obj.log_path = f"{settings.BASE_DIR.parent}/logs/{company}/{f_name}.log"
            obj.desc_name = init_data[obj.name]['desc_name']
            obj.path = init_data[obj.name]['path']
            obj.description = init_data[obj.name]['description']
            obj.db_name = db_name
            obj.interval = data_val['interval']
            obj.run_time = data_val['run_time']
            obj.days = data_val['days']
            obj.week_days = data_val['week_days']
            obj.is_active = data_val['is_active']
            obj.roles.remove(*existing_roles)
            obj.roles.add(*new_roles) 
            obj.save()
            alert_cursor = alert_conn.cursor()
            alert_cursor.execute(f"SELECT * FROM alert WHERE name = %s AND db_name = %s", (obj.name, db_name))
            existing_record = alert_cursor.fetchone()
            if existing_record:
                alert_cursor.execute("""
                    UPDATE alert
                    SET log_path = %s, interval = %s, run_time = %s, days = %s, week_days = %s, is_active = %s
                    WHERE name = %s AND db_name = %s
                """, (obj.log_path, obj.interval, obj.run_time, obj.days, obj.week_days, obj.is_active, obj.name, db_name))
            else:
                
                alert_cursor.execute("""
                    INSERT INTO alert (name, db_name, log_path, path, description, interval, run_time, days, week_days, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (obj.name, db_name, obj.log_path, obj.path, obj.description, obj.interval, obj.run_time, obj.days, obj.week_days, obj.is_active))
            alert_conn.commit()
            alert_cursor.close()
        alert_conn.close()
        
        return response.Response(
            success_response([], "Successfully Updated", 200),
            status=status.HTTP_200_OK
        )



class NotificationAlertApiView(APIView):
    
    model = Alert
    
    def get(self, request, *args, **kwargs):
        initial_data = NOTIFICATION_ALERTS_DATA
        exist_mods = list(Alert.objects.filter(interval__isnull=True).annotate(sub_module_name = db_models.F('desc_name')).values('name','sub_module_name','is_whatsapp','is_email','is_sms'))
        
        exist_mods_dict = {(item['name'], item['sub_module_name']): item for item in exist_mods}

        default_values = {'is_whatsapp': False, 'is_email': False, 'is_sms': False}

        for item1 in initial_data:
            key = (item1['name'], item1['sub_module_name'])
            item2 = exist_mods_dict.get(key)
            if item2:
                item1.update(item2)
            else:
                item1.update(default_values)  
        return response.Response(
            success_response(initial_data, "Successfully fetched details", 200), status=status.HTTP_200_OK)
    
    def put(self, request, *args, **kwargs):
        request_data = request.data
        
        for alert_obj in request_data:
            obj, is_created = self.model.objects.get_or_create(name=alert_obj['name'], desc_name=alert_obj['sub_module_name'])
            obj.is_whatsapp = alert_obj['is_whatsapp']
            obj.is_email = alert_obj['is_email']
            obj.is_sms = alert_obj['is_sms']
            obj.save()
        return response.Response(
            success_response([], "Successfully Updated", 200),
            status=status.HTTP_200_OK
        )
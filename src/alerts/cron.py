import subprocess
import traceback
import logging
import sys
import django
import pandas as pd
import numpy as np
import os
import subprocess
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from django.conf import settings
from core.utils import timezone_now
from HRMSProject.alert_logs_setup import setup_logging
from alerts.postgres_configs import create_database, create_table

logger = setup_logging(log_file=f'{settings.BASE_DIR.parent}/logs/cron.log')

def hie(*args, **kwargs):
    logger.critical("Coming Here")
    logger.critical(f'Args:: {args}, Kwarhs:: {kwargs}')
    try:
        subprocess.run('/home/raju/Projects/hrms/.venv/bin/python /home/raju/Projects/hrms/src/check.py', shell=True)
    except Exception as e:
        logger.critical(str(traceback.format_exc()))

def get_env_file(env):
    if env == 'dev':
        return 'hrmsenv'
    if env == 'qa':
        return 'hrms_env'
    return '.venv'

def calling_alerts():
    logger.info("Running")
    try:
        c_time = timezone_now(tz=settings.TIME_ZONE)
        env = os.environ.get('APP_ENV', 'local')
        conn = psycopg2.connect(dbname=settings.DATABASES['default']['NAME'],
            user=django.db.connections.databases['default']['USER'],
            host=django.db.connections.databases['default']['HOST'],
            password=django.db.connections.databases['default']['PASSWORD'])
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        cursor.execute("""SELECT datname FROM pg_database WHERE datistemplate = false;""")
        rows = cursor.fetchall()
        db_names = [i[0] for i in rows]
        cursor.close()
        if 'alert_cron_db' not in db_names:
            create_database()
            create_table()
        conn.close()
        
        alert_conn = psycopg2.connect(dbname='alert_cron_db',
            user=django.db.connections.databases['default']['USER'],
            host=django.db.connections.databases['default']['HOST'],
            password=django.db.connections.databases['default']['PASSWORD'])
        alert_cursor = alert_conn.cursor()
        alert_cursor.execute("""select * from alert where is_active=true""")
        data = alert_cursor.fetchall()
        column_names = [desc[0] for desc in alert_cursor.description]
        alert_cursor.close()
        alert_conn.close()
        df = pd.DataFrame(data, columns=column_names)
        # print(df[['name', 'run_time']])
        op_df =  df[df.apply(lambda x: c_time.strftime("%H:%M") in x['run_time'], axis=1)]
        # print(op_df)
        env_folder_name = get_env_file(env)
        for obj in op_df.to_dict('records'):
            if obj['interval'] == 'daily':
                try:
                    op_str = f"cd {str(settings.BASE_DIR.parent.parent)} && . {env_folder_name}/bin/activate && cd src && python {obj['path']} {env} commit {obj['db_name']} >> {obj['log_path']} 2>&1"
                  
                    logger.info(op_str)
                    subprocess.run(op_str, shell=True)
                except Exception as e:
                    logger.error(f'{e} - {traceback.format_exc()}')
            if obj['interval'] == 'weekly' and c_time.strftime("%a") in obj['week_days']:
                try:
                    op_str = f"cd {str(settings.BASE_DIR.parent.parent)} && . {env_folder_name}/bin/activate && cd src && python {obj['path']} {env} commit {obj['db_name']} >> {obj['log_path']} 2>&1"
                    logger.info(op_str)
                    subprocess.run(op_str, shell=True)
                except Exception as e:
                    logger.error(f'{e} - {traceback.format_exc()}')               
            if obj['interval'] == 'monthly' and c_time.day in obj['days']:
                try:
                    op_str = f"cd {str(settings.BASE_DIR.parent.parent)} && . {env_folder_name}/bin/activate && cd src && python {obj['path']} {env} commit {obj['db_name']} >> {obj['log_path']} 2>&1"
                    subprocess.run(op_str, shell=True)
                except Exception as e:
                    logger.error(f'{e} - {traceback.format_exc()}')                  
                    
                
    except Exception as e:
        logger.error(f'{e} - {traceback.format_exc()}')
        
# Jenkins QA Test 3
    
import subprocess
import traceback
import logging
import sys
import os

from HRMSProject.alert_logs_setup import  setup_logging

from alerts.models import Alert


def call_func(*args, **kwargs):
    
    objs = Alert.objects.all()
    
    
    
    logger = setup_logging()
    logger.critical("Coming Here")

    env = os.environ.get('APP_ENV', 'local')
    objs = Alert.objects.filter(is_active=True, is_deleted=False)
    try:
        subprocess.run(f'/home/raju/Projects/hrms/.venv/bin/python /home/raju/Projects/hrms/src/scripts/attendance/generate_anamolies.py {env} pss_db', shell=True)
    except Exception as e:
        logger.critical(str(traceback.format_exc()))

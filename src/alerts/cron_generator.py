import django
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from HRMSProject.alert_logs_setup import  setup_logging

from alerts.models import Alert
from alerts.postgres_configs import create_database, create_table

"""
* create alert_cron_db in postgres
* keys will be Copy Of Alert
* Cron will run for every minute
* check if there is active cron their or not, if present then it will run.



* Need to Add in CRONJOBS
* from cronjob need to call related call function.
    eg: alert.cron.generate_anamolies
    

"""
import psycopg2
from psycopg2 import sql


def create_connection():
    return psycopg2.connect(dbname='postgres',
        user=django.db.connections.databases['default']['USER'],
        host=django.db.connections.databases['default']['HOST'],
        password=django.db.connections.databases['default']['PASSWORD'])

pg_connection = create_connection()
pg_connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cursor = pg_connection.cursor()
cursor.execute("""SELECT datname FROM pg_database WHERE datistemplate = false;""")
rows = cursor.fetchall()
db_names = [i[0] for i in rows]
cursor.close()
if 'alert_cron_db' not in db_names:
    # create DB name
    create_database()
    create_table()

    
    

def generator_func(*args, **kwargs):
    op_generator = []
    objs = Alert.objects.filter(is_active=True)
    for obj in objs:
        print(obj.__dict__)
        if obj.interval == Alert.IntervalChoices.DAILY:
            # we will generate for Daily
            # /home/raju/Projects/hrms/.venv/bin/python /home/raju/Projects/hrms/src/scripts/attendance/generate_anamolies.py {env} pss_db
            # (
            #     '*/1 * * * *',
            #     f'alerts.cron.hie',
            #     f'>> {BASE_DIR.parent}/logs/cron.log 2>&1'
                
            # ),
            pass
        

        
        
        
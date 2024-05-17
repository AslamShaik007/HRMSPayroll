import django
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database():
    # Connect to the default database
    conn = psycopg2.connect(
        dbname="postgres",
        user=django.db.connections.databases['default']['USER'],
        host=django.db.connections.databases['default']['HOST'],
        password=django.db.connections.databases['default']['PASSWORD']
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Create the new database
    cur.execute(sql.SQL("""CREATE DATABASE {}""").format(sql.Identifier('alert_cron_db')))
    cur.close()
    conn.close()

def create_table():
    # Connect to the newly created database
    conn = psycopg2.connect(
        dbname="alert_cron_db",
        user=django.db.connections.databases['default']['USER'],
        host=django.db.connections.databases['default']['HOST'],
        password=django.db.connections.databases['default']['PASSWORD']
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Define the table creation query
    create_table_query = """
    CREATE TABLE alert (
        id SERIAL PRIMARY KEY,
        log_path TEXT,
        name VARCHAR(256),
        db_name VARCHAR(256) NOT NULL,
        path TEXT,
        description TEXT,
        interval VARCHAR(16),
        run_time TEXT[],  -- Array of strings
        days INTEGER[],
        week_days VARCHAR(8)[],
        is_active BOOLEAN DEFAULT FALSE,
        calling_func VARCHAR(256)
    )
    """

    # Execute the query to create the table
    cur.execute(create_table_query)
    cur.close()
    conn.close()

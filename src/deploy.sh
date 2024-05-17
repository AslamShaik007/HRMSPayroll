#!/bin/bash

echo $APP_ENV

if [ "$APP_ENV" = "dev" ]; then
    cd /var/www/html/hrms
    echo ENV IS $APP_ENV '&' $PWD 
    . hrmsenv/bin/activate
    cd src/
    git pull
    pip install -r ubuntu_requirements_lts.txt
    PG_USER="root"
    PG_HOST="localhost"
    PG_PORT="5432"
    PG_PASSWORD="Vitel@321"
    db_list=$(sudo PGPASSWORD="$PG_PASSWORD"  psql -U $PG_USER -h $PG_HOST -l | awk 'NR>2 {print $1}')
    for db_name in $db_list; do
        if [ -n "$(echo "$db_name" | grep 'indianhrms_db')" ]; then
            echo "$db_name"
            python scripts/run_migrations.py $APP_ENV $db_name
            python roles/module_sub_creation.py $APP_ENV $db_name
        fi
    done
    sudo systemctl restart gunicorn
    echo Completed
elif [ "$APP_ENV" = "qa" ]; then
    cd /var/www/html/hrms
    echo ENV IS $APP_ENV '&' $PWD 
    . hrms_env/bin/activate
    cd src/
    git pull
    pip install -r ubuntu_requirements_lts.txt
    PG_USER="root"
    PG_HOST="localhost"
    PG_PORT="5432"
    PG_PASSWORD="cjKMN554pRLnKhd3dbYcvGVDpHZ6B2TA7"
    db_list=$(sudo PGPASSWORD="$PG_PASSWORD"  psql -U $PG_USER -h $PG_HOST -l | awk 'NR>2 {print $1}')
    python scripts/run_migrations.py $APP_ENV base_db
    for db_name in $db_list; do
        if [ -n "$(echo "$db_name" | grep 'indianpayrollservice_db')" ]; then
            echo "$db_name"
            python scripts/run_migrations.py $APP_ENV $db_name
            python roles/module_sub_creation.py $APP_ENV $db_name
        fi
    done
    sudo systemctl restart gunicorn
    echo Completed
elif [ "$APP_ENV" = "prod" ]; then
    cd  /var/www/html/hrms
    echo ENV IS $APP_ENV '&' $PWD 
    . hrms_env/bin/activate
    cd src/
    git pull
    pip install -r ubuntu_requirements_lts.txt
    PG_USER="root"
    PG_HOST="localhost"
    PG_PORT="5432"
    PG_PASSWORD="oGf7S3d4sRth9lPPNAP4cqLkpv"
    db_list=$(sudo PGPASSWORD="$PG_PASSWORD"  psql -U $PG_USER -h $PG_HOST -l | awk 'NR>2 {print $1}')
    python scripts/run_migrations.py $APP_ENV base_db
    for db_name in $db_list; do
        if [ -n "$(echo "$db_name" | grep 'bharatpayroll_db')" ]; then
            echo "$db_name"
            python scripts/run_migrations.py $APP_ENV $db_name
            python roles/module_sub_creation.py $APP_ENV $db_name
        fi
    done
    sudo systemctl restart gunicorn
    echo Completed
elif [ "$APP_ENV" = "local" ]; then
    cd /home/raju/Projects/hrms/
    echo $PWD
    . .venv/bin/activate
    cd src/
    PG_USER="postgres"
    PG_HOST="localhost"
    PG_PORT="5432"
    PG_PASSWORD="Rajkumar35*"
    echo $PWD
    db_list=$(sudo PGPASSWORD="$PG_PASSWORD"  psql -U $PG_USER -h $PG_HOST -l | awk 'NR>2 {print $1}')
    for db_name in $db_list; do
        if [ -n "$(echo "$db_name" | grep 'pss')" ]; then
            echo "$db_name"
            python scripts/run_migrations.py $APP_ENV $db_name
        fi
    done
else
    echo "Values are not equal"
fi
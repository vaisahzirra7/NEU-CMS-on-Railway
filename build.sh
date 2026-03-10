#!/usr/bin/env bash
# build.sh — Render build script

# Start of code to extract the content of the database
# Run this code in your local environment to create a data.json file with the content of your database, then copy that file to the root of this project before deploying to Render.
# ---------------------------------------
# set "DJANGO_DB_ENGINE=django.db.backends.mysql"
# set "DJANGO_DB_NAME=your_local_db"
# set "DJANGO_DB_USER=your_user"
# set "DJANGO_DB_PASSWORD=your_password"
# set "DJANGO_DB_HOST=127.0.0.1"
# set "DJANGO_DB_PORT=3306"

# python -c "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings'); django.setup(); from django.core.management import call_command; call_command('dumpdata','--exclude','auth.permission','--exclude','contenttypes','--exclude','admin.logentry', stdout=open('data.json','w', encoding='utf-8'))"
# ----------------------------------------


# End of code to extract the content of the database


set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py create_superuser_env

# Automatically load the database dump if it exists
if [ -f data.json ]; then
    echo "Found data.json. Loading data into the database..."
    python manage.py loaddata data.json
    
    # Rename the file so it doesn't get loaded again on subsequent deployments
    # (or if Render crashes and restarts the instance).
    mv data.json data_loaded.json
    echo "Data loaded successfully and file renamed to prevent duplicate loads."
fi
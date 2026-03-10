#!/usr/bin/env bash
# build.sh — Render build script
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# Automatically load the database dump if it exists
if [ -f data.json ]; then
    echo "Found data.json. Loading data into the database..."
    python manage.py loaddata data.json
    
    # Rename the file so it doesn't get loaded again on subsequent deployments
    # (or if Render crashes and restarts the instance).
    mv data.json data_loaded.json
    echo "Data loaded successfully and file renamed to prevent duplicate loads."
fi
#!/bin/bash
set -e

export DJANGO_SETTINGS_MODULE=core.settings
echo "Starting Django application..."

# Wait for database
python -c "
import os
import django
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection
cursor = connection.cursor()
print('Database connection successful')
"

# Try to create tables if they don't exist, ignore errors if they do
python manage.py migrate --fake-initial 2>/dev/null || true

# Collect static files
python manage.py collectstatic --noinput

# Create superuser if needed (skip for now)

echo "Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 core.wsgi:application
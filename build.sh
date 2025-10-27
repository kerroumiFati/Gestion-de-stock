#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input --clear

# Run migrations
python manage.py migrate

# Create superuser automatically (disabled temporarily for debugging)
# python create_superuser.py

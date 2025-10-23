#!/bin/bash

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run migrations (if needed)
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Ensure static files are properly organized for Vercel
echo "Organizing static files for Vercel..."
ls -la staticfiles_build/

echo "Build completed successfully!"
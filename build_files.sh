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

# Create the static directory in the output for Vercel
echo "Organizing static files for Vercel..."
mkdir -p staticfiles_build/static
cp -r staticfiles_build/static/* staticfiles_build/static/ 2>/dev/null || true

echo "Build completed successfully!"
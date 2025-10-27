#!/usr/bin/env bash
# exit on error
set -o errexit

echo "===> Installing dependencies..."
pip install -r requirements.txt

echo "===> Python version:"
python --version

echo "===> Django version:"
python -m django --version

echo "===> Collecting static files..."
echo "STATIC_ROOT will be: $(python -c 'from Gestion_stock.settings import STATIC_ROOT; print(STATIC_ROOT)')"
python manage.py collectstatic --no-input --clear -v 2

echo "===> Listing collected files..."
ls -la staticfiles/ 2>/dev/null || echo "staticfiles directory not found!"

echo "===> Running migrations..."
python manage.py migrate

echo "===> Build completed successfully!"

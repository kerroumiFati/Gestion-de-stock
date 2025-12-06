#!/usr/bin/env python
"""
Script to create a superuser if it doesn't exist
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Superuser credentials from environment variables
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@gestionstock.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123456')

# Create superuser if it doesn't exist
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    print(f'✅ Superuser "{username}" created successfully!')
else:
    print(f'ℹ️ Superuser "{username}" already exists.')

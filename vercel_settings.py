# Vercel-specific settings that override main settings
import os
from Gestion_stock.settings import *

# Override BASE_DIR for Vercel
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Use a simple SQLite database for build process
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'build_db.sqlite3'),
    }
}

# Disable debug mode for production
DEBUG = False

# Add Vercel domain to allowed hosts
ALLOWED_HOSTS = ['*']  # For Vercel deployment

# Static files for Vercel
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_build', 'static')
STATICFILES_DIRS = []

# Create static directory if it doesn't exist
STATIC_DIR = os.path.join(BASE_DIR, 'static')
if os.path.exists(STATIC_DIR):
    STATICFILES_DIRS.append(STATIC_DIR)

# Ensure static files storage is properly configured
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
ALLOWED_HOSTS = ['*']

# Disable admin and database-dependent middleware
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
]]

MIDDLEWARE = [middleware for middleware in MIDDLEWARE if middleware not in [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]]
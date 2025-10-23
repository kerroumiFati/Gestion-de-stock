# Vercel-specific settings that override main settings
import os
from .settings import *

# Disable database operations for Vercel static deployment
DATABASES = {}

# Skip migrations on Vercel
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Static files for Vercel
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_build', 'static')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Security settings for production
DEBUG = False
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
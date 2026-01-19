# config/settings/test.py
"""
Test Settings Configuration

IMPORTANT: This configuration uses SQLite in-memory database for all tests.
This ensures tests never touch the production PostgreSQL database.
All database operations during testing are isolated and temporary.
"""

import sys

from .base import *  # noqa: F403

DEBUG = False

# Use faster password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Use in-memory SQLite for tests (fast and isolated)
# This overrides the PostgreSQL configuration from base.py
# Tests will NEVER use PostgreSQL - all data is in-memory and discarded after tests
# IMPORTANT: This ensures complete isolation from production/development PostgreSQL database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # In-memory database - no file, no persistence
        'OPTIONS': {
            # Ensure no file is created
            'timeout': 20,
        },
        # Explicitly prevent any connection to PostgreSQL
        'HOST': '',
        'PORT': '',
        'USER': '',
        'PASSWORD': '',
    }
}

# Ensure no other database connections exist
DATABASE_ROUTERS = []  # No custom routers that might route to PostgreSQL


# Celery - Run tasks synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Email - Use in-memory backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Cache - Use local memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}

# Disable Sentry in tests
SENTRY_DSN = ''


# Verify we're using SQLite (safety check)

if 'test' in sys.argv or 'pytest' in sys.modules:
    if 'postgresql' in DATABASES['default']['ENGINE']:
        raise RuntimeError(
            'CRITICAL: Test settings must use SQLite, not PostgreSQL! '
            'Tests should never touch the production database.'
        )


# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

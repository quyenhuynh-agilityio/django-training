from .base import *  # noqa: F403
from .base import INSTALLED_APPS, MIDDLEWARE, REST_FRAMEWORK

# ==============================
# DEBUG
# ==============================
# Enforce DEBUG=True in local development
DEBUG = True

# ==============================
# DEVELOPMENT TOOLS
# ==============================
INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

# Django Debug Toolbar
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# ==============================
# DRF - Enable Browsable API
# ==============================
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_RENDERER_CLASSES': [
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# ==============================
# CACHE & SESSION - No Redis required locally
# ==============================
# Use in-memory cache and DB sessions so the app works without Redis.
# Start Redis when you need Celery workers or Redis cache.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'KEY_PREFIX': 'studyportal',
        'TIMEOUT': 300,
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# ==============================
# CORS - Allow All Origins
# ==============================
# In development, allow all origins for easier testing
CORS_ALLOW_ALL_ORIGINS = True

# ==============================
# EMAIL
# ==============================
# Inherit EMAIL_BACKEND from base.py (SMTP by default),
# but you can still override via EMAIL_BACKEND in the local .env if needed.

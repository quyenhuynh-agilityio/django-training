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
# CORS - Allow All Origins
# ==============================
# In development, allow all origins for easier testing
CORS_ALLOW_ALL_ORIGINS = True

# ==============================
# EMAIL - Console Backend
# ==============================
# Always use console backend in local (prints to terminal)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

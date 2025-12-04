# config/settings/production.py
import environ

from .base import *  # noqa: F403

DEBUG = False
env = environ.Env(DEBUG=(bool, False))
# ==============================
# SECURITY SETTINGS
# ==============================

# Redirect all HTTP → HTTPS
SECURE_SSL_REDIRECT = True

# Cookies sent only over HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS (strict HTTPS enforcement)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Security Headers
SECURE_CONTENT_TYPE_NOSNIFF = True

# Django 5:
# SECURE_BROWSER_XSS_FILTER is REMOVED
# Replace with Content Security Policy instead (optional)
# SECURE_BROWSER_XSS_FILTER = True  ❌ (deprecated since Django 4.0)

X_FRAME_OPTIONS = 'DENY'

# ==============================
# ALLOWED HOSTS
# ==============================
# Must be overridden in environment variables
ALLOWED_HOSTS = env.list(
    'ALLOWED_HOSTS',
    default=[
        'localhost',
        '127.0.0.1',
    ],
)

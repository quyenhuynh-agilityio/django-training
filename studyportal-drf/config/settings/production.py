import dj_database_url

from .base import *  # noqa: F403
from .base import env

# ==============================
# CRITICAL: Force DEBUG OFF
# ==============================
DEBUG = False

# ==============================
# SECURITY: Require SECRET_KEY
# ==============================
secret_key_from_env = env('DJANGO_SECRET_KEY', default='')
if not secret_key_from_env or len(secret_key_from_env) < 40:
    raise ValueError(
        'DJANGO_SECRET_KEY must be explicitly set in production environment with at least 40 characters! '
        "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(50))'"
    )
SECRET_KEY = secret_key_from_env

# ==============================
# ALLOWED HOSTS
# ==============================
# Must be explicitly set in .env.production
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# ==============================
# SECURITY SETTINGS
# ==============================
# HTTPS enforcement
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)

# Secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Referrer policy
SECURE_REFERRER_POLICY = 'same-origin'

# ==============================
# CORS
# ==============================
# Must be explicitly set - no defaults
cors_origins = env.list('CORS_ALLOWED_ORIGINS', default=[])
if not cors_origins:
    raise ValueError(
        'CORS_ALLOWED_ORIGINS must be set in production. '
        'Example: CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com'
    )
CORS_ALLOWED_ORIGINS = cors_origins
CORS_ALLOW_ALL_ORIGINS = False  # Never allow in production

# ==============================
# DATABASE
# ==============================
# Prefer a single DATABASE_URL (e.g., from Render managed PostgreSQL)
DATABASE_URL = env('DATABASE_URL', default='')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,  # Connection pooling - keeps connections alive for 10 minutes
            ssl_require=env.bool('DB_SSL_REQUIRE', default=True),
        )
    }
else:
    # Fallback: require all individual database settings (no defaults)
    required_db_vars = ['DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST']
    missing_vars = [var for var in required_db_vars if not env(var, default='')]
    if missing_vars:
        raise ValueError(
            'Either DATABASE_URL must be set, or the following database environment '
            f"variables must be provided: {', '.join(missing_vars)}"
        )

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST'),
            'PORT': env('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }

# ==============================
# EMAIL
# ==============================
# Require real email backend in production
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

# Validate email settings if using SMTP
if EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
    required_email_vars = ['EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD']
    missing_email_vars = [var for var in required_email_vars if not env(var, default='')]
    if missing_email_vars:
        raise ValueError(
            f"Missing required email environment variables for SMTP: {', '.join(missing_email_vars)}"
        )

EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)
SERVER_EMAIL = env('SERVER_EMAIL', default=EMAIL_HOST_USER)

# ==============================
# SESSION
# ==============================
# Use database-backed sessions in production
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
# ==============================
# DISABLE DEBUG FEATURES
# ==============================
PASSWORD_RESET_DEBUG_EXPOSE_TOKENS = False
PASSWORD_RESET_DISABLE_EMAIL = False

# ==============================
# FRONTEND URL
# ==============================
frontend_url = env('FRONTEND_URL', default='')
if not frontend_url:
    raise ValueError('FRONTEND_URL must be set in production (e.g., https://yourdomain.com)')
FRONTEND_URL = frontend_url

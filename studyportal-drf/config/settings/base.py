import os
import secrets
from datetime import timedelta
from pathlib import Path

import environ

from django.core.exceptions import ImproperlyConfigured

# ==============================
# ENVIRONMENT
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# -------------------
# ENV
# -------------------
env = environ.Env(DEBUG=(bool, False))

# Load ONE .env file
environ.Env.read_env(BASE_DIR / '.env')

DJANGO_ENV = env('DJANGO_ENV', default='local')

# REDIS CONFIGURATION
# ============================================
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')


SECRET_KEY = env('SECRET_KEY', default=secrets.token_urlsafe(50))

DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list(
    'ALLOWED_HOSTS',
    default=[
        'localhost',
        '127.0.0.1',
    ],
)

# ==============================
# INSTALLED APPS
# ==============================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    # Celery
    'django_celery_beat',
    'django_celery_results',
    # Local apps
    'users.apps.UsersConfig',
    'courses.apps.CoursesConfig',
    'categories.apps.CategoriesConfig',
    'enrollments.apps.EnrollmentsConfig',
    'core',
]

# ==============================
# MIDDLEWARE
# ==============================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ==============================
# TEMPLATES
# ==============================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ==============================
# DATABASE
# ==============================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME', default='studyportal_db'),
        'USER': env('DB_USER', default='postgres'),
        'PASSWORD': env('DB_PASSWORD', default=''),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

# ==============================
# AUTH & PASSWORDS
# ==============================
AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==============================
# TIMEZONE
# ==============================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ==============================
# STATIC & MEDIA
# ==============================
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Prevent crash if static folder missing
STATICFILES_DIRS = [d for d in [BASE_DIR / 'static'] if d.exists()]

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================
# DRF CONFIG
# ==============================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# ==============================
# JWT
# ==============================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME', default=60)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ==============================
# CORS
# ==============================
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        'http://localhost:3000',
        'http://localhost:8080',
    ],
)
CORS_ALLOW_CREDENTIALS = True

# ==============================
# API Documentation
# ==============================
SPECTACULAR_SETTINGS = {
    'TITLE': 'Student Course Management API',
    'DESCRIPTION': 'API for managing student course enrollments',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'ENUM_NAME_OVERRIDES': {
        'CourseStatusEnum': 'courses.models.Course.STATUS_CHOICES',
        'EnrollmentStatusEnum': 'enrollments.models.Enrollment.STATUS_CHOICES',
    },
}


# ============================================
# CACHE CONFIGURATION (django-redis)
# ============================================
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'studyportal',
        'TIMEOUT': 300,  # Default: 5 minutes
    }
}

# ============================================
# SESSION CONFIGURATION (Optional: Use Redis)
# ============================================
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# ============================================
# CELERY CONFIGURATION
# ============================================
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_BACKEND_ALWAYS_RETRY = True
CELERY_RESULT_BACKEND_MAX_RETRIES = 10

# Celery Beat Schedule (will add tasks later)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    # Will add scheduled tasks here
}


# ============================================
# SENTRY CONFIGURATION
# ============================================
SENTRY_DSN = env('SENTRY_DSN', default='')

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment=DJANGO_ENV,
    )

# ==============================
# EMAIL
# ==============================
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')

EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

# ==============================
# PASSWORD RESET DEBUG OPTIONS
# ==============================
# Allow testing the reset flow directly in Swagger without sending emails.
# When enabled, the reset request endpoint will return uid/token/reset_link.
PASSWORD_RESET_DEBUG_EXPOSE_TOKENS = env.bool('PASSWORD_RESET_DEBUG_EXPOSE_TOKENS', default=DEBUG)
# Skip sending emails entirely (useful for local Swagger testing)
PASSWORD_RESET_DISABLE_EMAIL = env.bool('PASSWORD_RESET_DISABLE_EMAIL', default=False)
# Frontend URL used to build reset link (falls back to localhost)
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:3000')

# ==============================
# ENVIRONMENT VALIDATION
# ==============================
# Ensure base.py is never used directly
settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '')
if settings_module == 'config.settings.base':
    raise ImproperlyConfigured(
        "Don't use config.settings.base directly. "
        'Use config.settings.local, config.settings.production, or config.settings.test'
    )

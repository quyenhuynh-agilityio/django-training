# config/settings/__init__.py
import os

DJANGO_ENV = os.getenv('DJANGO_ENV', 'local')

if DJANGO_ENV == 'production':
    from .production import *  # noqa: F403
else:
    from .local import *  # noqa: F403

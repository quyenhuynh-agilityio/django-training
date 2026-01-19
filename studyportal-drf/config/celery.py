import os

from celery import Celery

from django.conf import settings

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

# Create Celery app
app = Celery('studyportal')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery is working"""
    print(f'Request: {self.request!r}')

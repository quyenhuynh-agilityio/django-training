import os

import sentry_sdk
from celery import Celery
from celery.signals import (
    task_failure,
    task_retry,
    task_success,
)

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

# Create Celery app
app = Celery('studyportal')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


# ============================================================================
# CELERY SIGNAL HANDLERS FOR SENTRY MONITORING
# ============================================================================


@task_failure.connect
def handle_task_failure(
    sender=None,
    task_id=None,
    exception=None,
    args=None,
    kwargs=None,
    traceback=None,
    einfo=None,
    **extra_kwargs,
):
    """Capture task failures in Sentry with full context"""
    with sentry_sdk.push_scope() as scope:
        scope.set_context(
            'celery-task',
            {
                'task': sender.name,
                'task_id': task_id,
                'args': args,
                'kwargs': kwargs,
            },
        )
        scope.set_tag('celery_task_name', sender.name)
        scope.set_tag('celery_task_id', task_id)
        sentry_sdk.capture_exception(exception)


@task_retry.connect
def handle_task_retry(sender=None, task_id=None, reason=None, einfo=None, **kwargs):
    """Log task retries to Sentry as breadcrumbs"""
    sentry_sdk.add_breadcrumb(
        category='celery',
        message=f'Task {sender.name} retry',
        level='warning',
        data={
            'task_id': task_id,
            'reason': str(reason),
            'task_name': sender.name,
        },
    )


@task_success.connect
def handle_task_success(sender=None, result=None, **kwargs):
    """Log successful task completions as breadcrumbs"""
    sentry_sdk.add_breadcrumb(
        category='celery',
        message=f'Task {sender.name} succeeded',
        level='info',
        data={'task_name': sender.name},
    )


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery is working"""
    print(f'Request: {self.request!r}')

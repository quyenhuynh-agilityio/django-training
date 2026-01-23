import os

from celery import Celery
from celery.signals import (
    task_failure,
    task_retry,
    task_success,
)

from core.sentry import sentry_add_breadcrumb, sentry_scope

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
    # Note: keep Sentry capture here even if individual tasks also capture,
    # since this is a last-resort hook for unhandled task errors.
    with sentry_scope(
        tags={'celery_task_name': sender.name, 'celery_task_id': task_id, 'module': 'celery'},
        contexts={
            'celery-task': {'task': sender.name, 'task_id': task_id, 'args': args, 'kwargs': kwargs}
        },
    ):
        # Capture directly to avoid nested scopes.
        import sentry_sdk as _sentry_sdk

        _sentry_sdk.capture_exception(exception)


@task_retry.connect
def handle_task_retry(sender=None, task_id=None, reason=None, einfo=None, **kwargs):
    """Log task retries to Sentry as breadcrumbs"""
    sentry_add_breadcrumb(
        category='celery',
        message=f'Task {sender.name} retry',
        level='warning',
        data={'task_id': task_id, 'reason': str(reason), 'task_name': sender.name},
    )


@task_success.connect
def handle_task_success(sender=None, result=None, **kwargs):
    """Log successful task completions as breadcrumbs"""
    sentry_add_breadcrumb(
        category='celery',
        message=f'Task {sender.name} succeeded',
        level='info',
        data={'task_name': sender.name},
    )


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery is working"""
    print(f'Request: {self.request!r}')

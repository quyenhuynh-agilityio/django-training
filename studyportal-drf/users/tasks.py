"""
Celery tasks for user-related email operations.

All email sending operations are asynchronous and use Celery with Redis broker.
Tasks include retry logic and Sentry error tracking.
"""

import logging

from celery import shared_task

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

# Import here to avoid circular imports
from django.db.models import Count, F, Q
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from core.choices import EnrollmentStatus
from core.sentry import (
    sentry_add_breadcrumb,
    sentry_capture_exception,
    sentry_capture_message,
    sentry_scope,
)
from core.texts import EmailMessage, EmailSubject
from courses.models import Course
from enrollments.models import Enrollment

logger = logging.getLogger(__name__)


def _get_user_by_id(user_id, error_context=''):
    """
    Helper function to get user by ID with consistent error handling.

    Args:
        user_id: UUID of the user
        error_context: Additional context for error messages

    Returns:
        User instance

    Raises:
        User.DoesNotExist: If user is not found
    """

    user_model = get_user_model()

    try:
        return user_model.objects.get(id=user_id)
    except user_model.DoesNotExist:
        context_msg = f' for {error_context}' if error_context else ''
        logger.error(f'User {user_id} not found{context_msg}')
        sentry_capture_message(
            f'User {user_id} not found{context_msg}',
            level='error',
            tags={'module': 'users', 'task_name': 'user_lookup'},
            contexts={'task_data': {'user_id': str(user_id), 'error_context': error_context}},
        )
        raise


def _send_email_with_context(user, subject, template_name, context, sentry_tag, log_message):
    """
    Helper function to send email with Sentry context and error handling.

    Args:
        user: User instance
        subject: Email subject (from EmailSubject constants)
        template_name: Email template path
        context: Template context dictionary
        sentry_tag: Tag for Sentry tracking
        log_message: Log message for successful send

    Returns:
        None

    Raises:
        Exception: If email sending fails
    """
    with sentry_scope(
        tags={'task_name': sentry_tag, 'module': 'users'},
        contexts={'task_data': {'user_id': str(user.id), 'email': user.email}},
        user={'id': str(user.id), 'email': user.email},
    ):
        try:
            html_message = render_to_string(template_name, context)
            plain_message = strip_tags(html_message)

            send_mail(
                subject=str(subject),
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(log_message.format(email=user.email))

        except Exception as e:
            logger.error(f'Failed to send email to {user.email}: {str(e)}')
            sentry_capture_exception(
                e,
                tags={'task_name': sentry_tag, 'module': 'users'},
                contexts={'task_data': {'user_id': str(user.id), 'email': user.email}},
                user={'id': str(user.id), 'email': user.email},
            )
            raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    retry_backoff=True,
    name='accounts.send_verification_email',
)
def send_verification_email(self, user_id, token):
    """
    Send email verification link to new user.

    Args:
        user_id: UUID of the user
        token: Verification token
    """
    user = _get_user_by_id(user_id, error_context='email verification')

    verification_url = f'{settings.EMAIL_VERIFICATION_URL}/{user_id}/{token}/'

    _send_email_with_context(
        user=user,
        subject=EmailSubject.VERIFY_EMAIL,
        template_name='emails/verification_email.html',
        context={
            'user': user,
            'verification_url': verification_url,
            'expiry_hours': settings.EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS,
        },
        sentry_tag='send_verification_email',
        log_message='Verification email sent to {email}',
    )

    # Record success in Sentry
    sentry_add_breadcrumb(
        category='email',
        message=str(EmailMessage.VERIFICATION_SENT),
        level='info',
        data={'task_name': 'send_verification_email', 'user_id': str(user.id)},
    )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    name='accounts.send_welcome_email',
)
def send_welcome_email(self, user_id):
    """
    Send welcome email after successful email verification.

    Args:
        user_id: UUID of the user
    """
    user = _get_user_by_id(user_id, error_context='welcome email')

    base_url = (getattr(settings, 'FRONTEND_URL', '') or 'http://localhost:3000').rstrip('/')
    dashboard_url = f'{base_url}/dashboard'

    _send_email_with_context(
        user=user,
        subject=EmailSubject.WELCOME,
        template_name='emails/welcome_email.html',
        context={
            'user': user,
            'dashboard_url': dashboard_url,
        },
        sentry_tag='send_welcome_email',
        log_message='Welcome email sent to {email}',
    )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 10},
    name='accounts.auto_enroll_intro_courses',
)
def auto_enroll_intro_courses(self, user_id):
    """
    Automatically enroll new user in introduction courses.

    Args:
        user_id: UUID of the user
    """
    if not settings.AUTO_ENROLL_INTRO_COURSES:
        logger.info('Auto-enrollment is disabled')
        return

    user = _get_user_by_id(user_id, error_context='auto-enrollment')

    with sentry_scope(
        tags={'task_name': 'auto_enroll_intro_courses', 'module': 'users'},
        contexts={'task_data': {'user_id': str(user_id)}},
        user={'id': str(user.id), 'email': user.email},
    ):
        try:
            # Single queryset: intro + active + not at capacity + not already enrolled by user
            to_enroll = list(
                Course.objects.filter(
                    is_introduction=True,
                    is_active=True,
                    status=Course.STATUS_ACTIVE,
                )
                .exclude(
                    enrollments__student=user,
                    enrollments__is_active=True,
                )
                .annotate(
                    enrolled_count=Count(
                        'enrollments',
                        filter=Q(enrollments__is_active=True),
                        distinct=True,
                    )
                )
                .filter(
                    Q(max_students__isnull=True)
                    | Q(enrolled_count__lt=F('max_students'))
                )
            )

            if not to_enroll:
                logger.info('No introduction courses found for auto-enrollment')
                return

            to_create = [
                Enrollment(
                    student=user,
                    course=course,
                    status=EnrollmentStatus.ACTIVE,
                )
                for course in to_enroll
            ]

            if not to_create:
                logger.info(
                    'User already enrolled or no available intro courses for auto-enrollment'
                )
                return

            # Bulk-create enrollments in one DB round-trip
            created_enrollments = Enrollment.objects.bulk_create(to_create)
            enrolled_count = len(created_enrollments)

            for course in to_enroll:
                logger.info(f'Auto-enrolled {user.email} in course: {course.title}')

            logger.info(f'Auto-enrolled user {user.email} in {enrolled_count} courses')

            # Track enrollment metrics in Sentry
            sentry_add_breadcrumb(
                category='enrollment',
                message=str(EmailMessage.AUTO_ENROLLED).format(count=enrolled_count),
                level='info',
                data={'enrolled_count': enrolled_count, 'user_id': str(user.id)},
            )

        except Exception as e:
            logger.error(f'Failed to auto-enroll user {user_id}: {str(e)}')
            sentry_capture_exception(
                e,
                tags={'task_name': 'auto_enroll_intro_courses', 'module': 'users'},
                contexts={'task_data': {'user_id': str(user_id)}},
                user={'id': str(user.id), 'email': user.email},
            )
            raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    name='accounts.send_password_reset_email',
)
def send_password_reset_email(self, user_id, reset_url):
    """
    Send password reset link to user.

    Args:
        user_id: UUID of the user
        reset_url: Password reset URL with token
    """
    user = _get_user_by_id(user_id, error_context='password reset email')

    _send_email_with_context(
        user=user,
        subject=EmailSubject.PASSWORD_RESET_REQUEST,
        template_name='emails/password_reset_email.html',
        context={
            'user': user,
            'reset_url': reset_url,
        },
        sentry_tag='send_password_reset_email',
        log_message='Password reset email sent to {email}',
    )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    name='accounts.send_password_reset_confirmation_email',
)
def send_password_reset_confirmation_email(self, user_id):
    """
    Send password reset confirmation email after successful password reset.

    Args:
        user_id: UUID of the user
    """
    user = _get_user_by_id(user_id, error_context='password reset confirmation email')

    _send_email_with_context(
        user=user,
        subject=EmailSubject.PASSWORD_RESET_CONFIRMATION,
        template_name='emails/password_reset_confirmation_email.html',
        context={
            'user': user,
            'login_url': f'{settings.FRONTEND_URL}/login',
        },
        sentry_tag='send_password_reset_confirmation_email',
        log_message='Password reset confirmation email sent to {email}',
    )

"""
Celery tasks for course-related email operations.

All email sending operations are asynchronous and use Celery with Redis broker.
Tasks include retry logic and Sentry error tracking.
"""

import logging

import sentry_sdk
from celery import shared_task

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from core.texts import EmailSubject

logger = logging.getLogger(__name__)


def _send_course_email_with_context(
    course, subject, template_name, context, sentry_tag, log_message
):
    """
    Helper function to send course-related email with Sentry context and error handling.
    """
    recipient_email = course.instructor.email if course.instructor else None

    if not recipient_email:
        logger.warning(f'No recipient email found for course {course.id} ({sentry_tag})')
        return

    with sentry_sdk.push_scope() as scope:
        scope.set_tag('task_name', sentry_tag)
        scope.set_context(
            'task_data',
            {
                'course_id': str(course.id),
                'course_title': course.title,
                'recipient_email': recipient_email,
            },
        )
        scope.set_user(
            {
                'id': str(course.instructor.id) if course.instructor else None,
                'email': recipient_email,
            }
        )

        try:
            html_message = render_to_string(template_name, context)
            plain_message = strip_tags(html_message)

            send_mail(
                subject=str(subject),
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(log_message.format(email=recipient_email, course=course.title))

        except Exception as e:
            logger.error(
                f'Failed to send email to {recipient_email} for course {course.title}: {str(e)}'
            )
            sentry_sdk.capture_exception(e)
            raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True,
    name='courses.send_course_full_email',
)
def send_course_full_email(self, course_id):
    """
    Sends an email to the instructor when a course reaches its enrollment limit.
    """
    from .models import Course  # Inline import to avoid circular dependencies

    try:
        # Optimization: select_related instructor to avoid extra DB hits in helper
        course = Course.objects.select_related('instructor').get(id=course_id)

        # Use the same logic as the model: active enrollments only
        enrolled_count = course.enrollments.filter(is_active=True).count()

        # Double-check condition (Safety check for concurrency)
        if course.max_students and enrolled_count < course.max_students:
            logger.info(f'Course {course.title} is no longer full; skipping email.')
            return

        if not course.instructor or not course.instructor.email:
            msg = f'Instructor info missing for course {course.id} capacity alert.'
            logger.warning(msg)
            sentry_sdk.capture_message(msg, level='warning')
            return

        context = {
            'instructor_name': getattr(course.instructor, 'full_name', course.instructor.email),
            'course_title': course.title,
            'course_code': course.course_code,
            'enrolled_count': enrolled_count,
            'max_students': course.max_students,
        }

        _send_course_email_with_context(
            course=course,
            subject=EmailSubject.COURSE_CAPACITY_REACHED,
            template_name='emails/enrollment_limit_notification.html',
            context=context,
            sentry_tag='send_course_full_email',
            log_message='Course capacity reached email sent to {email} for course {course}',
        )

        # Record success in Sentry
        sentry_sdk.add_breadcrumb(
            category='email',
            message=f'Capacity alert sent for {course.course_code}',
            level='info',
        )

    except Course.DoesNotExist:
        msg = f'Course {course_id} not found for full enrollment notification.'
        logger.error(msg)
        sentry_sdk.capture_message(msg, level='error')
        # No retry if the object doesn't exist
    except Exception as exc:
        logger.error(f'Unexpected error in send_course_full_email for {course_id}: {exc}')
        sentry_sdk.capture_exception(exc)
        raise self.retry(exc=exc)  # noqa: B904

"""
Celery tasks for course-related email operations.

All email sending operations are asynchronous and use Celery with Redis broker.
Tasks include retry logic and Sentry error tracking.
"""

import csv
import io
import logging
from collections import defaultdict
from datetime import timedelta

from celery import shared_task

from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.db.models import Count, Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from core.sentry import (
    sentry_add_breadcrumb,
    sentry_capture_exception,
    sentry_capture_message,
    sentry_scope,
)
from core.texts import EmailSubject
from courses.models import Course

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

    with sentry_scope(
        tags={'task_name': sentry_tag, 'module': 'courses'},
        contexts={
            'task_data': {
                'course_id': str(course.id),
                'course_title': course.title,
                'recipient_email': recipient_email,
            }
        },
        user={
            'id': str(course.instructor.id) if course.instructor else None,
            'email': recipient_email,
        },
    ):
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
            sentry_capture_exception(
                e,
                tags={'task_name': sentry_tag, 'module': 'courses'},
                contexts={
                    'task_data': {
                        'course_id': str(course.id),
                        'course_title': course.title,
                        'recipient_email': recipient_email,
                    }
                },
            )
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
            sentry_capture_message(
                msg,
                level='warning',
                tags={'task_name': 'send_course_full_email', 'module': 'courses'},
                contexts={
                    'task_data': {'course_id': str(course.id), 'course_code': course.course_code}
                },
            )
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
        sentry_add_breadcrumb(
            category='email',
            message=f'Capacity alert sent for {course.course_code}',
            level='info',
            data={'task_name': 'send_course_full_email', 'course_id': str(course.id)},
        )

    except Course.DoesNotExist:
        msg = f'Course {course_id} not found for full enrollment notification.'
        logger.error(msg)
        sentry_capture_message(
            msg,
            level='error',
            tags={'task_name': 'send_course_full_email', 'module': 'courses'},
            contexts={'task_data': {'course_id': str(course_id)}},
        )
        # No retry if the object doesn't exist
    except Exception as exc:
        logger.error(f'Unexpected error in send_course_full_email for {course_id}: {exc}')
        sentry_capture_exception(
            exc,
            tags={'task_name': 'send_course_full_email', 'module': 'courses'},
            contexts={'task_data': {'course_id': str(course_id)}},
        )
        raise self.retry(exc=exc)  # noqa: B904


@shared_task(name='courses.cleanup_inactive_courses')
def cleanup_inactive_courses():
    """
    Weekly task to permanently delete courses that have been
    inactive (soft-deleted) for more than 3 months.
    """
    three_months_ago = timezone.now() - timedelta(days=90)

    # Identify courses to purge
    to_delete = Course.objects.filter(is_active=False, updated_at__lte=three_months_ago)

    count = to_delete.count()
    if count > 0:
        logger.info(f'Starting cleanup: Removing {count} inactive courses.')
        to_delete.delete()  # This performs a hard delete from the DB
        logger.info('Cleanup successful.')
    else:
        logger.info('No inactive courses found for cleanup.')

    return {'deleted_count': count}


def _send_instructor_monthly_report(instructor, csv_content, report_label):
    """Send a monthly CSV enrollment report to a single instructor."""
    recipient_email = getattr(instructor, 'email', None)

    if not recipient_email:
        logger.warning('No email found for instructor %s in monthly report task', instructor.id)
        return

    with sentry_scope(
        tags={'task_name': 'send_monthly_enrollment_report', 'module': 'courses'},
        contexts={
            'task_data': {
                'instructor_id': str(instructor.id),
                'instructor_email': recipient_email,
                'report_period': report_label,
            }
        },
        user={'id': str(instructor.id), 'email': recipient_email},
    ):
        subject = str(EmailSubject.MONTHLY_ENROLLMENT_REPORT)
        instructor_name = getattr(instructor, 'full_name', None) or recipient_email
        body = (
            f'Hello {instructor_name},\\n\\n'
            f'Please find attached the enrollment report for {report_label}.\\n\\n'
            'Best regards,\\n'
            'Study Portal'
        )

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )

        filename_safe_label = report_label.replace(' ', '_').lower()
        filename = f'enrollment_report_{filename_safe_label}.csv'
        email.attach(filename, csv_content, 'text/csv')
        email.send(fail_silently=False)

        logger.info(
            'Monthly enrollment report email sent to %s for period %s',
            recipient_email,
            report_label,
        )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 300},
    retry_backoff=True,
    name='courses.send_monthly_enrollment_report',
)
def send_monthly_enrollment_report(self, report_label=None):
    """
    Generate and email a CSV report to each instructor with active enrollments per course.

    Args:
        report_label: Optional label for the report (e.g., "January 2026").
                     If None, uses current month/year.

    Returns:
        dict: Status of report generation
    """
    now = timezone.now()

    # Use provided label or generate from current date
    if not report_label:
        report_label = now.strftime('%B %Y')  # e.g., "January 2026"

    logger.info(f'Starting monthly enrollment report generation for {report_label}')

    # Annotate courses with active enrollment counts
    courses = (
        Course.objects.filter(instructor__isnull=False)
        .select_related('instructor')
        .annotate(
            active_enrollment_count=Count(
                'enrollments',
                filter=Q(enrollments__is_active=True),
            )
        )
        .order_by('instructor__email', 'title')
    )

    if not courses.exists():
        logger.info('No courses found for monthly enrollment report.')
        return {'status': 'no_courses', 'message': 'No courses with instructors found'}

    # Group courses by instructor
    courses_by_instructor = defaultdict(list)
    for course in courses:
        if not course.instructor:
            continue
        courses_by_instructor[course.instructor].append(course)

    if not courses_by_instructor:
        logger.info('No instructors found with courses.')
        return {'status': 'no_instructors', 'message': 'No instructors with courses found'}

    # Send report to each instructor
    reports_sent = 0
    for instructor, instructor_courses in courses_by_instructor.items():
        if not instructor_courses:
            continue

        # Generate CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Course ID', 'Course Code', 'Course Title', 'Active Enrollments'])

        for course in instructor_courses:
            writer.writerow(
                [
                    str(course.id),
                    course.course_code,
                    course.title,
                    getattr(course, 'active_enrollment_count', 0),
                ]
            )

        csv_content = output.getvalue()
        output.close()

        # Send email with CSV attachment
        try:
            _send_instructor_monthly_report(instructor, csv_content, report_label)
            reports_sent += 1
        except Exception as e:
            logger.error(
                f'Failed to send report to instructor {instructor.email}: {e}', exc_info=True
            )
            sentry_capture_exception(
                e,
                tags={'task_name': 'send_monthly_enrollment_report', 'module': 'courses'},
                contexts={
                    'task_data': {
                        'instructor_id': str(instructor.id),
                        'instructor_email': getattr(instructor, 'email', None),
                        'report_period': report_label,
                    }
                },
            )
            # Continue with other instructors even if one fails

    logger.info(f'Monthly enrollment report completed. Sent {reports_sent} reports.')

    return {
        'status': 'success',
        'reports_sent': reports_sent,
        'report_period': report_label,
        'timestamp': now.isoformat(),
    }

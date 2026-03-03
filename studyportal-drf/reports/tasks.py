"""
Celery tasks for reporting (cross-app analytics and exports).

Currently contains:
- Monthly enrollment report per instructor (courses + enrollments)
"""

import csv
import io
import logging
from collections import defaultdict

from celery import shared_task

from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Count, Q
from django.utils import timezone

from core.sentry import sentry_capture_exception, sentry_scope
from core.texts import EmailSubject
from courses.models import Course

logger = logging.getLogger(__name__)


def _send_instructor_monthly_report(instructor, csv_content, report_label):
    """Send a monthly CSV enrollment report to a single instructor."""
    recipient_email = getattr(instructor, 'email', None)

    if not recipient_email:
        logger.warning('No email found for instructor %s in monthly report task', instructor.id)
        return

    with sentry_scope(
        tags={'task_name': 'send_monthly_enrollment_report', 'module': 'reports'},
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
    name='reports.send_monthly_enrollment_report',
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

    # Annotate active courses with active enrollment counts
    courses_qs = (
        Course.objects.filter(
            instructor__isnull=False,
            is_active=True,
            status=Course.STATUS_ACTIVE,
        )
        .select_related('instructor')
        .annotate(
            active_enrollment_count=Count(
                'enrollments',
                filter=Q(enrollments__is_active=True),
            )
        )
        .order_by('instructor__email', 'title')
    )

    # Materialize once; avoid extra exists() query
    courses = list(courses_qs)
    if not courses:
        logger.info('No active courses with instructors found for monthly enrollment report.')
        return {'status': 'no_courses', 'message': 'No active courses with instructors found'}

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
        with io.StringIO() as output:
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

        # Send email with CSV attachment
        with sentry_scope(
            tags={'task_name': 'send_monthly_enrollment_report', 'module': 'reports'},
            contexts={
                'task_data': {
                    'instructor_id': str(instructor.id),
                    'instructor_email': getattr(instructor, 'email', None),
                    'report_period': report_label,
                }
            },
        ):
            try:
                _send_instructor_monthly_report(instructor, csv_content, report_label)
                reports_sent += 1
            except Exception as e:
                logger.error(
                    f'Failed to send report to instructor {instructor.email}: {e}', exc_info=True
                )
                sentry_capture_exception(e)  # scope already set above
                # Continue with other instructors even if one fails

    logger.info(f'Monthly enrollment report completed. Sent {reports_sent} reports.')

    return {
        'status': 'success',
        'reports_sent': reports_sent,
        'report_period': report_label,
        'timestamp': now.isoformat(),
    }


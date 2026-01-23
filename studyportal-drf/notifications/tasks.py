import logging

from celery import shared_task

from django.core.cache import cache

from core.sentry import sentry_capture_exception, sentry_scope
from notifications.models import Notification, NotificationType

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    name='notifications.create_student_enrolled_notification',
)
def create_student_enrolled_notification(
    self,
    instructor_id,
    student_id,
    student_name,
    student_email,
    course_id,
    course_code,
    course_title,
):
    """
    Async task to create student enrollment notification for instructor.

    Args:
        instructor_id: UUID of instructor
        student_id: UUID of student
        student_name: Full name of student
        student_email: Email of student
        course_id: UUID of course
        course_code: Course code
        course_title: Course title
    """
    try:
        logger.info(
            f'Creating enrollment notification for instructor {instructor_id} '
            f'about student {student_email} in course {course_code}'
        )

        with sentry_scope(
            tags={'task_name': 'create_student_enrolled_notification', 'module': 'notifications'},
            contexts={
                'task_data': {
                    'instructor_id': str(instructor_id),
                    'student_id': str(student_id),
                    'student_email': student_email,
                    'course_id': str(course_id),
                    'course_code': course_code,
                }
            },
        ):
            notification = Notification.objects.create(
                recipient_id=instructor_id,
                type=NotificationType.STUDENT_ENROLLED,
                payload={
                    'student_id': str(student_id),
                    'student_name': student_name,
                    'student_email': student_email,
                    'course_id': str(course_id),
                    'course_code': course_code,
                    'course_title': course_title,
                    'message': f'{student_name} has enrolled in {course_title}',
                },
            )

        # Invalidate instructor's unread count cache
        cache.delete(f'notification_unread_count_{instructor_id}')

        logger.info(f'Created notification {notification.id}')
        return {'status': 'success', 'notification_id': str(notification.id)}

    except Exception as e:
        logger.error(f'Failed to create enrollment notification: {e}', exc_info=True)
        sentry_capture_exception(
            e,
            tags={'task_name': 'create_student_enrolled_notification', 'module': 'notifications'},
            contexts={
                'task_data': {
                    'instructor_id': str(instructor_id),
                    'student_id': str(student_id),
                    'student_email': student_email,
                    'course_id': str(course_id),
                    'course_code': course_code,
                }
            },
        )
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    name='notifications.create_student_removed_notification',
)
def create_student_removed_notification(
    self,
    student_id,
    course_id,
    course_code,
    course_title,
    removed_by_id=None,
    removed_by_name=None,
):
    """
    Async task to create student removal notification.

    Args:
        student_id: UUID of student
        course_id: UUID of course
        course_code: Course code
        course_title: Course title
        removed_by_id: UUID of user who removed (optional)
        removed_by_name: Name of user who removed (optional)
    """
    try:
        logger.info(
            f'Creating removal notification for student {student_id} from course {course_code}'
        )

        with sentry_scope(
            tags={'task_name': 'create_student_removed_notification', 'module': 'notifications'},
            contexts={
                'task_data': {
                    'student_id': str(student_id),
                    'course_id': str(course_id),
                    'course_code': course_code,
                    'removed_by_id': str(removed_by_id) if removed_by_id else None,
                }
            },
        ):
            message = f'You have been removed from {course_title}'
            if removed_by_name:
                message += f' by {removed_by_name}'

            notification = Notification.objects.create(
                recipient_id=student_id,
                type=NotificationType.STUDENT_REMOVED,
                payload={
                    'course_id': str(course_id),
                    'course_code': course_code,
                    'course_title': course_title,
                    'removed_by': str(removed_by_id) if removed_by_id else None,
                    'removed_by_name': removed_by_name or 'System',
                    'message': message,
                },
            )

        # Invalidate student's unread count cache
        cache.delete(f'notification_unread_count_{student_id}')

        logger.info(f'Created notification {notification.id}')
        return {'status': 'success', 'notification_id': str(notification.id)}

    except Exception as e:
        logger.error(f'Failed to create removal notification: {e}', exc_info=True)
        sentry_capture_exception(
            e,
            tags={'task_name': 'create_student_removed_notification', 'module': 'notifications'},
            contexts={
                'task_data': {
                    'student_id': str(student_id),
                    'course_id': str(course_id),
                    'course_code': course_code,
                    'removed_by_id': str(removed_by_id) if removed_by_id else None,
                }
            },
        )
        raise

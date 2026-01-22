import logging

from celery import shared_task

from django.core.cache import cache

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
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    name='notifications.create_course_full_notification',
)
def create_course_full_notification(
    self,
    instructor_id,
    course_id,
    course_code,
    course_title,
    enrolled_count,
    max_students,
):
    """
    Async task to create course full notification for instructor.

    Args:
        instructor_id: UUID of instructor
        course_id: UUID of course
        course_code: Course code
        course_title: Course title
        enrolled_count: Current enrollment count
        max_students: Maximum allowed students
    """
    try:
        # Check for duplicate notification
        existing = Notification.objects.filter(
            recipient_id=instructor_id,
            type=NotificationType.COURSE_FULL,
            payload__course_id=str(course_id),
        ).exists()

        if existing:
            logger.info(f'Skipping duplicate course full notification for {course_code}')
            return {'status': 'skipped', 'reason': 'duplicate'}

        logger.info(
            f'Creating course full notification for instructor {instructor_id} '
            f'about course {course_code}'
        )

        notification = Notification.objects.create(
            recipient_id=instructor_id,
            type=NotificationType.COURSE_FULL,
            payload={
                'course_id': str(course_id),
                'course_code': course_code,
                'course_title': course_title,
                'enrolled_count': enrolled_count,
                'max_students': max_students,
                'message': f'{course_title} has reached maximum capacity ({enrolled_count}/{max_students} students)',
            },
        )

        # Invalidate instructor's unread count cache
        cache.delete(f'notification_unread_count_{instructor_id}')

        logger.info(f'Created notification {notification.id}')
        return {'status': 'success', 'notification_id': str(notification.id)}

    except Exception as e:
        logger.error(f'Failed to create course full notification: {e}', exc_info=True)
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
            f'Creating removal notification for student {student_id} ' f'from course {course_code}'
        )

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
        raise

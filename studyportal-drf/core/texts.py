"""Shared text constants (error messages + help text).

Why:
- Avoid repeating string literals across serializers/models
- Make wording consistent
- Centralize translation hooks via gettext_lazy

Keep this module dependency-light to avoid circular imports.
"""

from django.utils.translation import gettext_lazy as _


class HelpText:
    # Users / auth
    PASSWORD_STRENGTH_REQUIREMENTS = _('Password must meet strength requirements')
    MUST_MATCH_PASSWORD = _('Must match password')
    EMAIL_MUST_BE_UNIQUE = _('Must be unique')
    USERNAME_UNIQUE_AND_FORMAT = _('Must be unique, alphanumeric with underscores')
    USER_EMAIL_ADDRESS = _('User email address')
    USER_PASSWORD = _('User password')
    PASSWORD_RESET_EMAIL = _('Email address to send reset link')
    RESET_UID = _('Base64 encoded user ID from reset email')
    RESET_TOKEN = _('Password reset token from reset email')
    CURRENT_PASSWORD = _('Current password')

    # Users / models
    USER_ID = _('Secure, unguessable ID used in APIs and mobile app')
    USER_EMAIL_LOGIN = _('Used as login identifier (not username)')
    USER_ROLE = _('Determines user permissions in the platform')
    USER_CREATED_AT = _('When user registered')
    USER_UPDATED_AT = _('Last profile update')

    # Enrollments
    ENROLL_COURSE_ID = _('UUID of the course to enroll in')
    ENROLLMENT_STUDENT_FK = _('Only student-role users can be enrolled')

    # Courses
    COURSE_TITLE = _('Public course title')
    COURSE_CODE = _('Human-readable unique code: PY101, WEB202, etc.')
    COURSE_DESCRIPTION = _('Full course description (supports Markdown)')
    COURSE_IMAGE_URL = _('Course thumbnail/cover image (e.g., Cloudinary, S3, YouTube thumbnail)')
    COURSE_VIDEO_URL = _(
        'Intro/promo video (YouTube, Vimeo, direct MP4 link). Shown on course detail page.'
    )
    COURSE_CATEGORIES = _('Used for filtering in mobile app and course list')
    COURSE_INSTRUCTOR = _('Instructor who owns this course')
    COURSE_STATUS = _('Controls visibility and enrollment rules')
    COURSE_IS_ACTIVE = _('Quick toggle to show/hide course. Set to False for soft delete.')
    COURSE_IS_AUTO_ENROLLED = _(
        'Automatically enroll new users in this course (e.g., for introduction courses).'
    )
    COURSE_IS_INTRODUCTION = (
        "Labels this course as 'Introductory' level. Used for UI filtering and "
        "the 'Recommended for Beginners' section."
    )
    COURSE_MAX_STUDENTS = _('Maximum enrollment limit. Leave empty for unlimited.')
    COURSE_FILTER_TITLE = _('Filter by course title/name')

    COURSE_CATEGORY_IDS = _('List of category UUIDs to associate with this course')
    ENROLLED_COUNT = _('Current number of active enrollments')
    COURSE_IS_FULL = _('Whether the course has reached maximum capacity')
    COURSE_CAN_ENROLL = _('Whether new students can currently enroll')
    COURSE_CATEGORY_NAMES = _('Comma-separated list of category names')

    # Categories
    CATEGORY_NAME = _('e.g., Python, Data Science, Design')
    CATEGORY_IS_ACTIVE = _('Hide category without deleting')


class ErrorMessage:
    # Generic / common
    PASSWORDS_DO_NOT_MATCH = _('Passwords do not match.')
    USER_ACCOUNT_DISABLED = _('User account is disabled.')
    LOGOUT_FAILED = 'Logout failed'

    # Users / auth
    USERNAME_INVALID_CHARS = _('Username may contain letters, numbers, and underscores only.')
    INVALID_EMAIL_OR_PASSWORD = _('Invalid email or password.')
    OLD_PASSWORD_INCORRECT = _('Old password is incorrect.')
    NEW_PASSWORD_MUST_DIFFER = _('New password must be different from the old password.')
    INVALID_RESET_LINK = _('Invalid reset link.')
    INVALID_OR_EXPIRED_RESET_TOKEN = _('Invalid or expired reset token.')

    # Courses
    COURSE_TITLE_REQUIRED = _('Course title is required.')
    COURSE_TITLE_BLANK = _('Course title cannot be blank.')
    COURSE_TITLE_MAX_LENGTH = _('Course title cannot exceed 255 characters.')
    COURSE_CODE_REQUIRED = _('Course code is required.')
    COURSE_CODE_BLANK = _('Course code cannot be blank.')
    COURSE_CODE_EMPTY = _('Course code cannot be empty.')
    COURSE_CODE_INVALID_CHARS = _(
        'Course code can only contain letters, numbers, hyphens, and underscores.'
    )
    COURSE_CODE_ALREADY_EXISTS = _('Course code "%(code)s" already exists.')
    INVALID_OR_INACTIVE_CATEGORY_IDS = _(
        'The following category IDs are invalid or inactive: %(ids)s'
    )
    MAX_STUDENTS_MIN_1 = _('Maximum students must be at least 1.')
    MAX_STUDENTS_POSITIVE_OR_NULL = _(
        'Maximum students must be a positive number or null for unlimited enrollment.'
    )
    INVALID_STATUS = _('Invalid status. Must be one of: %(statuses)s')
    VIDEO_URL_INVALID_SCHEME = _('Video URL must start with http:// or https://')
    IMAGE_URL_INVALID_SCHEME = _('Image URL must start with http:// or https://')
    CANNOT_DISABLE_IN_PROGRESS_WITH_STUDENTS = _(
        'Cannot disable a course that is in progress with enrolled students.'
    )
    COURSE_ALREADY_DELETED = 'Course is already deleted.'
    CANNOT_DELETE_IN_PROGRESS_WITH_STUDENTS = _(
        'Cannot delete a course that is in progress with enrolled students.'
    )
    INVALID_STATUS_TRANSITION = _(
        'Invalid status transition from "%(from)s" to "%(to)s". '
        'Please follow the proper course workflow.'
    )
    CANNOT_SET_MAX_STUDENTS_BELOW_ENROLLED = _(
        'Cannot set maximum students to %(new)d. '
        'Course already has %(current)d enrolled student(s). '
        'Maximum must be at least %(current)d.'
    )

    # Enrollments
    COURSE_NOT_FOUND = _('Course not found.')
    CANNOT_ENROLL_IN_INACTIVE_COURSE = _('Cannot enroll in an inactive course.')
    CANNOT_ENROLL_WHEN_NOT_OPEN_TEMPLATE = _('Cannot enroll in a course that is %(status)s.')
    COURSE_AT_CAPACITY = _('Course has reached maximum capacity.')
    ALREADY_ENROLLED = _('You are already enrolled in this course.')
    CANNOT_ENROLL_AT_THE_MOMENT = _('Cannot enroll in this course at the moment.')

    # Categories
    CATEGORY_NAME_EMPTY = _('Category name cannot be empty.')
    CATEGORY_NAME_ALREADY_EXISTS = _('Category with this name already exists.')

    # Model-level validation
    ONLY_INSTRUCTORS_CAN_TEACH = _('Only users with Instructor role can teach courses.')
    ONLY_STUDENTS_CAN_BE_ENROLLED = _('Only students can be enrolled in courses.')
    COURSE_NOT_ACTIVE = _('This course is not active.')
    COURSE_NOT_OPEN_FOR_ENROLLMENT = _(
        'This course is not open for enrollment. '
        'Only courses with "Active" status accept new enrollments.'
    )
    COURSE_REACHED_MAX_CAPACITY = _('This course has reached maximum capacity.')


class SuccessMessage:
    """Non-error message strings used in API responses."""

    # Courses
    COURSE_DELETED_SUCCESSFULLY = _('Course deleted successfully.')

    # Enrollments
    ENROLLMENT_ENROLLED_SUCCESS = _('Successfully enrolled in course')
    ENROLLMENT_LEFT_COURSE_SUCCESS = _('Successfully left the course')

    # Authentication / users
    REGISTRATION_SUCCESS = _('Registration successful. Please login.')
    LOGIN_SUCCESS = _('Login successful')
    LOGOUT_SUCCESS = _('Logout successful')
    PASSWORD_RESET_EMAIL_SENT = _(
        'If an account exists with this email, a password reset link has been sent.'
    )
    PASSWORD_RESET_SUCCESS = _(
        'Password has been reset successfully. You can now login with your new password.'
    )
    PASSWORD_CHANGED_SUCCESS = _('Password changed successfully')

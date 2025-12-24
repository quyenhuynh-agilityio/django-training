from rest_framework import permissions

from utils.permissions import is_active_authenticated


class IsInstructor(permissions.BasePermission):
    """
    Permission: Only active, authenticated instructors are allowed.

    - Requires user to be authenticated and active.
    - Checks custom `is_instructor` flag/property.
    - Does not restrict based on HTTP methods (handled elsewhere if needed).
    """

    message = 'Only instructors are allowed to perform this action.'

    def has_permission(self, request, view):
        return bool(
            is_active_authenticated(request.user) and getattr(request.user, 'is_instructor', False)
        )


class IsCourseInstructor(permissions.BasePermission):
    """
    Permission: Course instructor (owner) or staff members only.

    Design:
    - View-level (`has_permission`): Ensures only active instructors can reach object-level checks.
    - Object-level (`has_object_permission`): Checks ownership or staff status for active users.
    - Staff members bypass ownership requirement (useful for admins/moderators).
    - No SAFE_METHODS differentiation here – handled by viewset action permissions if needed.
    """

    message = 'You must be the instructor of this course or a staff member.'

    def has_permission(self, request, view):
        return bool(
            is_active_authenticated(request.user) and getattr(request.user, 'is_instructor', False)
        )

    def has_object_permission(self, request, view, obj):
        return bool(
            is_active_authenticated(request.user)
            and (request.user.is_staff or obj.instructor == request.user)
        )


class IsStudent(permissions.BasePermission):
    """
    Permission: Only active, authenticated students are allowed.

    - Requires user to be authenticated and active.
    - Checks custom `is_student` flag/property.
    """

    message = 'Only students are allowed to perform this action.'

    def has_permission(self, request, view):
        return bool(
            is_active_authenticated(request.user) and getattr(request.user, 'is_student', False)
        )

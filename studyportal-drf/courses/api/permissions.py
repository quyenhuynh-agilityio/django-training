from rest_framework import permissions


class IsInstructor(permissions.BasePermission):
    """
    Permission: Authenticated instructor only.

    Why this exists:
    - Does NOT hide AllowAny
    - Does NOT depend on HTTP methods
    - Used explicitly by ViewSet actions (create, etc.)
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_instructor


class IsCourseInstructor(permissions.BasePermission):
    """
    Permission: Course owner (instructor) or staff.

    Design notes:
    - View-level check ensures only instructors reach object-level
    - Object-level check ensures ownership
    - No SAFE_METHODS logic here (handled by ViewSet)
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_instructor

    def has_object_permission(self, request, view, obj):
        return obj.instructor == request.user or request.user.is_staff


class IsStudent(permissions.BasePermission):
    """Only students can access"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_student

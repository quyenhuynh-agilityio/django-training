from rest_framework import permissions


class IsInstructorOrReadOnly(permissions.BasePermission):
    """
    Custom permission:
    - Read access: everyone
    - Write access: instructors only
    - Update/Delete: only course instructor (owner)
    """

    def has_permission(self, request, view):
        # Read permissions for everyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for authenticated instructors
        return request.user.is_authenticated and request.user.is_instructor()

    def has_object_permission(self, request, view, obj):
        # Read permissions for everyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for course instructor
        return obj.instructor == request.user


class IsInstructor(permissions.BasePermission):
    """Only instructors can access"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_instructor()


class IsStudent(permissions.BasePermission):
    """Only students can access"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_student()


class IsOwner(permissions.BasePermission):
    """Only the owner can access"""

    def has_object_permission(self, request, view, obj):
        # Check if obj has student attribute (for enrollments)
        if hasattr(obj, 'student'):
            return obj.student == request.user
        # Check if obj is the user themselves
        return obj == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission:
    - Read access: everyone
    - Write access: only owner
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions for everyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for owner
        if hasattr(obj, 'student'):
            return obj.student == request.user
        return obj == request.user

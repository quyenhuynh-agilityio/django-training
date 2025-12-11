"""
Enrollment Serializer Mixins

Reusable mixins for enrollment serializers.
"""

from rest_framework import serializers


class EnrollmentStudentInfoMixin:
    """Shared student identity fields for enrollment serializers."""

    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)

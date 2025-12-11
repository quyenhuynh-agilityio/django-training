"""
Enrollment API Serializers

This package provides serializers for Enrollment model operations.

Structure:
    - mixins.py: Reusable serializer components (mixins)
    - serializers.py: Enrollment serializers
"""

from django.db import transaction
from rest_framework import serializers

from courses.api.serializers import CourseListSerializer
from enrollments.models import Enrollment
from utils.serializers import AuditReadOnlyFieldsMixin

from .mixins import EnrollmentStudentInfoMixin


class EnrollmentBaseSerializer(
    AuditReadOnlyFieldsMixin,
    EnrollmentStudentInfoMixin,
    serializers.ModelSerializer,
):
    """
    Base enrollment serializer with common fields and read-only setup.
    Concrete serializers extend the field list to avoid duplication.
    """

    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id',
            'student',
            'student_name',
            'student_email',
            'status',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = AuditReadOnlyFieldsMixin.audit_fields('student')


class EnrollmentSerializer(EnrollmentBaseSerializer):
    """
    Enrollment Serializer for viewing enrollments
    """

    course = CourseListSerializer(read_only=True)

    class Meta(EnrollmentBaseSerializer.Meta):
        fields = EnrollmentBaseSerializer.Meta.fields + ['course']


class EnrolledStudentSerializer(EnrollmentBaseSerializer):
    """
    Serializer for viewing enrolled students in a course (for instructors).
    Shows student information without redundant course data.
    """

    student_username = serializers.CharField(source='student.username', read_only=True)

    class Meta(EnrollmentBaseSerializer.Meta):
        fields = EnrollmentBaseSerializer.Meta.fields + ['student_username']


class EnrollmentCreateSerializer(serializers.Serializer):
    """
    Serializer for creating new enrollments (student enrollment).
    """

    course_id = serializers.UUIDField(write_only=True, help_text='UUID of the course to enroll in')

    def validate(self, attrs):
        from courses.models import Course

        course_id = attrs['course_id']
        student = self.context['request'].user

        course = Course.objects.filter(id=course_id).first()
        if course is None:
            raise serializers.ValidationError({'course_id': 'Course not found.'}) from None

        # --- Business rule validations ---
        if not course.can_enroll():
            if not course.is_active:
                raise serializers.ValidationError(
                    {'course_id': 'Cannot enroll in inactive courses.'}
                )
            if course.status != 'active':
                raise serializers.ValidationError(
                    {
                        'course_id': (
                            f'Cannot enroll in {course.get_status_display().lower()} courses.'
                        )
                    }
                )
            if course.is_full:
                raise serializers.ValidationError(
                    {'course_id': 'Course has reached maximum capacity.'}
                )

        # Prevent duplicate enrollment
        if Enrollment.objects.filter(student=student, course=course, is_active=True).exists():
            raise serializers.ValidationError(
                {'course_id': 'You are already enrolled in this course.'}
            )

        # Add validated objects for create()
        attrs['course'] = course
        attrs['student'] = student
        return attrs

    def create(self, validated_data):
        """Create enrollment record."""
        course = validated_data.pop('course')
        student = validated_data.pop('student')
        validated_data.pop('course_id')

        # Guard against race conditions (capacity/duplicate enrollment)
        with transaction.atomic():
            locked_course = (
                course.__class__.objects.select_for_update()
                .select_related('instructor')
                .get(pk=course.pk)
            )

            if not locked_course.can_enroll():
                raise serializers.ValidationError(
                    {'course_id': 'Cannot enroll in this course at the moment.'}
                )

            if Enrollment.objects.filter(
                student=student, course=locked_course, is_active=True
            ).exists():
                raise serializers.ValidationError(
                    {'course_id': 'You are already enrolled in this course.'}
                )

            return Enrollment.objects.create(
                student=student, course=locked_course, **validated_data
            )


__all__ = [
    # Mixins
    'EnrollmentStudentInfoMixin',
    # Serializers
    'EnrollmentBaseSerializer',
    'EnrollmentSerializer',
    'EnrolledStudentSerializer',
    'EnrollmentCreateSerializer',
]

"""
Enrollment API Serializers

Structure:
- mixins.py       → shared serializer mixins
- serializers.py  → core Enrollment serializers (read, write, create)
"""

from django.db import transaction
from rest_framework import serializers

from courses.api.serializers import CourseListSerializer
from enrollments.models import Enrollment
from utils.serializers import AuditReadOnlyFieldsMixin

from .mixins import EnrollmentStudentInfoMixin

# ───────────────────────────────────────────────────────────────
# Base Serializer
# ───────────────────────────────────────────────────────────────


class EnrollmentBaseSerializer(
    AuditReadOnlyFieldsMixin,
    EnrollmentStudentInfoMixin,
    serializers.ModelSerializer,
):
    """
    Base serializer containing common enrollment fields.
    Extended by view-specific serializers to avoid duplication.
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


# ───────────────────────────────────────────────────────────────
# Display Serializers (READ)
# ───────────────────────────────────────────────────────────────


class EnrollmentSerializer(EnrollmentBaseSerializer):
    """Full Enrollment view serializer — includes course info."""

    course = CourseListSerializer(read_only=True)

    class Meta(EnrollmentBaseSerializer.Meta):
        fields = EnrollmentBaseSerializer.Meta.fields + ['course']


class EnrolledStudentSerializer(EnrollmentBaseSerializer):
    """
    Display serializer for instructors viewing student enrollments
    inside a course. Excludes course data.
    """

    student_username = serializers.CharField(
        source='student.username',
        read_only=True,
    )

    class Meta(EnrollmentBaseSerializer.Meta):
        fields = EnrollmentBaseSerializer.Meta.fields + ['student_username']


# ───────────────────────────────────────────────────────────────
# Create Enrollment Serializer (WRITE)
# ───────────────────────────────────────────────────────────────


class EnrollmentCreateSerializer(serializers.Serializer):
    """
    Create serializer for new student enrollments.
    """

    course_id = serializers.UUIDField(
        write_only=True,
        help_text='UUID of the course to enroll in',
    )

    def validate(self, attrs):
        from courses.models import Course

        course_id = attrs['course_id']
        student = self.context['request'].user

        # --- Course existence -------------------------------------------------
        course = Course.objects.filter(id=course_id).first()
        if not course:
            raise serializers.ValidationError({'course_id': 'Course not found.'})

        # --- Business rules ---------------------------------------------------
        if not course.can_enroll():
            if not course.is_active:
                raise serializers.ValidationError(
                    {'course_id': 'Cannot enroll in an inactive course.'}
                )

            if course.status != 'active':
                raise serializers.ValidationError(
                    {
                        'course_id': (
                            f'Cannot enroll in a course that is {course.get_status_display().lower()}.'
                        )
                    }
                )

            if course.is_full:
                raise serializers.ValidationError(
                    {'course_id': 'Course has reached maximum capacity.'}
                )

        # --- Duplicate enrollment ---------------------------------------------
        if Enrollment.objects.filter(
            student=student,
            course=course,
            is_active=True,
        ).exists():
            raise serializers.ValidationError(
                {'course_id': 'You are already enrolled in this course.'}
            )

        # Pass objects forward to create()
        attrs['course'] = course
        attrs['student'] = student
        return attrs

    # ----------------------------------------------------------------------

    def create(self, validated_data):
        """Create enrollment with race-condition protection."""
        course = validated_data.pop('course')
        student = validated_data.pop('student')
        validated_data.pop('course_id')

        with transaction.atomic():
            locked_course = course.__class__.objects.select_for_update().get(pk=course.pk)

            # Re-check constraints under DB lock
            if not locked_course.can_enroll():
                raise serializers.ValidationError(
                    {'course_id': 'Cannot enroll in this course at the moment.'}
                )

            if Enrollment.objects.filter(
                student=student,
                course=locked_course,
                is_active=True,
            ).exists():
                raise serializers.ValidationError(
                    {'course_id': 'You are already enrolled in this course.'}
                )

            return Enrollment.objects.create(
                student=student,
                course=locked_course,
                **validated_data,
            )

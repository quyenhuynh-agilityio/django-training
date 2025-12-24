"""
Enrollment API Serializers

Structure:
- serializers.py  → core Enrollment serializers (read, write, create)
"""

from django.db import transaction
from rest_framework import serializers

from core.serializers import get_audit_read_only_fields
from core.texts import ErrorMessage, HelpText
from courses.api.serializers import CourseListSerializer
from enrollments.models import Enrollment

# ───────────────────────────────────────────────────────────────
# Base Serializer
# ───────────────────────────────────────────────────────────────


class EnrollmentBaseSerializer(
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
        read_only_fields = get_audit_read_only_fields('student')


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
    Uses write_only course_id, returns full EnrollmentSerializer.
    """

    course_id = serializers.UUIDField(
        write_only=True,
        help_text=HelpText.ENROLL_COURSE_ID,
    )

    def validate_course_id(self, value):
        """Validate that course exists and is accessible"""
        from courses.models import Course

        try:
            course = Course.objects.get(id=value)
        except Course.DoesNotExist:
            raise serializers.ValidationError(ErrorMessage.COURSE_NOT_FOUND)  # noqa: B904

        return course  # Return the course object for reuse

    def validate(self, attrs):
        """Validate enrollment business rules"""
        # course_id is now a Course object from validate_course_id
        course = attrs['course_id']
        student = self.context['request'].user

        # --- Business rules ---------------------------------------------------
        if not course.can_enroll():
            if not course.is_active:
                raise serializers.ValidationError(
                    {'course_id': ErrorMessage.CANNOT_ENROLL_IN_INACTIVE_COURSE}
                )

            if course.status != 'active':
                raise serializers.ValidationError(
                    {
                        'course_id': ErrorMessage.CANNOT_ENROLL_WHEN_NOT_OPEN_TEMPLATE
                        % {'status': course.get_status_display().lower()}
                    }
                )

            if course.is_full:
                raise serializers.ValidationError({'course_id': ErrorMessage.COURSE_AT_CAPACITY})

        # --- Duplicate enrollment ---------------------------------------------
        if Enrollment.objects.filter(
            student=student,
            course=course,
            is_active=True,
        ).exists():
            raise serializers.ValidationError({'course_id': ErrorMessage.ALREADY_ENROLLED})

        # Store for create method
        attrs['course'] = course
        attrs['student'] = student
        return attrs

    def create(self, validated_data):
        """Create enrollment with race-condition protection."""
        course = validated_data['course']
        student = validated_data['student']

        with transaction.atomic():
            # Lock the course row to prevent race conditions
            locked_course = course.__class__.objects.select_for_update().get(pk=course.pk)

            # Re-check constraints under DB lock
            if not locked_course.can_enroll():
                raise serializers.ValidationError(
                    {'course_id': ErrorMessage.CANNOT_ENROLL_AT_THE_MOMENT}
                )

            if Enrollment.objects.filter(
                student=student,
                course=locked_course,
                is_active=True,
            ).exists():
                raise serializers.ValidationError({'course_id': ErrorMessage.ALREADY_ENROLLED})

            # Create the enrollment
            enrollment = Enrollment.objects.create(
                student=student,
                course=locked_course,
            )

            return enrollment

    def to_representation(self, instance):
        """Return full enrollment data with course info"""
        return EnrollmentSerializer(instance, context=self.context).data

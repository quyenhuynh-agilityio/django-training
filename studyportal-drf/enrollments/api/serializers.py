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


class PaginatedResponseSerializer(serializers.Serializer):
    """Base serializer for paginated responses"""

    count = serializers.IntegerField(min_value=0, required=True)
    next = serializers.URLField(required=False, allow_null=True)
    previous = serializers.URLField(required=False, allow_null=True)

    def validate_count(self, value):
        if value < 0:
            raise serializers.ValidationError('Count must be non-negative')
        return value


class EnrollmentListResponseSerializer(PaginatedResponseSerializer):
    """
    Response for: GET /enrollments/
    Returns paginated list of student's enrollments with course details
    """

    results = EnrollmentSerializer(many=True, required=True)

    def validate_results(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Results must be a list')
        return value


class EnrollmentDetailResponseSerializer(serializers.Serializer):
    """
    Response for: GET /enrollments/{id}/
    Returns complete enrollment details with nested course information
    """

    # Delegate to EnrollmentSerializer for validation
    def to_internal_value(self, data):
        serializer = EnrollmentSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def to_representation(self, instance):
        return EnrollmentSerializer(instance).data


class EnrollmentDataSerializer(serializers.Serializer):
    """Nested enrollment data for enroll response"""

    id = serializers.UUIDField(required=True)
    course = serializers.DictField(required=True)
    student = serializers.DictField(required=True)
    student_name = serializers.CharField(required=True, min_length=1)
    student_email = serializers.EmailField(required=True)
    status = serializers.CharField(required=True)
    is_active = serializers.BooleanField(required=True)
    created_at = serializers.DateTimeField(required=True)
    updated_at = serializers.DateTimeField(required=True)

    def validate_status(self, value):
        valid_statuses = ['active', 'completed', 'dropped']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            )
        return value

    def validate_course(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('Course must be a dictionary')

        required_fields = ['id', 'title', 'course_code']
        missing_fields = [field for field in required_fields if field not in value]

        if missing_fields:
            raise serializers.ValidationError(
                f'Course missing required fields: {", ".join(missing_fields)}'
            )
        return value

    def validate_student(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('Student must be a dictionary')

        # The student field might be just the UUID in some cases
        if isinstance(value, str):
            return value

        return value


class EnrollmentEnrollResponseSerializer(serializers.Serializer):
    """
    Response for: POST /enrollments/enroll/
    Returns success message and newly created enrollment details
    """

    message = serializers.CharField(required=True, min_length=1)
    data = EnrollmentDataSerializer(required=True)

    def validate_message(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Message cannot be empty')
        return value


class LeaveDataSerializer(serializers.Serializer):
    """Nested data for leave course response"""

    enrollment_id = serializers.UUIDField(required=True)
    status = serializers.CharField(required=True)

    def validate_status(self, value):
        if value != 'dropped':
            raise serializers.ValidationError('Status must be "dropped" after leaving')
        return value


class EnrollmentLeaveResponseSerializer(serializers.Serializer):
    """
    Response for: DELETE /enrollments/{id}/leave/
    Returns success message and updated enrollment status
    """

    message = serializers.CharField(required=True, min_length=1)
    data = LeaveDataSerializer(required=True)

    def validate_message(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Message cannot be empty')
        return value


__all__ = [
    'EnrollmentCreateSerializer',
    'EnrollmentSerializer',
    'EnrollmentListResponseSerializer',
    'EnrollmentDetailResponseSerializer',
    'EnrollmentEnrollResponseSerializer',
    'EnrollmentLeaveResponseSerializer',
]

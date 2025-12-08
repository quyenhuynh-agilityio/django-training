from rest_framework import serializers

from courses.api.serializers import CourseListSerializer
from enrollments.models import Enrollment


class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Enrollment Serializer for viewing enrollments
    """

    course = CourseListSerializer(read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id',
            'student',
            'student_name',
            'student_email',
            'course',
            'status',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'student', 'created_at', 'updated_at']


class EnrollmentCreateSerializer(serializers.Serializer):
    """
    Serializer for creating new enrollments (student enrollment).
    """

    course_id = serializers.UUIDField(write_only=True, help_text='UUID of the course to enroll in')

    def validate_course_id(self, value):
        """Validate course exists."""
        from courses.models import Course

        if not Course.objects.filter(id=value).exists():
            # `from None` removes traceback noise → resolves linter B904
            raise serializers.ValidationError('Course not found.') from None

        return value

    def validate(self, attrs):
        from courses.models import Course

        course_id = attrs['course_id']
        student = self.context['request'].user

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
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

        return Enrollment.objects.create(student=student, course=course, **validated_data)

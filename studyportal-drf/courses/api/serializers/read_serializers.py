"""
Course Read Serializers

Serializers for read-only operations (list and detail views):
- CourseListSerializer: Optimized for list views
- CourseDetailSerializer: Complete course details
- InstructorSerializer: Instructor information
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from categories.api.serializers import CategorySerializer
from courses.models import Course
from utils.serializers import AuditReadOnlyFieldsMixin

from .mixins import (
    CategoryNamesMixin,
    CourseCategoriesReadOnlyMixin,
    CourseEnrollmentComputedMixin,
)

User = get_user_model()


class InstructorSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for instructor information.

    Used to display instructor details in course responses.
    All fields are read-only to prevent accidental user modification.

    Note:
        Requires select_related('instructor') in viewset for optimal performance.
    """

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'full_name', 'first_name', 'last_name']
        read_only_fields = fields


class CourseListSerializer(
    AuditReadOnlyFieldsMixin,
    CourseEnrollmentComputedMixin,
    CourseCategoriesReadOnlyMixin,
    serializers.ModelSerializer,
):
    """
    Lightweight serializer for course list views.

    Optimized for performance with computed enrollment fields from mixins.
    Includes nested categories for filtering in mobile app and course list.

    Performance Requirements:
        Requires queryset optimization in viewset:
        - select_related('instructor')
        - prefetch_related('categories')
        - annotate(enrolled_count_computed=..., is_full_computed=..., can_enroll_computed=...)

    Use Case: GET /api/v1/courses/

    Response Structure:
        {
            "id": "uuid",
            "title": "Introduction to Python",
            "course_code": "PY101",
            "instructor_name": "John Doe",
            "categories": [{"id": "uuid", "name": "Programming"}, ...],
            "enrolled_count": 25,
            "is_full": false,
            "can_enroll": true,
            "max_students": 30,
            ...
        }
    """

    categories = CategorySerializer(
        many=True, read_only=True, help_text='List of categories this course belongs to'
    )
    instructor_name = serializers.CharField(
        source='instructor.full_name',
        read_only=True,
        help_text='Full name of the course instructor',
    )

    class Meta:
        model = Course
        fields = [
            # Basic info
            'id',
            'title',
            'course_code',
            'description',
            # Relationships
            'categories',
            'instructor_name',
            # Media
            'image_url',
            'video_url',
            # Status
            'status',
            'is_active',
            # Enrollment info (from CourseEnrollmentComputedMixin)
            'enrolled_count',
            'is_full',
            'can_enroll',
            'max_students',
            # Timestamps (from AuditReadOnlyFieldsMixin)
            'created_at',
        ]
        read_only_fields = AuditReadOnlyFieldsMixin.audit_fields(include_updated=False)


class CourseDetailSerializer(
    AuditReadOnlyFieldsMixin,
    CourseEnrollmentComputedMixin,
    CategoryNamesMixin,
    CourseCategoriesReadOnlyMixin,
    serializers.ModelSerializer,
):
    """
    Complete serializer for single course detail views.

    Includes all course information with nested related objects.
    Uses multiple mixins for enrollment stats, categories, and category names.

    Performance Requirements:
        Requires queryset optimization in viewset:
        - select_related('instructor')
        - prefetch_related('categories')
        - annotate(enrolled_count_computed=..., is_full_computed=..., can_enroll_computed=...)

    Use Case: GET /api/v1/courses/{id}/

    Response Structure:
        {
            "id": "uuid",
            "title": "Introduction to Python",
            "course_code": "PY101",
            "categories": [{"id": "uuid", "name": "Programming"}, ...],
            "category_names": "Programming, Python",
            "instructor": {"id": "uuid", "email": "...", "full_name": "John Doe"},
            "video_url": "https://youtube.com/...",
            "image_url": "https://cloudinary.com/...",
            "enrolled_count": 25,
            "is_full": false,
            "can_enroll": true,
            ...
        }
    """

    categories = CategorySerializer(
        many=True, read_only=True, help_text='List of categories this course belongs to'
    )
    instructor = InstructorSerializer(read_only=True, help_text='Complete instructor information')

    class Meta:
        model = Course
        fields = [
            # Basic info
            'id',
            'title',
            'course_code',
            'description',
            # Relationships
            'categories',
            'category_names',
            'instructor',
            # Media (used in mobile app & web)
            'video_url',
            'image_url',
            # Status
            'status',
            'is_active',
            'max_students',
            # Enrollment info (from CourseEnrollmentComputedMixin)
            'enrolled_count',
            'is_full',
            'can_enroll',
            # Timestamps (from AuditReadOnlyFieldsMixin)
            'created_at',
            'updated_at',
        ]
        read_only_fields = AuditReadOnlyFieldsMixin.audit_fields()

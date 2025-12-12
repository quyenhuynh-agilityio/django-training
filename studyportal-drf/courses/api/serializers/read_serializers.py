"""
Course Read Serializers

Serializers for read-only operations (list and detail views):
- CourseListSerializer: Optimized for list views
- CourseDetailSerializer: Complete course details
- InstructorSerializer: Instructor information
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from categories.api.serializes.category import CategorySerializer
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
    Includes nested categories for filtering.

    Queryset Requirements:
        - select_related('instructor')
        - prefetch_related('categories')
        - annotate(enrolled_count_computed, is_full_computed, can_enroll_computed)
    """

    categories = CategorySerializer(many=True, read_only=True)
    instructor_name = serializers.CharField(source='instructor.full_name', read_only=True)

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'course_code',
            'description',
            'categories',
            'instructor_name',
            'image_url',
            'video_url',
            'status',
            'is_active',
            'enrolled_count',
            'is_full',
            'can_enroll',
            'max_students',
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

    Queryset Requirements:
        - select_related('instructor')
        - prefetch_related('categories')
        - annotate(enrolled_count_computed, is_full_computed, can_enroll_computed)
    """

    categories = CategorySerializer(many=True, read_only=True)
    instructor = InstructorSerializer(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'course_code',
            'description',
            'categories',
            'category_names',
            'instructor',
            'video_url',
            'image_url',
            'status',
            'is_active',
            'max_students',
            'enrolled_count',
            'is_full',
            'can_enroll',
            'created_at',
            'updated_at',
        ]
        read_only_fields = AuditReadOnlyFieldsMixin.audit_fields()

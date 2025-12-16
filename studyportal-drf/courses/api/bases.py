"""
Course Serializer Base Classes

Reusable base classes for course serializers to reduce duplication.
These are NOT DRF mixins - they're standard Python base classes.
"""

from rest_framework import serializers


class CourseEnrollmentFieldsBase(serializers.Serializer):
    """
    Base class providing computed enrollment fields.

    Adds three read-only computed fields that handle both annotated
    values (from viewset) and fallback to model properties/methods.

    Usage:
        class MyCourseSerializer(CourseEnrollmentFieldsBase, serializers.ModelSerializer):
            class Meta:
                model = Course
                fields = [..., 'enrolled_count', 'is_full', 'can_enroll']
    """

    enrolled_count = serializers.SerializerMethodField(
        help_text='Current number of active enrollments'
    )
    is_full = serializers.SerializerMethodField(
        help_text='Whether the course has reached maximum capacity'
    )
    can_enroll = serializers.SerializerMethodField(
        help_text='Whether new students can currently enroll'
    )

    def get_enrolled_count(self, obj):
        """Get enrolled count from annotation or model property"""
        return getattr(obj, 'enrolled_count_computed', obj._enrolled_count)

    def get_is_full(self, obj):
        """Get is_full from annotation or model property"""
        return getattr(obj, 'is_full_computed', obj.is_full)

    def get_can_enroll(self, obj):
        """Get can_enroll from annotation or model method"""
        return getattr(obj, 'can_enroll_computed', obj.can_enroll())


class CategoryNamesFieldBase(serializers.Serializer):
    """
    Base class providing category_names computed field.

    Usage:
        class MyCourseSerializer(CategoryNamesFieldBase, serializers.ModelSerializer):
            class Meta:
                model = Course
                fields = [..., 'category_names']
    """

    category_names = serializers.SerializerMethodField(
        help_text='Comma-separated list of category names'
    )

    def get_category_names(self, obj):
        """Return comma-separated category names"""
        return ', '.join(obj.categories.values_list('name', flat=True))


__all__ = [
    'CourseEnrollmentFieldsBase',
    'CategoryNamesFieldBase',
]

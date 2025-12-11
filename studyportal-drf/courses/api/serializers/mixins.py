"""
Course Serializer Mixins

Reusable mixins for course serializers providing:
- Enrollment computed fields
- Category handling
- Code normalization and validation
- URL validation
"""

from drf_spectacular.utils import extend_schema_field

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from categories.models import Category
from courses.models import Course


class CourseEnrollmentComputedMixin(serializers.Serializer):
    """
    Mixin providing computed enrollment fields.

    Adds three read-only computed fields that handle both annotated
    values (from viewset) and fallback to model properties/methods.

    Fields:
        - enrolled_count: Number of active enrollments
        - is_full: Whether course has reached maximum capacity
        - can_enroll: Whether new students can currently enroll

    Note:
        The model uses _enrolled_count as the property name, but we expose
        it as enrolled_count in the API for cleaner interface.

    Usage:
        class MyCourseSerializer(CourseEnrollmentComputedMixin, serializers.ModelSerializer):
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
        """
        Get enrolled count from annotation or model property.

        Prefers annotated value for performance, falls back to model's _enrolled_count.
        """
        # Check for annotation first (from viewset queryset.annotate())
        if hasattr(obj, 'enrolled_count_computed'):
            return obj.enrolled_count_computed
        # Fall back to model's _enrolled_count property
        return obj._enrolled_count

    def get_is_full(self, obj):
        """
        Get is_full from annotation or model method.

        The model's is_full() is a method, not a property.
        """
        # Check for annotation first
        if hasattr(obj, 'is_full_computed'):
            return obj.is_full_computed
        # Fall back to model method
        return obj.is_full()

    def get_can_enroll(self, obj):
        """
        Get can_enroll from annotation or model method.

        The model's can_enroll() is a method that checks:
        - is_active == True
        - status == STATUS_ACTIVE
        - not is_full()
        """
        # Check for annotation first
        if hasattr(obj, 'can_enroll_computed'):
            return obj.can_enroll_computed
        # Fall back to model method
        return obj.can_enroll()


class CourseCategoriesReadOnlyMixin(serializers.Serializer):
    """
    Mixin providing read-only nested categories.

    Adds a nested CategorySerializer field for displaying
    course categories in API responses.

    Note:
        Requires prefetch_related('categories') in viewset for optimal performance.
        The categories field should be explicitly defined in the serializer using this mixin.

    Usage:
        class MyCourseSerializer(CourseCategoriesReadOnlyMixin, serializers.ModelSerializer):
            categories = CategorySerializer(many=True, read_only=True)

            class Meta:
                model = Course
                fields = [..., 'categories']
    """


class CategoryNamesMixin(serializers.Serializer):
    """
    Mixin providing comma-separated category names.

    Adds a computed field that returns category names as a single
    comma-separated string for simplified display.

    Note: This is redundant if full category objects are already included.
          Consider using only when categories list is not needed.

    Usage:
        class MyCourseSerializer(CategoryNamesMixin, serializers.ModelSerializer):
            class Meta:
                model = Course
                fields = [..., 'category_names']
    """

    category_names = serializers.SerializerMethodField(
        read_only=True, help_text='Comma-separated list of category names'
    )

    @extend_schema_field(serializers.CharField())
    def get_category_names(self, obj):
        """
        Return comma-separated category names.

        Uses values_list for efficient query if not prefetched.
        """
        return ', '.join(obj.categories.values_list('name', flat=True))


class UppercaseCodeMixin:
    """
    Mixin ensuring course_code is normalized to uppercase.

    Provides field-level validation for course_code that:
    - Normalizes to uppercase
    - Strips whitespace
    - Validates format (alphanumeric with hyphens/underscores)
    - Ensures uniqueness (case-insensitive)

    Note:
        The model has unique=True on course_code, so database-level
        uniqueness is enforced. This validation provides better error
        messages and handles case-insensitivity.

    Usage:
        class MyCourseSerializer(UppercaseCodeMixin, serializers.ModelSerializer):
            # course_code validation is automatically applied
    """

    def validate_course_code(self, value):
        """
        Validate and normalize course code.

        Args:
            value: Raw course code string

        Returns:
            Normalized course code (uppercase, stripped)

        Raises:
            ValidationError: If code is empty, invalid format, or already exists
        """
        if not value or not value.strip():
            raise serializers.ValidationError(_('Course code cannot be empty.'), code='required')

        # Normalize: uppercase and strip whitespace (matches model expectation)
        code = value.upper().strip()

        # Validate length (model max_length=20)
        if len(code) > 20:
            raise serializers.ValidationError(
                _('Course code cannot exceed 20 characters.'), code='max_length'
            )

        # Validate format: alphanumeric with optional hyphens/underscores
        # Examples: PY101, WEB202, CS-101, DATA_SCI
        import re

        if not re.match(r'^[A-Z0-9_-]+$', code):
            raise serializers.ValidationError(
                _('Course code can only contain letters, numbers, hyphens, and underscores.'),
                code='invalid_format',
            )

        # Check uniqueness (model has unique=True but this gives better error message)
        queryset = Course.objects.filter(course_code=code)

        # Exclude current instance when updating
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                _('Course code "%(code)s" already exists. Please choose a different code.'),
                params={'code': code},
                code='unique',
            )

        return code


class CategoryIDsValidationMixin:
    """
    Mixin for validating and applying category_ids.

    Provides:
    - Field-level validation for category_ids list
    - Helper method to apply categories to course instance
    - Duplicate removal
    - Active category filtering

    Usage:
        class MyCourseSerializer(CategoryIDsValidationMixin, serializers.ModelSerializer):
            category_ids = serializers.ListField(...)

            def create(self, validated_data):
                category_ids = validated_data.pop('category_ids', [])
                course = Course.objects.create(**validated_data)
                self._apply_category_ids(course, category_ids)
                return course
    """

    def validate_category_ids(self, value):
        """
        Validate that all provided category IDs exist and are active.

        Args:
            value: List of category UUIDs

        Returns:
            List of validated, deduplicated UUIDs

        Raises:
            ValidationError: If any category IDs are invalid or inactive
        """
        if not value:
            return []

        # Remove duplicates while preserving order
        unique_ids = list(dict.fromkeys(value))

        # Check which IDs exist and are active in database
        existing_ids = set(
            Category.objects.filter(id__in=unique_ids, is_active=True).values_list('id', flat=True)
        )

        invalid_ids = set(unique_ids) - existing_ids

        if invalid_ids:
            # Sort for consistent error messages
            invalid_ids_list = sorted(str(id) for id in invalid_ids)
            raise serializers.ValidationError(
                _('The following category IDs are invalid or inactive: %(ids)s'),
                params={'ids': ', '.join(invalid_ids_list)},
                code='invalid_categories',
            )

        return unique_ids

    def _apply_category_ids(self, instance, category_ids):
        """
        Apply categories to course instance.

        Args:
            instance: Course instance
            category_ids: List of category UUIDs or None

        Note:
            If category_ids is None, categories are not modified (useful for PATCH).
            If category_ids is empty list, all categories are removed.
        """
        if category_ids is not None:
            instance.categories.set(category_ids)


class URLValidationMixin:
    """
    Mixin providing URL field validation.

    Validates that URLs:
    - Start with http:// or https://
    - Don't exceed maximum length (500 chars per model)
    - Are properly formatted

    Note:
        Model uses URLField with max_length=500 for both image_url and video_url.

    Usage:
        class MyCourseSerializer(URLValidationMixin, serializers.ModelSerializer):
            # Automatically validates video_url and image_url fields
    """

    def validate_url_field(self, value, field_name, max_length=500):
        """
        Generic URL validation helper.

        Args:
            value: URL string to validate
            field_name: Name of the field for error messages
            max_length: Maximum allowed URL length (default 500)

        Returns:
            Validated and cleaned URL

        Raises:
            ValidationError: If URL format is invalid
        """
        if not value:
            return value

        value = value.strip()

        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError(
                _(f'{field_name} must start with http:// or https://'), code='invalid_url_scheme'
            )

        if len(value) > max_length:
            raise serializers.ValidationError(
                _(f'{field_name} cannot exceed {max_length} characters'), code='max_length'
            )

        return value

    def validate_video_url(self, value):
        """Validate video URL format (YouTube, Vimeo, direct MP4 link)."""
        return self.validate_url_field(value, 'Video URL')

    def validate_image_url(self, value):
        """Validate image URL format (Cloudinary, S3, YouTube thumbnail)."""
        return self.validate_url_field(value, 'Image URL')

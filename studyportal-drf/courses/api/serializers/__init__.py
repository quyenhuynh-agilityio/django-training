"""
Course API Serializers

This package provides serializers for Course model operations following Django REST Framework
best practices with a mixin-based architecture for code reusability.

Structure:
    - mixins.py: Reusable serializer components (mixins)
    - read_serializers.py: Read-only serializers (list, detail)
    - write_serializers.py: Write serializers (create, update)
"""

# Import mixins
from .mixins import (
    CategoryIDsValidationMixin,
    CategoryNamesMixin,
    CourseCategoriesReadOnlyMixin,
    CourseEnrollmentComputedMixin,
    UppercaseCodeMixin,
    URLValidationMixin,
)

# Import serializers
from .read_serializers import (
    CourseDetailSerializer,
    CourseListSerializer,
    InstructorSerializer,
)
from .write_serializers import (
    CourseCreateUpdateSerializer,
    CourseWriteSerializer,
)

__all__ = [
    # Mixins
    'CourseEnrollmentComputedMixin',
    'CourseCategoriesReadOnlyMixin',
    'CategoryNamesMixin',
    'UppercaseCodeMixin',
    'CategoryIDsValidationMixin',
    'URLValidationMixin',
    # Read Serializers
    'InstructorSerializer',
    'CourseListSerializer',
    'CourseDetailSerializer',
    # Write Serializers
    'CourseWriteSerializer',
    'CourseCreateUpdateSerializer',  # Backward compatibility alias
]

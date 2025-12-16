"""
Course Read Serializers

Serializers for read-only operations (list and detail views):
- CourseListSerializer: Optimized for list views
- CourseDetailSerializer: Complete course details
- InstructorSerializer: Instructor information
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from categories.api.serializers import CategorySerializer
from categories.models import Category
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


class CourseWriteSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating courses.

    Handles write operations with comprehensive validation.

    Business Rules:
        - category_ids must reference existing, active categories
        - course_code is auto-normalized to uppercase and must be unique
        - max_students must be positive or null for unlimited
        - Cannot disable in-progress courses with enrolled students
        - Cannot reduce max_students below current enrollment
        - Status transitions must follow valid workflow
    """

    category_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        allow_empty=True,
        help_text='List of category UUIDs to associate with this course',
    )

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'course_code',
            'description',
            'category_ids',
            'video_url',
            'image_url',
            'status',
            'is_active',
            'max_students',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'title': {
                'required': True,
                'max_length': 255,
                'error_messages': {
                    'required': _('Course title is required.'),
                    'blank': _('Course title cannot be blank.'),
                    'max_length': _('Course title cannot exceed 255 characters.'),
                },
            },
            'course_code': {
                'required': True,
                'max_length': 20,
                'error_messages': {
                    'required': _('Course code is required.'),
                    'blank': _('Course code cannot be blank.'),
                },
            },
            'description': {
                'required': False,
                'allow_blank': True,
            },
            'max_students': {
                'required': False,
                'allow_null': True,
                'min_value': 1,
                'error_messages': {'min_value': _('Maximum students must be at least 1.')},
            },
            'video_url': {
                'required': False,
                'allow_blank': True,
                'max_length': 500,
            },
            'image_url': {
                'required': False,
                'allow_blank': True,
                'max_length': 500,
            },
            'status': {
                'required': False,
            },
            'is_active': {
                'required': False,
            },
        }

    def validate_course_code(self, value):
        """Normalize course code to uppercase"""
        return value.upper() if value else value

    def validate_category_ids(self, value):
        """Validate that all category IDs exist and are active"""
        if not value:
            return []

        # Check if all categories exist and are active
        existing_categories = Category.objects.filter(id__in=value, is_active=True).values_list(
            'id', flat=True
        )

        existing_set = set(existing_categories)
        provided_set = set(value)

        missing_ids = provided_set - existing_set

        if missing_ids:
            raise serializers.ValidationError(
                _('The following category IDs are invalid or inactive: %(ids)s')
                % {'ids': ', '.join(str(id) for id in missing_ids)}
            )

        return value

    def validate_max_students(self, value):
        """Validate that max_students is positive or null"""
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                _('Maximum students must be a positive number or null for unlimited enrollment.')
            )
        return value

    def validate_status(self, value):
        """Validate status is a valid choice"""
        valid_statuses = [choice[0] for choice in Course.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                _('Invalid status. Must be one of: %(statuses)s')
                % {'statuses': ', '.join(valid_statuses)}
            )
        return value

    def validate_video_url(self, value):
        """Validate video URL format if provided"""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError(_('Video URL must start with http:// or https://'))
        return value

    def validate_image_url(self, value):
        """Validate image URL format if provided"""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError(_('Image URL must start with http:// or https://'))
        return value

    def validate(self, attrs):
        """
        Object-level validation for business rules.

        Enforces:
            - Cannot disable in-progress courses with enrolled students
            - Valid status transitions
            - Cannot reduce max_students below current enrollment
        """
        if self.instance:
            self._validate_is_active_change(attrs)
            self._validate_status_transition(attrs)
            self._validate_max_students_change(attrs)

        return attrs

    def _validate_is_active_change(self, attrs):
        """Prevent disabling in-progress courses with students"""
        new_active = attrs.get('is_active', self.instance.is_active)

        if self.instance.is_active and not new_active:
            enrolled_count = getattr(
                self.instance,
                '_enrolled_count',
                self.instance.enrollments.filter(is_active=True).count(),
            )

            if self.instance.status == Course.STATUS_IN_PROGRESS and enrolled_count > 0:
                raise serializers.ValidationError(
                    {
                        'is_active': _(
                            'Cannot disable a course that is in progress with enrolled students.'
                        )
                    }
                )

    def _validate_status_transition(self, attrs):
        """Validate status change follows valid workflow"""
        new_status = attrs.get('status', self.instance.status)

        if new_status != self.instance.status:
            if not self._is_valid_transition(self.instance.status, new_status):
                raise serializers.ValidationError(
                    {
                        'status': _(
                            'Invalid status transition from "%(from)s" to "%(to)s". '
                            'Please follow the proper course workflow.'
                        )
                        % {
                            'from': self.instance.get_status_display(),
                            'to': dict(Course.STATUS_CHOICES).get(new_status, new_status),
                        }
                    }
                )

    def _validate_max_students_change(self, attrs):
        """Validate max_students isn't below current enrollment"""
        if 'max_students' not in attrs:
            return

        new_max = attrs['max_students']

        enrolled_count = getattr(
            self.instance,
            '_enrolled_count',
            self.instance.enrollments.filter(is_active=True).count(),
        )

        if new_max is not None and enrolled_count > 0 and new_max < enrolled_count:
            raise serializers.ValidationError(
                {
                    'max_students': _(
                        'Cannot set maximum students to %(new)d. '
                        'Course already has %(current)d enrolled student(s). '
                        'Maximum must be at least %(current)d.'
                    )
                    % {'new': new_max, 'current': enrolled_count}
                }
            )

    @staticmethod
    def _is_valid_transition(from_status, to_status):
        """
        Check if status transition is valid.

        Workflow:
            draft → active, in_progress
            active → in_progress, completed, draft
            in_progress → completed, active
            completed → draft
        """
        if from_status == to_status:
            return True

        valid_transitions = {
            Course.STATUS_DRAFT: [Course.STATUS_ACTIVE, Course.STATUS_IN_PROGRESS],
            Course.STATUS_ACTIVE: [
                Course.STATUS_IN_PROGRESS,
                Course.STATUS_COMPLETED,
                Course.STATUS_DRAFT,
            ],
            Course.STATUS_IN_PROGRESS: [Course.STATUS_COMPLETED, Course.STATUS_ACTIVE],
            Course.STATUS_COMPLETED: [Course.STATUS_DRAFT],
        }

        return to_status in valid_transitions.get(from_status, [])

    @transaction.atomic
    def create(self, validated_data):
        """
        Create a new course with associated categories.

        The instructor field is set in viewset's perform_create.
        Model's save() calls full_clean() for additional validation.
        """
        category_ids = validated_data.pop('category_ids', [])

        # Set default values if not provided
        if 'status' not in validated_data:
            validated_data['status'] = Course.STATUS_DRAFT
        if 'is_active' not in validated_data:
            validated_data['is_active'] = True

        course = Course.objects.create(**validated_data)

        # Associate categories
        if category_ids:
            categories = Category.objects.filter(id__in=category_ids)
            course.categories.set(categories)

        return course

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Update existing course and its relationships.

        Handles both partial (PATCH) and full (PUT) updates.
        Model's save() calls full_clean() for additional validation.
        """
        category_ids = validated_data.pop('category_ids', None)

        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        # Update categories if provided
        if category_ids is not None:
            categories = Category.objects.filter(id__in=category_ids)
            instance.categories.set(categories)

        instance.refresh_from_db()
        return instance

    def to_representation(self, instance):
        """Return detailed course data after create/update"""
        return CourseDetailSerializer(instance, context=self.context).data


# Alias for backward compatibility
CourseCreateUpdateSerializer = CourseWriteSerializer


__all__ = [
    'InstructorSerializer',
    'CourseListSerializer',
    'CourseDetailSerializer',
    'CourseWriteSerializer',
    'CourseCreateUpdateSerializer',
]

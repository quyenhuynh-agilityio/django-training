"""
Course Write Serializers

Serializers for write operations (create and update):
- CourseWriteSerializer: Handles create and update with comprehensive validation
"""

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from courses.models import Course

from .mixins import CategoryIDsValidationMixin, UppercaseCodeMixin, URLValidationMixin


class CourseWriteSerializer(
    UppercaseCodeMixin,
    CategoryIDsValidationMixin,
    URLValidationMixin,
    serializers.ModelSerializer,
):
    """
    Serializer for creating and updating courses.

    Handles write operations with comprehensive validation using mixins
    for code normalization, category validation, and URL validation.

    Use Cases:
        - POST /api/v1/courses/ (create new course)
        - PUT/PATCH /api/v1/courses/{id}/ (update existing course)

    Instructor Assignment:
        The instructor field is automatically set from request.user in the
        viewset's perform_create method.

    Business Rules Enforced:
        1. category_ids must reference existing, active Category objects (CategoryIDsValidationMixin)
        2. course_code must be unique (model has unique=True), auto-normalized to uppercase (UppercaseCodeMixin)
        3. max_students must be positive or null for unlimited capacity
        4. video_url and image_url must be valid HTTP/HTTPS URLs (URLValidationMixin)
        5. Cannot disable courses with status=in_progress and enrolled students (matches model.clean())
        6. Cannot reduce max_students below current enrolled_count
        7. Status transitions must follow valid workflow

    Request Example:
        POST /api/v1/courses/
        {
            "title": "Introduction to Python",
            "course_code": "py101",
            "description": "Learn Python basics",
            "category_ids": ["uuid1", "uuid2"],
            "video_url": "https://youtube.com/watch?v=...",
            "image_url": "https://cloudinary.com/image.jpg",
            "max_students": 30,
            "status": "draft"
        }

    Response:
        Returns the created/updated course (same format as CourseDetailSerializer would provide)

    Notes:
        - Uses transaction.atomic for data integrity
        - All validation errors include helpful context and error codes
        - Calls model's save() which triggers full_clean() for additional validation
        - Mixins provide reusable validation logic
    """

    category_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        allow_empty=True,
        default=list,
        help_text='List of category UUIDs to associate with this course',
    )

    class Meta:
        model = Course
        fields = [
            # Basic info
            'id',
            'title',
            'course_code',
            'description',
            # Write-only relationship field
            'category_ids',
            # Media
            'video_url',
            'image_url',
            # Status
            'status',
            'is_active',
            'max_students',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'title': {
                'required': True,
                'max_length': 255,
                'help_text': 'Public course title',
                'error_messages': {
                    'required': _('Course title is required.'),
                    'blank': _('Course title cannot be blank.'),
                    'max_length': _('Course title cannot exceed 255 characters.'),
                },
            },
            'course_code': {
                'required': True,
                'max_length': 20,
                'help_text': 'Unique course code (automatically converted to uppercase). Examples: PY101, WEB202',
                'error_messages': {
                    'required': _('Course code is required.'),
                    'blank': _('Course code cannot be blank.'),
                },
            },
            'description': {
                'required': False,
                'allow_blank': True,
                'help_text': 'Full course description (supports Markdown)',
            },
            'max_students': {
                'required': False,
                'allow_null': True,
                'help_text': 'Maximum enrollment limit. Leave empty for unlimited',
                'error_messages': {'min_value': _('Maximum students must be at least 1.')},
            },
            'video_url': {
                'required': False,
                'allow_blank': True,
                'max_length': 500,
                'help_text': 'Intro/promo video (YouTube, Vimeo, direct MP4 link). Shown on course detail page',
            },
            'image_url': {
                'required': False,
                'allow_blank': True,
                'max_length': 500,
                'help_text': 'Course thumbnail/cover image (e.g., Cloudinary, S3, YouTube thumbnail)',
            },
            'status': {
                'required': False,
                'default': Course.STATUS_DRAFT,
                'help_text': 'Controls visibility and enrollment rules',
            },
            'is_active': {
                'required': False,
                'default': True,
                'help_text': 'Quick toggle to show/hide course. Set to False for soft delete',
            },
        }

    def validate_max_students(self, value):
        """
        Validate maximum student capacity.

        Args:
            value: Integer or None

        Returns:
            Validated max_students value

        Raises:
            ValidationError: If value is not positive
        """
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                _('Maximum students must be a positive number or null for unlimited enrollment.'),
                code='invalid_max_students',
            )
        return value

    def validate_status(self, value):
        """
        Validate status field value.

        Args:
            value: Status string

        Returns:
            Validated status

        Raises:
            ValidationError: If status is not in valid choices
        """
        valid_statuses = [choice[0] for choice in Course.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                _('Invalid status. Must be one of: %(statuses)s'),
                params={'statuses': ', '.join(valid_statuses)},
                code='invalid_choice',
            )
        return value

    def validate(self, attrs):
        """
        Object-level validation enforcing business rules.

        Validates complex business rules that require multiple fields or
        database state checking. These validations complement the model's
        clean() method.

        Rules Enforced:
            1. Cannot disable courses in progress with enrolled students (matches model.clean())
            2. Status transitions must be valid according to workflow
            3. Cannot reduce max_students below current enrollment count

        Args:
            attrs: Dictionary of validated field data

        Returns:
            Validated attributes dictionary

        Raises:
            ValidationError: If any business rule is violated
        """
        instance = self.instance

        # Skip complex validations for new courses
        if not instance:
            return attrs

        # Rule 1: Prevent disabling in-progress courses with students
        # This matches the model's clean() validation
        new_active = attrs.get('is_active', instance.is_active)
        if instance.is_active and not new_active:
            if instance.status == Course.STATUS_IN_PROGRESS and instance._enrolled_count > 0:
                raise serializers.ValidationError(
                    {
                        'is_active': _(
                            'Cannot disable a course that is in progress with enrolled students.'
                        )
                    },
                    code='course_in_progress',
                )

        # Rule 2: Validate status transitions
        new_status = attrs.get('status', instance.status)
        if new_status != instance.status:
            if not self._is_valid_status_transition(instance.status, new_status):
                raise serializers.ValidationError(
                    {
                        'status': _(
                            'Invalid status transition from "%(from)s" to "%(to)s". '
                            'Please follow the proper course workflow.'
                        )
                        % {
                            'from': instance.get_status_display(),
                            'to': dict(Course.STATUS_CHOICES).get(new_status, new_status),
                        }
                    },
                    code='invalid_status_transition',
                )

        # Rule 3: Validate max_students against current enrollment
        if 'max_students' in attrs:
            new_max = attrs['max_students']
            current_enrolled = instance._enrolled_count

            if new_max is not None and current_enrolled > 0 and new_max < current_enrolled:
                raise serializers.ValidationError(
                    {
                        'max_students': _(
                            'Cannot set maximum students to %(new)d. '
                            'Course already has %(current)d enrolled student(s). '
                            'Maximum must be at least %(current)d.'
                        )
                        % {'new': new_max, 'current': current_enrolled}
                    },
                    code='max_students_exceeded',
                )

        return attrs

    @staticmethod
    def _is_valid_status_transition(from_status, to_status):
        """
        Check if a status transition is valid according to workflow.

        Valid Course Status Workflow:
            draft → active, in_progress
            active → in_progress, completed, draft
            in_progress → completed, active
            completed → draft (for reset)

        Args:
            from_status: Current status
            to_status: Desired new status

        Returns:
            bool: True if transition is valid, False otherwise
        """
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

        # Allow staying in same status
        if from_status == to_status:
            return True

        return to_status in valid_transitions.get(from_status, [])

    @transaction.atomic
    def create(self, validated_data):
        """
        Create a new course with associated categories.

        Uses database transaction to ensure atomicity.
        The instructor field must be set in the viewset's perform_create.

        Args:
            validated_data: Validated data from serializer

        Returns:
            Created Course instance with relationships

        Note:
            Model's save() will call full_clean() which includes additional validation
            like ensuring instructor has role='instructor'.
        """
        category_ids = validated_data.pop('category_ids', [])

        # Create course instance (save() calls full_clean())
        course = Course.objects.create(**validated_data)

        # Apply categories using mixin helper
        self._apply_category_ids(course, category_ids)

        return course

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Update existing course and its relationships.

        Uses database transaction to ensure atomicity.
        Handles both partial (PATCH) and full (PUT) updates.

        Args:
            instance: Existing Course instance
            validated_data: Validated data from serializer

        Returns:
            Updated Course instance with refreshed relationships

        Note:
            Model's save() will call full_clean() which includes additional validation.
        """
        category_ids = validated_data.pop('category_ids', None)

        # Update course fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Save will trigger model's full_clean() for additional validation
        instance.save()

        # Apply categories using mixin helper (None means no change for PATCH)
        self._apply_category_ids(instance, category_ids)

        # Refresh to ensure we have latest data
        instance.refresh_from_db()

        return instance


# Backward compatibility alias
CourseCreateUpdateSerializer = CourseWriteSerializer

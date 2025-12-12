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
        default=list,
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
                'default': Course.STATUS_DRAFT,
            },
            'is_active': {
                'required': False,
                'default': True,
            },
        }

    def validate_max_students(self, value):
        """Validate that max_students is positive or null."""
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                _('Maximum students must be a positive number or null for unlimited enrollment.'),
                code='invalid_max_students',
            )
        return value

    def validate_status(self, value):
        """Validate status is a valid choice."""
        valid_statuses = [choice[0] for choice in Course.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                _('Invalid status. Must be one of: %(statuses)s')
                % {'statuses': ', '.join(valid_statuses)},
                code='invalid_choice',
            )
        return value

    def validate(self, attrs):
        """
        Object-level validation for business rules.

        Enforces:
            - Cannot disable in-progress courses with enrolled students
            - Valid status transitions
            - Cannot reduce max_students below current enrollment
        """
        if not self.instance:
            return attrs

        self._validate_is_active_change(attrs)
        self._validate_status_transition(attrs)
        self._validate_max_students_change(attrs)

        return attrs

    def _validate_is_active_change(self, attrs):
        """Prevent disabling in-progress courses with students."""
        new_active = attrs.get('is_active', self.instance.is_active)

        if self.instance.is_active and not new_active:
            if (
                self.instance.status == Course.STATUS_IN_PROGRESS
                and self.instance._enrolled_count > 0
            ):
                raise serializers.ValidationError(
                    {
                        'is_active': _(
                            'Cannot disable a course that is in progress with enrolled students.'
                        )
                    },
                    code='course_in_progress',
                )

    def _validate_status_transition(self, attrs):
        """Validate status change follows valid workflow."""
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
                    },
                    code='invalid_status_transition',
                )

    def _validate_max_students_change(self, attrs):
        """Validate max_students isn't below current enrollment."""
        if 'max_students' not in attrs:
            return

        new_max = attrs['max_students']
        current_enrolled = self.instance._enrolled_count

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
        course = Course.objects.create(**validated_data)
        self._apply_category_ids(course, category_ids)
        return course

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Update existing course and its relationships.

        Handles both partial (PATCH) and full (PUT) updates.
        Model's save() calls full_clean() for additional validation.
        """
        category_ids = validated_data.pop('category_ids', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        self._apply_category_ids(instance, category_ids)
        instance.refresh_from_db()

        return instance


CourseCreateUpdateSerializer = CourseWriteSerializer

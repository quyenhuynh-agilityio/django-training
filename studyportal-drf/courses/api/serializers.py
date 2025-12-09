from rest_framework import serializers

from categories.api.serializers import CategorySerializer
from courses.models import Course


class InstructorSerializer(serializers.Serializer):
    """
    Nested Instructor Serializer
    Used in course detail to show instructor info
    """

    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)


class CourseListSerializer(serializers.ModelSerializer):
    """
    Course List Serializer - Limited fields for list view

    Used for: GET /api/v1/courses/

    Fields include:
    - Basic info (id, title, course_code, description)
    - Categories (nested)
    - Instructor name (read-only)
    - Enrollment stats (read-only)
    - Status and availability
    """

    categories = CategorySerializer(many=True, read_only=True)
    instructor_name = serializers.CharField(source='instructor.full_name', read_only=True)
    enrolled_count = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    can_enroll = serializers.BooleanField(read_only=True)

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
            'status',
            'is_active',
            'enrolled_count',
            'is_full',
            'can_enroll',
            'max_students',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CourseDetailSerializer(serializers.ModelSerializer):
    """
    Course Detail Serializer - Full details for single course view

    Used for: GET /api/v1/courses/{id}/

    Includes all course information plus:
    - Full instructor details (nested)
    - All categories (nested)
    - Enrollment statistics
    """

    categories = CategorySerializer(many=True, read_only=True)
    instructor = InstructorSerializer(read_only=True)
    enrolled_count = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    can_enroll = serializers.BooleanField(read_only=True)
    category_names = serializers.SerializerMethodField()

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
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_category_names(self, obj):
        """Get comma-separated category names"""
        return ', '.join([cat.name for cat in obj.categories.all()])


class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Course Create/Update Serializer - For instructors

    Used for:
    - POST /api/v1/courses/ (create)
    - PUT/PATCH /api/v1/courses/{id}/ (update)

    Validation:
    - category_ids must exist
    - course_code must be unique
    - max_students must be positive
    """

    category_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text='List of category UUIDs',
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

    def validate_category_ids(self, value):
        """Validate category IDs exist"""
        from categories.models import Category

        if value:
            existing_count = Category.objects.filter(id__in=value).count()
            if existing_count != len(value):
                raise serializers.ValidationError('Some category IDs are invalid.')
        return value

    def validate_max_students(self, value):
        """Validate max_students is positive"""
        if value is not None and value <= 0:
            raise serializers.ValidationError('Must be a positive number.')
        return value

    def validate_course_code(self, value):
        """Validate course code is unique"""
        value = value.upper().strip()

        # Check uniqueness (exclude current instance if updating)
        queryset = Course.objects.filter(course_code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError('Course code already exists.')

        return value

    def create(self, validated_data):
        """Create course with categories"""
        category_ids = validated_data.pop('category_ids', [])
        course = Course.objects.create(**validated_data)

        if category_ids:
            course.categories.set(category_ids)

        return course

    def validate(self, attrs):
        """Validate course update - prevent disabling in-progress courses with students"""
        if self.instance:
            # Check if trying to disable a course
            is_active = attrs.get('is_active', self.instance.is_active)
            if self.instance.is_active and not is_active:
                # Check if course is currently in progress with enrolled students
                if (
                    self.instance.status == Course.STATUS_IN_PROGRESS
                    and self.instance.enrolled_count > 0
                ):
                    raise serializers.ValidationError(
                        {
                            'is_active': (
                                'Cannot disable a course that is in progress with enrolled students.'
                            )
                        }
                    )
        return attrs

    def update(self, instance, validated_data):
        """Update course with categories"""
        category_ids = validated_data.pop('category_ids', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if category_ids is not None:
            instance.categories.set(category_ids)

        return instance

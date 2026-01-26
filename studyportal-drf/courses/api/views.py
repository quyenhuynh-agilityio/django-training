"""
Course ViewSets

This module provides ViewSet for Course CRUD operations with proper
query optimization, permissions, and custom actions.

Architecture:
- Implements action-based serializer/permission selection
- Optimizes queries with annotations for computed fields
- Supports role-based filtering (anonymous, authenticated, instructor)
"""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)

from django.conf import settings
from django.core.cache import cache
from django.db.models import BooleanField, Case, Count, F, Q, Value, When
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.api_views import CommonViewSet
from core.permissions import IsCourseInstructor, IsInstructor
from core.texts import ErrorMessage, SuccessMessage
from courses.models import Course
from enrollments.models import Enrollment
from utils.permissions import permissions_for_action

from .filters import CourseFilter
from .serializers import (
    CourseDeleteResponseSerializer,
    CourseDetailSerializer,
    CourseListSerializer,
    CourseWriteSerializer,
    EnrolledStudentSerializer,
    EnrolledStudentsResponseSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary='List all courses',
        description="""
        Get a paginated list of courses with advanced filtering and search.

        **Access Control:**
        - **Anonymous users:** See only active courses
        - **Authenticated users:** See all active courses
        - **Instructors:** Can filter to show only their courses with `?my_courses=true`

        **Search Capabilities:**
        Search across multiple fields simultaneously:
        - Course title (e.g., "Introduction to Python")
        - Course code (e.g., "CS101")
        - Description text

        **Filtering Options:**

        **By Category:**
        - `?category=uuid` - Filter courses by category

        **By Status:**
        - `?status=draft` - Courses in draft state
        - `?status=active` - Open for enrollment
        - `?status=in_progress` - Currently running
        - `?status=completed` - Finished courses

        **By Ownership (Instructors only):**
        - `?my_courses=true` - Show only courses you created

        **Sorting:**
        - `?ordering=title` - Alphabetical by title
        - `?ordering=-created_at` - Newest first (default)
        - `?ordering=enrolled_count` - By enrollment numbers

        **Computed Fields in Response:**
        - `enrolled_count`: Current number of enrolled students
        - `is_full`: Whether course is at maximum capacity
        - `can_enroll`: Whether new students can enroll

        **Example Queries:**
        - `/courses/?search=python` - Find Python courses
        - `/courses/?category=uuid&status=active` - Active courses in category
        - `/courses/?my_courses=true&ordering=-created_at` - My newest courses
        """,
        parameters=[
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='Filter by category UUID',
                required=False,
            ),
            OpenApiParameter(
                name='status',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by course status',
                required=False,
                enum=['draft', 'active', 'in_progress', 'completed'],
                examples=[
                    OpenApiExample(name='Active Courses', value='active'),
                    OpenApiExample(name='In Progress', value='in_progress'),
                ],
            ),
            OpenApiParameter(
                name='search',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Search in title, course code, or description',
                required=False,
                examples=[
                    OpenApiExample(name='Search Python', value='python'),
                    OpenApiExample(name='Search Code', value='CS101'),
                ],
            ),
            OpenApiParameter(
                name='my_courses',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='(Instructors only) Show only courses you created',
                required=False,
            ),
            OpenApiParameter(
                name='ordering',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Sort by field (prefix with - for descending)',
                required=False,
                examples=[
                    OpenApiExample(name='Newest First', value='-created_at'),
                    OpenApiExample(name='Alphabetical', value='title'),
                    OpenApiExample(name='Most Popular', value='-enrolled_count'),
                ],
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=CourseListSerializer(many=True),
                description='List of courses retrieved successfully',
                examples=[
                    OpenApiExample(
                        name='Course List',
                        value={
                            'count': 50,
                            'next': 'http://api.example.com/courses/?page=2',
                            'previous': None,
                            'results': [
                                {
                                    'id': '123e4567-e89b-12d3-a456-426614174000',
                                    'title': 'Introduction to Python Programming',
                                    'course_code': 'CS101',
                                    'description': 'Learn Python from scratch',
                                    'status': 'active',
                                    'instructor': {
                                        'id': '223e4567-e89b-12d3-a456-426614174001',
                                        'full_name': 'Dr. Jane Smith',
                                    },
                                    'enrolled_count': 45,
                                    'max_students': 50,
                                    'is_full': False,
                                    'can_enroll': True,
                                    'created_at': '2024-01-15T10:30:00Z',
                                }
                            ],
                        },
                    )
                ],
            ),
        },
        tags=['Courses'],
    ),
    retrieve=extend_schema(
        summary='Get course details',
        description="""
        Retrieve comprehensive information about a specific course.

        **Response Includes:**
        - Complete course information (title, code, description)
        - Instructor details (name, email, bio)
        - Course categories
        - Enrollment statistics (current count, maximum capacity)
        - Enrollment availability status
        - Media URLs (thumbnail, cover image)
        - Timestamps (created, updated)

        **Computed Fields:**
        - `enrolled_count`: Number of students currently enrolled
        - `is_full`: Boolean indicating if course is at capacity
        - `can_enroll`: Boolean indicating if new enrollments are accepted

        **Access:**
        - Public endpoint (no authentication required)
        - Shows only active courses to anonymous users

        **Use Cases:**
        - Display course details page
        - Check enrollment availability before enrolling
        - Show instructor information
        - Display course media and description
        """,
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Course UUID',
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=CourseDetailSerializer,
                description='Course details retrieved successfully',
                examples=[
                    OpenApiExample(
                        name='Course Detail',
                        value={
                            'id': '123e4567-e89b-12d3-a456-426614174000',
                            'title': 'Introduction to Python Programming',
                            'course_code': 'CS101',
                            'description': 'A comprehensive introduction to Python programming...',
                            'status': 'active',
                            'instructor': {
                                'id': '223e4567-e89b-12d3-a456-426614174001',
                                'full_name': 'Dr. Jane Smith',
                                'email': 'jane.smith@example.com',
                                'bio': 'PhD in Computer Science with 10 years teaching experience',
                            },
                            'categories': [
                                {
                                    'id': '323e4567-e89b-12d3-a456-426614174002',
                                    'name': 'Programming',
                                },
                                {'id': '423e4567-e89b-12d3-a456-426614174003', 'name': 'Python'},
                            ],
                            'enrolled_count': 45,
                            'max_students': 50,
                            'is_full': False,
                            'can_enroll': True,
                            'thumbnail_url': 'https://example.com/thumbnails/cs101.jpg',
                            'created_at': '2024-01-15T10:30:00Z',
                            'updated_at': '2024-01-20T14:22:00Z',
                        },
                    )
                ],
            ),
            404: OpenApiResponse(
                description='Course not found or inactive',
                examples=[OpenApiExample(name='Not Found', value={'detail': 'Not found.'})],
            ),
        },
        tags=['Courses'],
    ),
    create=extend_schema(
        summary='Create a new course',
        description="""
        Create a new course as an authenticated instructor.

        **Who Can Create:**
        - Only authenticated users with instructor role
        - The instructor field is automatically set to the authenticated user

        **Required Fields:**
        - `title`: Course title (max 200 characters)
        - `course_code`: Unique course code (e.g., "CS101")
        - `description`: Detailed course description

        **Optional Fields:**
        - `status`: Course status (default: "draft")
        - `max_students`: Maximum enrollment capacity (null = unlimited)
        - `categories`: Array of category UUIDs
        - `thumbnail`: Course thumbnail image
        - `start_date`: Course start date
        - `end_date`: Course end date

        **Course Status Options:**
        - `draft`: Not visible to students, still editing
        - `active`: Open for enrollment
        - `in_progress`: Currently running
        - `completed`: Course finished

        **Validation:**
        - Course code must be unique
        - Title cannot be empty
        - Instructor must have instructor role
        - If max_students is set, must be positive number
        - End date must be after start date (if both provided)

        **After Creation:**
        - Course is created with specified or default status
        - You are set as the instructor
        - Course appears in your courses list
        - If status is "active", students can enroll
        """,
        request=CourseWriteSerializer,
        responses={
            201: OpenApiResponse(
                response=CourseDetailSerializer,
                description='Course created successfully',
                examples=[
                    OpenApiExample(
                        name='Created Course',
                        value={
                            'id': '123e4567-e89b-12d3-a456-426614174000',
                            'title': 'Advanced Web Development',
                            'course_code': 'WEB301',
                            'description': 'Master modern web development...',
                            'status': 'draft',
                            'instructor': {
                                'id': '223e4567-e89b-12d3-a456-426614174001',
                                'full_name': 'Dr. Jane Smith',
                            },
                            'max_students': 30,
                            'enrolled_count': 0,
                            'is_full': False,
                            'can_enroll': False,
                            'created_at': '2024-01-25T15:30:00Z',
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description='Bad Request - Validation errors',
                examples=[
                    OpenApiExample(
                        name='Duplicate Course Code',
                        value={'course_code': ['Course with this code already exists.']},
                    ),
                    OpenApiExample(
                        name='Missing Required Fields',
                        value={
                            'title': ['This field is required.'],
                            'course_code': ['This field is required.'],
                        },
                    ),
                ],
            ),
            403: OpenApiResponse(
                description='Forbidden - Only instructors can create courses',
                examples=[
                    OpenApiExample(
                        name='Not an Instructor',
                        value={'detail': 'You must be an instructor to create courses.'},
                    )
                ],
            ),
        },
        tags=['Courses'],
    ),
    update=extend_schema(
        summary='Update course (full update)',
        description="""
        Update all fields of a course you own.

        **Who Can Update:**
        - Course instructor (owner)
        - Staff/admin users

        **Update Type:**
        This is a full update (PUT) - all fields must be provided.
        For partial updates, use PATCH instead.

        **Updatable Fields:**
        - `title`: Course title
        - `description`: Course description
        - `status`: Course status
        - `max_students`: Maximum enrollment capacity
        - `categories`: Course categories
        - `thumbnail`: Course image
        - `start_date` & `end_date`: Course schedule

        **Read-Only Fields:**
        - `id`: Cannot be changed
        - `course_code`: Cannot be changed after creation
        - `instructor`: Cannot be reassigned
        - `enrolled_count`: Computed field
        - `created_at`: Historical timestamp

        **Important Notes:**
        - Changing status to "active" opens enrollment
        - Changing status from "active" closes enrollment
        - Cannot reduce max_students below current enrolled_count
        - End date must be after start date

        **Validation:**
        - All required fields must be present
        - Course code cannot be changed
        - Instructor cannot be changed
        """,
        request=CourseWriteSerializer,
        responses={
            200: OpenApiResponse(
                response=CourseDetailSerializer,
                description='Course updated successfully',
            ),
            400: OpenApiResponse(
                description='Bad Request - Validation errors',
                examples=[
                    OpenApiExample(
                        name='Invalid Status', value={'status': ['Invalid status value.']}
                    ),
                ],
            ),
            403: OpenApiResponse(
                description='Forbidden - Only course owner can update',
                examples=[
                    OpenApiExample(
                        name='Not Course Owner',
                        value={'detail': 'You do not have permission to edit this course.'},
                    )
                ],
            ),
        },
        tags=['Courses'],
    ),
    partial_update=extend_schema(
        summary='Update course (partial update)',
        description="""
        Update specific fields of a course you own.

        **Who Can Update:**
        - Course instructor (owner)
        - Staff/admin users

        **Update Type:**
        This is a partial update (PATCH) - only provide fields you want to change.
        Other fields will remain unchanged.

        **Updatable Fields:**
        - `title`: Course title
        - `description`: Course description
        - `status`: Course status
        - `max_students`: Maximum enrollment capacity
        - `categories`: Course categories
        - `thumbnail`: Course image
        - `start_date` & `end_date`: Course schedule

        **Read-Only Fields:**
        - `id`: Cannot be changed
        - `course_code`: Cannot be changed after creation
        - `instructor`: Cannot be reassigned
        - `enrolled_count`: Computed field

        **Common Update Scenarios:**

        **Publish a draft course:**
        ```json
        {"status": "active"}
        ```

        **Update enrollment limit:**
        ```json
        {"max_students": 100}
        ```

        **Update title and description:**
        ```json
        {
            "title": "Updated Course Title",
            "description": "New detailed description..."
        }
        ```

        **Important Notes:**
        - Only send fields you want to update
        - Cannot reduce max_students below current enrollments
        - Changing status affects enrollment availability
        """,
        request=CourseWriteSerializer,
        responses={
            200: OpenApiResponse(
                response=CourseDetailSerializer,
                description='Course updated successfully',
            ),
            400: OpenApiResponse(
                description='Bad Request - Validation errors',
            ),
            403: OpenApiResponse(
                description='Forbidden - Only course owner can update',
            ),
        },
        tags=['Courses'],
    ),
)
class CourseViewSet(CommonViewSet, viewsets.ModelViewSet):
    """
    Course ViewSet - Full CRUD operations with custom actions

    Comprehensive course management API with role-based access control,
    advanced filtering, and enrollment tracking.

    **Available Operations:**
    - **Public Access:** Browse and search courses (list, retrieve)
    - **Instructor Access:** Create and manage their courses
    - **Owner Access:** Full control over owned courses

    **Key Features:**
    - Smart query optimization with computed fields
    - Enrollment tracking (count, capacity, availability)
    - Role-based queryset filtering
    - Soft delete (preserves data)
    - Advanced search and filtering

    **Computed Fields:**
    - `enrolled_count`: Number of active enrollments
    - `is_full`: Whether course is at capacity
    - `can_enroll`: Whether new enrollments are accepted

    **Permissions by Action:**
    - List/Retrieve: Anyone (public)
    - Create: Authenticated instructors only
    - Update/Delete: Course owner or staff
    - Enrolled Students: Course instructor only

    **Filtering Options:**
    - By category (UUID)
    - By status (draft, active, in_progress, completed)
    - By instructor (my_courses=true for instructors)
    - Full-text search in title, code, description
    - Sort by various fields
    """

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CourseFilter
    search_fields = ['title', 'course_code', 'description']
    ordering_fields = ['title', 'created_at', 'enrolled_count']
    ordering = ['-created_at']
    lookup_field = 'pk'

    # ═══════════════════════════════════════════════════════════════════════════
    #   P E R M I S S I O N S  &  S E R I A L I Z E R S
    # ═══════════════════════════════════════════════════════════════════════════

    permission_classes = [AllowAny]

    permission_classes_map = {
        'list': [AllowAny],
        'retrieve': [AllowAny],
        'create': [IsInstructor],
        'update': [IsCourseInstructor],
        'partial_update': [IsCourseInstructor],
        'destroy': [IsCourseInstructor],
        'enrolled_students': [IsCourseInstructor],
    }

    def get_permissions(self):
        """Get permissions based on action"""
        return permissions_for_action(
            action=self.action,
            permission_classes_map=self.permission_classes_map,
            default_permissions=self.permission_classes,
        )

    def get_serializer_class(self):
        """Return serializer based on action"""
        return {
            'list': CourseListSerializer,
            'retrieve': CourseDetailSerializer,
            'create': CourseWriteSerializer,
            'update': CourseWriteSerializer,
            'partial_update': CourseWriteSerializer,
            'enrolled_students': EnrolledStudentSerializer,
        }.get(self.action, CourseWriteSerializer)

    # ═══════════════════════════════════════════════════════════════════════════
    #   Q U E R Y S E T
    # ═══════════════════════════════════════════════════════════════════════════

    def get_queryset(self):
        """Get optimized queryset with computed fields and role-based filtering"""
        queryset = Course.objects.select_related('instructor').prefetch_related('categories')
        queryset = self._add_computed_fields(queryset)
        queryset = self._apply_role_based_filtering(queryset)
        return queryset.distinct()

    def _add_computed_fields(self, queryset):
        """Add computed annotations for list/retrieve"""
        if self.action not in ['list', 'retrieve', 'enrolled_students']:
            return queryset

        return queryset.annotate(
            # Count active enrollments
            enrolled_count_computed=Count(
                'enrollments', filter=Q(enrollments__is_active=True), distinct=True
            ),
            # Check if course is full
            is_full_computed=Case(
                When(
                    max_students__isnull=False,
                    enrolled_count_computed__gte=F('max_students'),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
            # Check if enrollment is allowed
            can_enroll_computed=Case(
                When(
                    Q(is_active=True, status=Course.STATUS_ACTIVE)
                    & (
                        Q(max_students__isnull=True)
                        | Q(enrolled_count_computed__lt=F('max_students'))
                    ),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )

    def _apply_role_based_filtering(self, queryset):
        """
        Apply access control based on user role.

        Access Rules:
            - Anonymous: Only active courses
            - Authenticated: All active courses
            - Instructor + ?my_courses=true: Only own courses
        """
        user = self.request.user

        if not user.is_authenticated:
            return queryset.filter(is_active=True)

        queryset = queryset.filter(is_active=True)

        if (
            getattr(user, 'is_instructor', False)
            and self.request.query_params.get('my_courses') == 'true'
        ):
            queryset = queryset.filter(instructor=user)

        return queryset

    # ═══════════════════════════════════════════════════════════════════════════
    #   C R U D  O P E R A T I O N S  (WITH RESPONSE VALIDATION)
    # ═══════════════════════════════════════════════════════════════════════════

    def list(self, request, *args, **kwargs):  # noqa: D401
        """List courses with optional caching for public queries."""
        # Do not cache instructor-specific "my courses" view
        if (
            request.user.is_authenticated
            and getattr(request.user, 'is_instructor', False)
            and request.query_params.get('my_courses') == 'true'
        ):
            return super().list(request, *args, **kwargs)

        # Build cache key from query parameters that affect the queryset
        relevant_params = ['page', 'search', 'status', 'category', 'ordering']
        key_parts = [f"{name}={request.query_params.get(name, '')}" for name in relevant_params]
        cache_key = 'courses:list:' + ':'.join(key_parts)

        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)

        # Cache successful responses only
        if response.status_code == 200:
            timeout = getattr(settings, 'COURSE_LIST_CACHE_TIMEOUT', 60)
            cache.set(cache_key, response.data, timeout)

        return response

    def perform_create(self, serializer):
        """
        Create course and set instructor from request user

        Note:
            The serializer will call model's save() which triggers full_clean()
            for additional validation (e.g., instructor role check).
        """
        serializer.save(instructor=self.request.user)

    @extend_schema(
        summary='Delete a course (soft delete)',
        description="""
        Mark a course as inactive (soft delete).

        **Who Can Delete:**
        - Course instructor (owner)
        - Staff/admin users

        **What Happens:**
        - Course is marked as inactive (`is_active=False`)
        - Course disappears from public listings
        - Data is preserved in the database
        - Historical enrollment records are maintained

        **Deletion Rules:**
        You **cannot delete** a course if:
        - Course status is "in_progress" AND
        - There are students currently enrolled
        - Course is already deleted

        This prevents disruption to ongoing courses with active students.

        **Allowed Deletion Scenarios:**
        - Draft courses (any time)
        - Active courses with no enrollments
        - Completed courses
        - Courses with status changed to something other than "in_progress"

        **After Deletion:**
        - Students lose access to course materials
        - Course won't appear in search results
        - Instructor can still access through admin if needed
        - Course can potentially be reactivated by admin

        **Alternative:**
        Instead of deleting, consider changing status to "completed" or "draft"
        to preserve access for enrolled students.
        """,
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Course UUID to delete',
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description='Course deleted successfully',
                examples=[
                    OpenApiExample(
                        name='Delete Success',
                        value={
                            'message': 'Course deleted successfully.',
                            'course_id': '123e4567-e89b-12d3-a456-426614174000',
                            'course_code': 'CS101',
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description='Bad Request - Cannot delete course',
                examples=[
                    OpenApiExample(
                        name='Course In Progress',
                        value={
                            'message': 'Cannot delete a course that is in progress with enrolled students.',
                            'code': 'COURSE_IN_PROGRESS_WITH_STUDENTS',
                        },
                    ),
                    OpenApiExample(
                        name='Already Deleted',
                        value={
                            'message': 'Course is already deleted.',
                            'code': 'COURSE_ALREADY_DELETED',
                        },
                    ),
                ],
            ),
            403: OpenApiResponse(
                description='Forbidden - Only course owner can delete',
                examples=[
                    OpenApiExample(
                        name='Not Course Owner',
                        value={'detail': 'You do not have permission to delete this course.'},
                    )
                ],
            ),
        },
        tags=['Courses'],
    )
    def destroy(self, request, *args, **kwargs):
        """
        Soft delete a course

        Business Rules:
            - Cannot delete courses in progress with enrolled students
            - Cannot delete a course that is already deleted

        Returns:
            200 OK: Course deleted successfully (with validated response)
            400 Bad Request: Business rule violation
        """
        course = self.get_object()

        # Check if already deleted
        if not course.is_active:
            return self.bad_request(
                message='Course is already deleted.',
                code='COURSE_ALREADY_DELETED',
            )

        # Check if course can be deleted
        enrolled = getattr(
            course,
            'enrolled_count_computed',
            course.enrollments.filter(is_active=True).count(),
        )

        if course.status == Course.STATUS_IN_PROGRESS and enrolled > 0:
            return self.bad_request(
                message=ErrorMessage.CANNOT_DELETE_IN_PROGRESS_WITH_STUDENTS,
                code='COURSE_IN_PROGRESS_WITH_STUDENTS',
            )

        # Perform soft delete
        course.soft_delete()

        # Prepare response data
        response_data = {
            'message': SuccessMessage.COURSE_DELETED_SUCCESSFULLY,
            'course_id': str(course.id),
            'course_code': course.course_code,
        }

        # Validate response structure
        response_serializer = CourseDeleteResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        return self.ok(response_serializer.data)

    # ═══════════════════════════════════════════════════════════════════════════
    #   C U S T O M   A C T I O N S
    # ═══════════════════════════════════════════════════════════════════════════

    @extend_schema(
        summary='Get enrolled students',
        description="""
        View all students enrolled in your course.

        **Who Can Access:**
        - Only the course instructor (owner)
        - Staff/admin users

        **Response Includes:**
        For each enrollment:
        - Student information (name, email)
        - Enrollment status (active, completed, dropped)
        - Enrollment date
        - Student progress/activity (if implemented)

        **Pagination:**
        - Results are paginated for large enrollments
        - Default page size is determined by system settings
        - Use `?page=2` to navigate pages

        **Ordering:**
        - Students ordered by enrollment date (newest first)
        - Most recently enrolled students appear at top

        **Use Cases:**
        - View course roster
        - Track enrollment numbers
        - Export student list
        - Monitor course participation
        - Send announcements to enrolled students

        **Filtering:**
        Only active enrollments are shown by default.
        Dropped or inactive enrollments are excluded.
        """,
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Course UUID',
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=EnrolledStudentsResponseSerializer,
                description='List of enrolled students retrieved successfully',
                examples=[
                    OpenApiExample(
                        name='Enrolled Students',
                        value={
                            'count': 45,
                            'next': None,
                            'previous': None,
                            'results': [
                                {
                                    'id': '123e4567-e89b-12d3-a456-426614174000',
                                    'student': {
                                        'id': '223e4567-e89b-12d3-a456-426614174001',
                                        'email': 'john.doe@example.com',
                                        'full_name': 'John Doe',
                                        'username': 'johndoe',
                                    },
                                    'status': 'active',
                                    'enrolled_at': '2024-01-15T10:30:00Z',
                                },
                                {
                                    'id': '323e4567-e89b-12d3-a456-426614174002',
                                    'student': {
                                        'id': '423e4567-e89b-12d3-a456-426614174003',
                                        'email': 'jane.smith@example.com',
                                        'full_name': 'Jane Smith',
                                        'username': 'janesmith',
                                    },
                                    'status': 'active',
                                    'enrolled_at': '2024-01-16T14:20:00Z',
                                },
                            ],
                        },
                    )
                ],
            ),
            403: OpenApiResponse(
                description='Forbidden - Only course instructor can view',
                examples=[
                    OpenApiExample(
                        name='Not Course Instructor',
                        value={'detail': 'Only the course instructor can view enrolled students.'},
                    )
                ],
            ),
            404: OpenApiResponse(
                description='Course not found',
                examples=[OpenApiExample(name='Not Found', value={'detail': 'Not found.'})],
            ),
        },
        tags=['Courses'],
    )
    @action(
        detail=True,
        methods=['get'],
        url_path='enrolled-students',
        url_name='enrolled-students',
    )
    def enrolled_students(self, request, pk=None):
        """
        Get enrolled students for a course

        Access Control:
            - Only the course instructor can view enrolled students
            - Returns 403 if user is not the course instructor

        Response:
            Paginated list of enrollments with student details (validated)
        """
        course = self.get_object()

        enrollments = (
            Enrollment.objects.filter(course=course, is_active=True)
            .select_related('student')
            .order_by('-created_at')
        )

        # Apply pagination
        page = self.paginate_queryset(enrollments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)

            # Validate response structure
            response_serializer = EnrolledStudentsResponseSerializer(data=paginated_response.data)
            response_serializer.is_valid(raise_exception=True)

            return paginated_response

        # Non-paginated response (fallback)
        serializer = self.get_serializer(enrollments, many=True)
        response_data = {'results': serializer.data}

        return self.ok(response_data)


__all__ = ['CourseViewSet']

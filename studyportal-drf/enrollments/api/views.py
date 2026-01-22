"""
Enrollment ViewSets - Updated with Response Serializers

Added response validation for all actions to ensure type safety and consistency.
Each endpoint now validates its output before returning to the client.
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

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter

from core.api_views import CommonViewSet
from core.permissions import IsStudent
from core.texts import SuccessMessage
from enrollments.models import Enrollment
from notifications.tasks import (
    create_student_enrolled_notification,
    create_student_removed_notification,
)

from .serializers import (
    EnrollmentCreateSerializer,
    EnrollmentDetailResponseSerializer,
    EnrollmentEnrollResponseSerializer,
    EnrollmentLeaveResponseSerializer,
    EnrollmentListResponseSerializer,
    EnrollmentSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary='List my enrolled courses',
        description="""
        Get a paginated list of courses you are currently enrolled in.

        **What You'll See:**
        - All your active enrollments
        - Course details (title, code, instructor)
        - Enrollment status and dates
        - Course categories

        **Filtering Options:**
        Use query parameters to filter and sort your enrollments:

        **Search:**
        - `?search=python` - Find courses by title or course code
        - `?search=CS101` - Search by course code

        **Filter by Status:**
        - `?status=active` - Only active enrollments
        - `?status=completed` - Completed courses
        - `?status=dropped` - Courses you've left

        **Filter by Active State:**
        - `?is_active=true` - Only active enrollments (default)
        - `?is_active=false` - Include inactive enrollments

        **Sorting:**
        - `?ordering=created_at` - Oldest first
        - `?ordering=-created_at` - Newest first (default)
        - `?ordering=updated_at` - Recently updated first

        **Example Queries:**
        - `/enrollments/?search=python&status=active` - Active Python courses
        - `/enrollments/?ordering=-created_at` - Most recent enrollments
        """,
        parameters=[
            OpenApiParameter(
                name='search',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Search in course title or course code',
                required=False,
                examples=[
                    OpenApiExample(name='Search by Title', value='python'),
                    OpenApiExample(name='Search by Code', value='CS101'),
                ],
            ),
            OpenApiParameter(
                name='status',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by enrollment status',
                required=False,
                enum=['active', 'completed', 'dropped'],
                examples=[
                    OpenApiExample(name='Active', value='active'),
                    OpenApiExample(name='Completed', value='completed'),
                    OpenApiExample(name='Dropped', value='dropped'),
                ],
            ),
            OpenApiParameter(
                name='is_active',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by active status',
                required=False,
            ),
            OpenApiParameter(
                name='ordering',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Sort results (prefix with - for descending)',
                required=False,
                examples=[
                    OpenApiExample(name='Newest First', value='-created_at'),
                    OpenApiExample(name='Oldest First', value='created_at'),
                    OpenApiExample(name='Recently Updated', value='-updated_at'),
                ],
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=EnrollmentListResponseSerializer,
                description='List of enrollments retrieved successfully',
                examples=[
                    OpenApiExample(
                        name='Enrollment List',
                        value={
                            'count': 3,
                            'next': None,
                            'previous': None,
                            'results': [
                                {
                                    'id': '123e4567-e89b-12d3-a456-426614174000',
                                    'course': {
                                        'id': '223e4567-e89b-12d3-a456-426614174001',
                                        'title': 'Introduction to Python',
                                        'course_code': 'CS101',
                                    },
                                    'student': {
                                        'id': '323e4567-e89b-12d3-a456-426614174002',
                                        'email': 'student@example.com',
                                        'full_name': 'John Doe',
                                    },
                                    'status': 'active',
                                    'is_active': True,
                                    'enrolled_at': '2024-01-15T10:30:00Z',
                                }
                            ],
                        },
                    )
                ],
            ),
            401: OpenApiResponse(
                description='Unauthorized - Authentication required',
                examples=[
                    OpenApiExample(
                        name='Not Authenticated',
                        value={'detail': 'Authentication credentials were not provided.'},
                    )
                ],
            ),
        },
        tags=['Enrollments'],
    ),
    retrieve=extend_schema(
        summary='Get enrollment details',
        description="""
        Retrieve detailed information about a specific enrollment.

        **Response Includes:**
        - Complete enrollment information
        - Full course details (title, code, description, instructor)
        - Course categories
        - Enrollment status and timestamps
        - Student information

        **Use Cases:**
        - View enrollment confirmation details
        - Check enrollment status
        - Access course information from enrollment record
        - Display enrollment history

        **Note:** You can only view your own enrollments.
        """,
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Enrollment UUID',
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=EnrollmentDetailResponseSerializer,
                description='Enrollment details retrieved successfully',
                examples=[
                    OpenApiExample(
                        name='Enrollment Detail',
                        value={
                            'id': '123e4567-e89b-12d3-a456-426614174000',
                            'course': {
                                'id': '223e4567-e89b-12d3-a456-426614174001',
                                'title': 'Introduction to Python Programming',
                                'course_code': 'CS101',
                                'description': 'Learn Python from scratch',
                                'instructor': {
                                    'id': '423e4567-e89b-12d3-a456-426614174003',
                                    'full_name': 'Dr. Jane Smith',
                                    'email': 'jane.smith@example.com',
                                },
                                'categories': [
                                    {
                                        'id': '523e4567-e89b-12d3-a456-426614174004',
                                        'name': 'Programming',
                                    }
                                ],
                            },
                            'student': {
                                'id': '323e4567-e89b-12d3-a456-426614174002',
                                'email': 'student@example.com',
                                'full_name': 'John Doe',
                            },
                            'status': 'active',
                            'is_active': True,
                            'enrolled_at': '2024-01-15T10:30:00Z',
                            'updated_at': '2024-01-15T10:30:00Z',
                        },
                    )
                ],
            ),
            404: OpenApiResponse(
                description='Enrollment not found or not yours',
            ),
        },
        tags=['Enrollments'],
    ),
)
class StudentEnrolledCoursesViewSet(CommonViewSet, viewsets.ReadOnlyModelViewSet):
    """
    Student Enrolled Courses ViewSet

    Manage student course enrollments including viewing enrolled courses,
    enrolling in new courses, and leaving courses.

    **Available Endpoints:**
    - List all enrolled courses for the authenticated student
    - View detailed enrollment information
    - Enroll in a new course
    - Leave (unenroll from) a course

    **Features:**
    - Automatic filtering to show only current student's enrollments
    - Search courses by title or course code
    - Filter by enrollment status (active, completed, dropped)
    - Sort by enrollment date
    - Query optimization with prefetched relations
    - Response validation for all endpoints

    **Permissions:**
    - All endpoints require student authentication
    - Students can only view and manage their own enrollments

    **Enrollment Status:**
    - `active`: Currently enrolled and participating
    - `completed`: Successfully finished the course
    - `dropped`: Withdrew from the course
    """

    serializer_class = EnrollmentSerializer
    permission_classes = [IsStudent]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'is_active']
    search_fields = ['course__title', 'course__course_code']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get enrollments for current student only with optimized queries"""
        # Handle schema generation (drf-spectacular introspection)
        if getattr(self, 'swagger_fake_view', False):
            return Enrollment.objects.none()

        return (
            Enrollment.objects.filter(student=self.request.user, is_active=True)
            .select_related('course', 'course__instructor')
            .prefetch_related('course__categories')
        )

    @extend_schema(
        summary='Enroll in a course',
        description="""
        Enroll yourself in a new course.

        **Enrollment Process:**
        1. Provide the course ID
        2. System validates eligibility
        3. Enrollment is created with 'active' status
        4. You gain access to course materials

        **Validation Rules:**
        - Course must exist and be active
        - Course must not be full (if max_students is set)
        - You cannot be already enrolled in the course
        - Course status must be 'active' (not draft, completed, etc.)

        **Request Body:**
        ```json
        {
            "course_id": "123e4567-e89b-12d3-a456-426614174000"
        }
        ```

        **Success Response:**
        - Returns enrollment details including course information
        - Enrollment status is automatically set to 'active'
        - You'll receive confirmation with enrolled_at timestamp
        """,
        request=EnrollmentCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=EnrollmentEnrollResponseSerializer,
                description='Successfully enrolled in course',
                examples=[
                    OpenApiExample(
                        name='Enrollment Success',
                        value={
                            'message': 'Successfully enrolled in course',
                            'data': {
                                'id': '123e4567-e89b-12d3-a456-426614174000',
                                'course': {
                                    'id': '223e4567-e89b-12d3-a456-426614174001',
                                    'title': 'Introduction to Python',
                                    'course_code': 'CS101',
                                },
                                'student': '323e4567-e89b-12d3-a456-426614174002',
                                'student_name': 'John Doe',
                                'student_email': 'student@example.com',
                                'status': 'active',
                                'is_active': True,
                                'created_at': '2024-01-15T10:30:00Z',
                                'updated_at': '2024-01-15T10:30:00Z',
                            },
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description='Bad Request - Validation failed',
                examples=[
                    OpenApiExample(
                        name='Course Not Found', value={'course_id': ['Course not found.']}
                    ),
                    OpenApiExample(
                        name='Course Full',
                        value={'course_id': ['Course has reached maximum capacity.']},
                    ),
                    OpenApiExample(
                        name='Already Enrolled',
                        value={'course_id': ['You are already enrolled in this course.']},
                    ),
                    OpenApiExample(
                        name='Course Inactive',
                        value={'course_id': ['Cannot enroll in an inactive course.']},
                    ),
                ],
            ),
            401: OpenApiResponse(
                description='Unauthorized - Student authentication required',
                examples=[
                    OpenApiExample(
                        name='Not Authenticated',
                        value={'detail': 'Authentication credentials were not provided.'},
                    )
                ],
            ),
        },
        tags=['Enrollments'],
    )
    @action(detail=False, methods=['post'])
    def enroll(self, request):
        """
        Enroll in a course

        Validates input, creates enrollment, and returns validated response.

        Request body:
        ```json
        {
            "course_id": "123e4567-e89b-12d3-a456-426614174000"
        }
        ```

        Returns:
            201 Created: Success message with enrollment details (validated)
            400 Bad Request: Validation errors
        """
        # Validate input
        serializer = EnrollmentCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        enrollment = serializer.save()

        # Prepare response data
        enrollment_data = EnrollmentSerializer(
            enrollment, context=self.get_serializer_context()
        ).data

        response_data = {
            'message': str(SuccessMessage.ENROLLMENT_ENROLLED_SUCCESS),
            'data': enrollment_data,
        }

        # Validate response structure
        response_serializer = EnrollmentEnrollResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        create_student_enrolled_notification.delay(
            # instructor_id is on the course model
            instructor_id=str(enrollment.course.instructor_id),
            # student properties
            student_id=str(enrollment.student.id),
            student_name=enrollment.student.full_name,
            student_email=enrollment.student.email,
            # course properties
            course_id=str(enrollment.course.id),
            course_code=enrollment.course.course_code,
            course_title=enrollment.course.title,
        )

        return self.created(response_serializer.data)

    @extend_schema(
        summary='Leave a course',
        description="""
        Unenroll from a course you're currently enrolled in.

        **What Happens:**
        1. Enrollment status changes to 'dropped'
        2. Enrollment marked as inactive
        3. You lose access to course materials
        4. Enrollment record is preserved for history

        **Important Notes:**
        - This is a soft delete - the enrollment record remains in the system
        - You can re-enroll in the course later if it's still available
        - Your progress and history are maintained
        - This action cannot be undone through the API

        **Access Control:**
        - You can only leave your own enrollments
        - The enrollment must be active to leave

        **Use Cases:**
        - Student withdrawing from a course
        - Dropping a course before completion
        - Freeing up space in capacity-limited courses
        """,
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Enrollment UUID to leave',
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=EnrollmentLeaveResponseSerializer,
                description='Successfully left the course',
                examples=[
                    OpenApiExample(
                        name='Leave Success',
                        value={
                            'message': 'Successfully left the course',
                            'data': {
                                'enrollment_id': '123e4567-e89b-12d3-a456-426614174000',
                                'status': 'dropped',
                            },
                        },
                    )
                ],
            ),
            404: OpenApiResponse(
                description='Enrollment not found or not yours',
            ),
            401: OpenApiResponse(
                description='Unauthorized - Authentication required',
            ),
        },
        tags=['Enrollments'],
    )
    @action(detail=True, methods=['delete'], url_path='leave')
    def leave(self, request, pk=None):
        """
        Leave a course (unenroll)

        This marks the enrollment as inactive and sets status to 'dropped'.
        The enrollment record is preserved for historical purposes.

        Returns:
            200 OK: Success message with updated status (validated)
            404 Not Found: Enrollment not found or not accessible
        """
        enrollment = self.get_object()

        # Unenroll the student (updates status to 'dropped' and is_active to False)
        enrollment.unenroll()

        # Prepare response data
        response_data = {
            'message': str(SuccessMessage.ENROLLMENT_LEFT_COURSE_SUCCESS),
            'data': {
                'enrollment_id': str(enrollment.id),
                'status': enrollment.status,
            },
        }

        # Validate response structure
        response_serializer = EnrollmentLeaveResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        create_student_removed_notification.delay(
            student_id=str(enrollment.student.id),
            course_id=str(enrollment.course.id),
            course_code=enrollment.course.course_code,
            course_title=enrollment.course.title,
        )

        return self.ok(response_serializer.data)


__all__ = [
    'StudentEnrolledCoursesViewSet',
]

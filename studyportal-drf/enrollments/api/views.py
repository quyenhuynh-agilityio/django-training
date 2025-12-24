"""
Enrollment ViewSets

ViewSet for student enrollment management with proper DRF patterns.
"""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter

from core.api_views import CommonViewSet
from core.permissions import IsStudent
from core.texts import SuccessMessage
from enrollments.models import Enrollment

from .serializers import EnrollmentCreateSerializer, EnrollmentSerializer


@extend_schema_view(
    list=extend_schema(
        summary='List my enrolled courses',
        description="Get paginated list of courses I'm enrolled in",
        parameters=[
            OpenApiParameter(
                name='search', type=str, description='Search in course title or course code'
            ),
            OpenApiParameter(
                name='status',
                type=str,
                description='Filter by enrollment status (active, completed, dropped)',
            ),
            OpenApiParameter(
                name='is_active', type=OpenApiTypes.BOOL, description='Filter by active status'
            ),
            OpenApiParameter(
                name='ordering',
                type=str,
                description='Order by field (use - for descending, e.g., -created_at)',
            ),
        ],
        tags=['Enrollments'],
    ),
    retrieve=extend_schema(
        summary='Get enrollment detail',
        description='Get detailed information about a specific enrollment',
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Enrollment UUID',
            ),
        ],
        tags=['Enrollments'],
    ),
)
class StudentEnrolledCoursesViewSet(CommonViewSet, viewsets.ReadOnlyModelViewSet):
    """
    Student Enrolled Courses ViewSet

    Endpoints:
    - GET    /api/v1/students/enrollments/           - List my enrollments
    - GET    /api/v1/students/enrollments/{id}/      - Get enrollment detail
    - POST   /api/v1/students/enrollments/enroll/    - Enroll in course
    - DELETE /api/v1/students/enrollments/{id}/leave/ - Leave course

    Filters:
    - ?search=python       - Search in course title/code
    - ?status=active       - Filter by enrollment status
    - ?is_active=true      - Filter by active status
    - ?ordering=-created_at - Sort by creation date

    Permissions: Students only
    """

    serializer_class = EnrollmentSerializer
    permission_classes = [IsStudent]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'is_active']
    search_fields = ['course__title', 'course__course_code']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get enrollments for current student only"""
        # Handle schema generation (drf-spectacular introspection)
        if getattr(self, 'swagger_fake_view', False):
            return Enrollment.objects.none()

        return (
            Enrollment.objects.filter(student=self.request.user, is_active=True)
            .select_related('course', 'course__instructor')
            .prefetch_related('course__categories')
        )

    @extend_schema(
        summary='Enroll in course',
        description='Enroll the authenticated student in a course',
        request=EnrollmentCreateSerializer,
        responses={
            201: EnrollmentSerializer,
            400: {
                'description': 'Validation errors',
                'content': {
                    'application/json': {
                        'examples': {
                            'course_not_found': {
                                'summary': 'Course not found',
                                'value': {'course_id': ['Course not found.']},
                            },
                            'course_full': {
                                'summary': 'Course at capacity',
                                'value': {'course_id': ['Course has reached maximum capacity.']},
                            },
                            'already_enrolled': {
                                'summary': 'Already enrolled',
                                'value': {
                                    'course_id': ['You are already enrolled in this course.']
                                },
                            },
                            'course_inactive': {
                                'summary': 'Course inactive',
                                'value': {'course_id': ['Cannot enroll in an inactive course.']},
                            },
                        }
                    }
                },
            },
        },
        tags=['Enrollments'],
    )
    @action(detail=False, methods=['post'])
    def enroll(self, request):
        """
        Enroll in a course

        Request body:
        ```json
        {
            "course_id": "123e4567-e89b-12d3-a456-426614174000"
        }
        ```
        """
        serializer = EnrollmentCreateSerializer(data=request.data, context={'request': request})

        serializer.is_valid(raise_exception=True)
        serializer.save()  # Creates enrollment, no need to store it

        return self.created(
            {
                'message': SuccessMessage.ENROLLMENT_ENROLLED_SUCCESS,
                'data': serializer.data,
            },
        )

    @extend_schema(
        summary='Leave course',
        description='Unenroll from a specific course (marks enrollment as inactive)',
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Enrollment UUID',
            ),
        ],
        responses={
            200: {
                'description': 'Successfully left course',
                'content': {
                    'application/json': {
                        'example': {
                            'message': 'Successfully left the course',
                            'data': {
                                'enrollment_id': '123e4567-e89b-12d3-a456-426614174000',
                                'status': 'dropped',
                            },
                        }
                    }
                },
            },
            404: {
                'description': 'Enrollment not found',
            },
        },
        tags=['Enrollments'],
    )
    @action(detail=True, methods=['delete'], url_path='leave')
    def leave(self, request, pk=None):
        """
        Leave a course (unenroll)

        This marks the enrollment as inactive and sets status to 'dropped'.
        The enrollment record is preserved for historical purposes.
        """
        enrollment = self.get_object()

        # Unenroll the student
        enrollment.unenroll()

        return self.ok(
            {
                'message': SuccessMessage.ENROLLMENT_LEFT_COURSE_SUCCESS,
                'data': {'enrollment_id': str(enrollment.id), 'status': enrollment.status},
            },
        )


__all__ = [
    'StudentEnrolledCoursesViewSet',
]

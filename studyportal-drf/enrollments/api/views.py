from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema

from rest_framework import generics, serializers, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.views import APIView

from core.api_views import CommonViewSet
from courses.api.permissions import IsStudent
from enrollments.models import Enrollment

from .serializers import EnrollmentCreateSerializer, EnrollmentSerializer


class StudentEnrolledCoursesViewSet(CommonViewSet, viewsets.ReadOnlyModelViewSet):
    """
    Student Enrolled Courses ViewSet

    GET /api/v1/students/enrolled-courses/ - List my enrollments (paginated)
    GET /api/v1/students/enrolled-courses/{id}/ - Get enrollment detail

    Filters:
    - ?search=python - Search in course title
    - ?status=active - Filter by enrollment status

    Permissions: Students only
    Pagination: 10 items per page
    """

    serializer_class = EnrollmentSerializer
    permission_classes = [IsStudent]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'is_active']
    search_fields = ['course__title', 'course__course_code']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get enrollments for current student only"""
        return (
            Enrollment.objects.filter(student=self.request.user, is_active=True)
            .select_related('course', 'course__instructor')
            .prefetch_related('course__categories')
        )

    @extend_schema(
        summary='List my enrolled courses',
        description="Get paginated list of courses I'm enrolled in",
        parameters=[
            OpenApiParameter(name='search', type=str, description='Search in course title'),
            OpenApiParameter(name='status', type=str, description='Filter by enrollment status'),
        ],
        tags=['Enrollments'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Get enrollment detail',
        description='Get detailed information about an enrollment',
        tags=['Enrollments'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class EnrollInCourseView(CommonViewSet, generics.CreateAPIView):
    """
    Enroll in Course API

    POST /api/v1/students/enroll/

    Request body:
    {
        "course_id": "uuid"
    }

    Validations:
    - Course must exist
    - Course must be active (status='active')
    - Course must not be full
    - Student cannot enroll twice

    Permissions: Students only
    """

    serializer_class = EnrollmentCreateSerializer
    permission_classes = [IsStudent]

    @extend_schema(
        summary='Enroll in course',
        description='Enroll in an active course',
        request=EnrollmentCreateSerializer,
        responses={
            201: EnrollmentSerializer,
            400: {
                'description': 'Validation errors',
                'examples': {
                    'course_full': {
                        'value': {'course_id': ['Course has reached maximum capacity.']}
                    },
                    'already_enrolled': {
                        'value': {'course_id': ['You are already enrolled in this course.']}
                    },
                },
            },
        },
        tags=['Enrollments'],
    )
    def post(self, request, *args, **kwargs):
        """Handle POST request for enrollment"""
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            enrollment = serializer.save()

            # Return full enrollment details
            output_serializer = EnrollmentSerializer(enrollment)
            return self.created(
                {
                    'message': 'Successfully enrolled in course',
                    'enrollment': output_serializer.data,
                }
            )

        except serializers.ValidationError as e:
            return self.bad_request(message='Enrollment failed', code=e.detail)


class LeaveCourseView(CommonViewSet, APIView):
    """
    Leave Course API

    DELETE /api/v1/students/leave/{course_id}/

    Unenrolls student from the specified course.
    Sets is_active=False and status='dropped'

    Permissions: Students only
    """

    permission_classes = [IsStudent]

    @extend_schema(
        summary='Leave course',
        description='Unenroll from a course',
        responses={
            200: {'description': 'Successfully left course'},
            404: {'description': 'Enrollment not found'},
        },
        tags=['Enrollments'],
    )
    def delete(self, request, course_id):
        """Handle DELETE request to leave course"""
        try:
            enrollment = Enrollment.objects.get(
                student=request.user, course__id=course_id, is_active=True
            )

            # Unenroll
            enrollment.unenroll()

            return self.ok({'message': 'Successfully left the course'})

        except Enrollment.DoesNotExist:
            return self.not_found()

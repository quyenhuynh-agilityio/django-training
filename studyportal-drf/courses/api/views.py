from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema

from django.db.models import Count, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from courses.models import Course
from enrollments.api.serializers import EnrollmentSerializer
from enrollments.models import Enrollment

from .filters import CourseFilter
from .permissions import IsInstructorOrReadOnly
from .serializers import CourseCreateUpdateSerializer, CourseDetailSerializer, CourseListSerializer


class CourseViewSet(viewsets.ModelViewSet):
    """
    Course ViewSet - Full CRUD operations

    List: GET /api/v1/courses/ - Public (filtered for anonymous)
    Retrieve: GET /api/v1/courses/{id}/ - Public
    Create: POST /api/v1/courses/ - Instructors only
    Update: PUT/PATCH /api/v1/courses/{id}/ - Course instructor only
    Delete: DELETE /api/v1/courses/{id}/ - Course instructor only

    Filters:
    - ?category={uuid} - Filter by category
    - ?status=active - Filter by status
    - ?search=python - Search in title/description
    - ?my_courses=true - Show instructor's own courses

    Pagination: 10 items per page
    """

    permission_classes = [IsInstructorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CourseFilter
    search_fields = ['title', 'course_code', 'description']
    ordering_fields = ['title', 'created_at', 'enrolled_count']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Get queryset based on user role

        Anonymous users: Only active courses with status='active'
        Authenticated users: Active courses
        Instructors: Can see their own courses (with ?my_courses=true)
        """
        queryset = Course.objects.prefetch_related('categories').select_related('instructor')

        # Add enrolled count annotation
        queryset = queryset.annotate(
            total_enrolled=Count('enrollments', filter=Q(enrollments__is_active=True))
        )

        # Anonymous users see only active courses
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_active=True, status='active')
        else:
            # Authenticated users see active courses
            queryset = queryset.filter(is_active=True)

        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(categories__id=category_id)

        # Instructor can filter their own courses
        if self.request.user.is_authenticated and self.request.user.is_instructor():
            if self.request.query_params.get('my_courses') == 'true':
                queryset = queryset.filter(instructor=self.request.user)

        return queryset.distinct()

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return CourseListSerializer
        elif self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseCreateUpdateSerializer

    def perform_create(self, serializer):
        """Set instructor to current user"""
        serializer.save(instructor=self.request.user)

    @extend_schema(
        summary='List courses',
        description='Get paginated list of courses with filtering and search',
        parameters=[
            OpenApiParameter(name='category', type=str, description='Filter by category UUID'),
            OpenApiParameter(name='status', type=str, description='Filter by status'),
            OpenApiParameter(name='search', type=str, description='Search in title/description'),
            OpenApiParameter(
                name='my_courses', type=bool, description='Show only my courses (instructors)'
            ),
        ],
        tags=['Courses'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Get course detail',
        description='Get detailed information about a course',
        tags=['Courses'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary='Create course',
        description='Create a new course (instructors only)',
        tags=['Courses'],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary='Update course',
        description='Update course details (course instructor only)',
        tags=['Courses'],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary='Delete course',
        description='Delete course (course instructor only)',
        tags=['Courses'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated, IsInstructorOrReadOnly],
    )
    def enrolled_students(self, request, pk=None):
        """
        Get enrolled students for a course
        GET /api/v1/courses/{id}/enrolled_students/

        Only accessible by course instructor
        """
        course = self.get_object()

        # Check if user is course instructor
        if course.instructor != request.user:
            return Response(
                {'error': 'Only course instructor can view enrolled students.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        enrollments = Enrollment.objects.filter(course=course, is_active=True).select_related(
            'student'
        )

        # Pagination
        page = self.paginate_queryset(enrollments)
        if page is not None:
            serializer = EnrollmentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

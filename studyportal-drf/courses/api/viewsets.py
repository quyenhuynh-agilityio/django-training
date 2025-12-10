"""
Course ViewSets

This module hosts router-friendly viewsets for course resources, mirroring the
structure used in the accounts app (views + viewsets split). The main
CourseViewSet keeps all Course CRUD plus the custom `enrolled_students` action.
"""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema

from django.db.models import Count, Q
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter

from core.api_views import CommonViewSet
from courses.models import Course
from enrollments.api.serializers import EnrolledStudentSerializer
from enrollments.models import Enrollment

from .filters import CourseFilter
from .permissions import IsInstructorOrReadOnly
from .serializers import (
    CourseCreateUpdateSerializer,
    CourseDetailSerializer,
    CourseListSerializer,
)


class CourseViewSet(CommonViewSet, viewsets.ModelViewSet):
    """
    Course ViewSet - Full CRUD + enrolled students endpoint.

    Routes (via DefaultRouter):
    - GET    /api/v1/courses/                 -> list
    - POST   /api/v1/courses/                 -> create (instructors)
    - GET    /api/v1/courses/{id}/            -> retrieve
    - PUT    /api/v1/courses/{id}/            -> update (instructor owner)
    - PATCH  /api/v1/courses/{id}/            -> partial_update (instructor owner)
    - DELETE /api/v1/courses/{id}/            -> destroy (instructor owner, with checks)
    - GET    /api/v1/courses/{id}/enrolled-students/ -> enrolled_students (instructor owner)
    """

    permission_classes = [IsInstructorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CourseFilter
    search_fields = ['title', 'course_code', 'description']
    ordering_fields = ['title', 'created_at', 'enrolled_count']
    ordering = ['-created_at']

    serializer_action_classes = {
        'list': CourseListSerializer,
        'retrieve': CourseDetailSerializer,
        'create': CourseCreateUpdateSerializer,
        'update': CourseCreateUpdateSerializer,
        'partial_update': CourseCreateUpdateSerializer,
        'enrolled_students': EnrolledStudentSerializer,
    }

    permission_action_classes = {
        'enrolled_students': [permissions.IsAuthenticated, IsInstructorOrReadOnly],
    }

    def get_permissions(self):
        """Return per-action permissions when provided."""
        if self.action in self.permission_action_classes:
            return [permission() for permission in self.permission_action_classes[self.action]]
        return super().get_permissions()

    def get_queryset(self):
        """
        Build queryset based on user role and query params.

        Anonymous users: only active courses with status='active'
        Authenticated users: active courses
        Instructors: optionally filter own courses (?my_courses=true)
        """
        queryset = Course.objects.prefetch_related('categories').select_related('instructor')

        queryset = queryset.annotate(
            total_enrolled=Count('enrollments', filter=Q(enrollments__is_active=True))
        )

        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_active=True, status='active')
        else:
            queryset = queryset.filter(is_active=True)

        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(categories__id=category_id)

        if self.request.user.is_authenticated and self.request.user.is_instructor():
            if self.request.query_params.get('my_courses') == 'true':
                queryset = queryset.filter(instructor=self.request.user)

        return queryset.distinct()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        return self.serializer_action_classes.get(self.action, CourseCreateUpdateSerializer)

    def perform_create(self, serializer):
        """Set instructor to current user on create."""
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
        summary='Partial update course',
        description='Partially update course details (course instructor only)',
        tags=['Courses'],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary='Delete course',
        description=(
            'Soft delete course (course instructor only). Cannot delete if course is in progress with enrolled students.'
        ),
        tags=['Courses'],
    )
    def destroy(self, request, *args, **kwargs):
        """
        Soft delete a course.
        Prevents deletion if course is in progress and has enrolled students.
        """
        course = self.get_object()

        if course.status == Course.STATUS_IN_PROGRESS and course.enrolled_count > 0:
            return self.bad_request(
                message='Cannot delete a course that is in progress with enrolled students.',
                code='COURSE_IN_PROGRESS_WITH_STUDENTS',
            )

        course.soft_delete()
        return self.ok({'message': 'Course deleted successfully.'})

    @extend_schema(
        summary='Get enrolled students',
        description='Get paginated list of all enrolled students in a course. Only accessible by the course instructor.',
        tags=['Courses'],
        responses={200: EnrolledStudentSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated, IsInstructorOrReadOnly],
        url_path='enrolled-students',
    )
    def enrolled_students(self, request, pk=None):
        """
        Get enrolled students for a course
        GET /api/v1/courses/{id}/enrolled-students/

        Only accessible by course instructor. Returns paginated list of enrolled students.
        """
        course = self.get_object()

        if course.instructor != request.user:
            return self.forbidden({'error': 'Only course instructor can view enrolled students.'})

        enrollments = (
            Enrollment.objects.filter(course=course, is_active=True)
            .select_related('student')
            .order_by('-created_at')
        )

        page = self.paginate_queryset(enrollments)
        if page is not None:
            serializer = EnrolledStudentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = EnrolledStudentSerializer(enrollments, many=True)
        return self.ok(serializer.data)


__all__ = ['CourseViewSet']

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
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view

from django.db.models import BooleanField, Case, Count, F, Q, Value, When
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny

from courses.models import Course
from enrollments.api.serializers import EnrolledStudentSerializer
from enrollments.models import Enrollment

from .filters import CourseFilter
from .permissions import IsCourseInstructor, IsInstructor
from .serializers import (
    CourseDetailSerializer,
    CourseListSerializer,
    CourseWriteSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary='List courses',
        description='Get a paginated list of courses with filtering, search, and ordering. '
        'Anonymous users see only active courses. Instructors can filter their own courses.',
        parameters=[
            OpenApiParameter(
                name='category', type=str, description='Filter by category UUID', required=False
            ),
            OpenApiParameter(
                name='status',
                type=str,
                description='Filter by course status (draft, active, in_progress, completed)',
                required=False,
            ),
            OpenApiParameter(
                name='search',
                type=str,
                description='Search in title, course_code, or description',
                required=False,
            ),
            OpenApiParameter(
                name='my_courses',
                type=OpenApiTypes.BOOL,
                description='(Instructors only) Show only courses I created',
                required=False,
            ),
            OpenApiParameter(
                name='ordering',
                type=str,
                description='Order by: title, created_at, enrolled_count (prefix with - for descending)',
                required=False,
            ),
        ],
        tags=['Courses'],
        responses={200: CourseListSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary='Get course detail',
        description='Retrieve complete details for a single course including instructor, '
        'categories, enrollment stats, and media URLs.',
        tags=['Courses'],
        responses={200: CourseDetailSerializer},
    ),
    create=extend_schema(
        summary='Create course',
        description='Create a new course. Only authenticated instructors can create courses. '
        'The instructor field is automatically set from the authenticated user.',
        tags=['Courses'],
        request=CourseWriteSerializer,
        responses={
            201: CourseDetailSerializer,
            400: {'description': 'Validation error'},
            403: {'description': 'Only instructors can create courses'},
        },
    ),
    update=extend_schema(
        summary='Update course',
        description='Update all fields of a course. Only the course instructor or staff can update.',
        tags=['Courses'],
        request=CourseWriteSerializer,
        responses={
            200: CourseDetailSerializer,
            400: {'description': 'Validation error'},
            403: {'description': 'Only course instructor can update'},
        },
    ),
    partial_update=extend_schema(
        summary='Partial update course',
        description='Update specific fields of a course. Only the course instructor or staff can update.',
        tags=['Courses'],
        request=CourseWriteSerializer,
        responses={
            200: CourseDetailSerializer,
            400: {'description': 'Validation error'},
            403: {'description': 'Only course instructor can update'},
        },
    ),
)
class CourseViewSet(viewsets.ModelViewSet):
    """
    Course ViewSet - Full CRUD operations with custom actions.

    Endpoints:
        GET    /api/v1/courses/                - List courses
        POST   /api/v1/courses/                - Create course (instructors only)
        GET    /api/v1/courses/{id}/           - Retrieve course detail
        PUT    /api/v1/courses/{id}/           - Update course (instructor/owner only)
        PATCH  /api/v1/courses/{id}/           - Partial update (instructor/owner only)
        DELETE /api/v1/courses/{id}/           - Soft delete course (instructor/owner only)
        GET    /api/v1/courses/{id}/enrolled-students/ - List enrolled students (instructor only)

    Permissions:
        - List/Retrieve: Anyone (with role-based filtering)
        - Create: Authenticated instructors only
        - Update/Delete: Course owner or staff
        - enrolled_students: Course instructor only

    Query Parameters:
        - category: Filter by category UUID
        - status: Filter by course status
        - search: Search in title, course_code, description
        - my_courses: (Instructors only) Show only my courses
        - ordering: Order by title, created_at, enrolled_count

    Features:
        - Automatic query optimization with annotations
        - Soft delete instead of hard delete
        - Role-based queryset filtering
        - Computed fields (enrolled_count, is_full, can_enroll)
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

    def get_permissions(self):
        """
        Explicit, action-based permission control.

        Rules:
        - list / retrieve: AllowAny
        - create: Instructor only
        - update / partial_update / destroy: Course owner or staff
        - enrolled_students: Course instructor only
        """

        if self.action in ['list', 'retrieve']:
            return [AllowAny()]

        if self.action == 'create':
            return [IsInstructor()]

        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsCourseInstructor()]

        if self.action == 'enrolled_students':
            return [IsCourseInstructor()]

        return super().get_permissions()

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
            # Logic: max_students is not null AND enrolled >= max_students
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
            # Logic: is_active=True AND status=active AND not full
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
            - Anonymous: Only active courses with status=active
            - Authenticated: All active courses
            - Instructor + ?my_courses=true: Only own courses

        Args:
            queryset: QuerySet to filter

        Returns:
            Filtered QuerySet based on user role
        """
        user = self.request.user

        if not user.is_authenticated:
            return queryset.filter(is_active=True, status=Course.STATUS_ACTIVE)

        queryset = queryset.filter(is_active=True)

        if (
            getattr(user, 'is_instructor', False)
            and self.request.query_params.get('my_courses') == 'true'
        ):
            queryset = queryset.filter(instructor=user)

        return queryset

    # ═══════════════════════════════════════════════════════════════════════════
    #   C R U D
    # ═══════════════════════════════════════════════════════════════════════════

    def perform_create(self, serializer):
        """
        Create course and set instructor from request user.

        Note:
            The serializer will call model's save() which triggers full_clean()
            for additional validation (e.g., instructor role check).
        """
        serializer.save(instructor=self.request.user)

    @extend_schema(
        summary='Soft delete a course',
        description=(
            'Marks a course as inactive (soft delete). '
            'Cannot delete courses in progress with enrolled students.'
        ),
        tags=['Courses'],
        responses={
            200: {
                'description': 'Course deleted successfully',
                'content': {
                    'application/json': {
                        'example': {
                            'message': 'Course deleted successfully.',
                            'course_id': '123e4567-e89b-12d3-a456-426614174000',
                            'course_code': 'CS101',
                        }
                    }
                },
            },
            400: {'description': 'Cannot delete course in progress with students'},
        },
    )
    def destroy(self, request, *args, **kwargs):
        """
        Soft delete a course.

        Business Rules:
            - Cannot delete courses in progress with enrolled students
            - Uses model's soft_delete() method (sets is_active=False)

        Returns:
            200 OK: Course soft-deleted successfully
            400 Bad Request: Course in progress with students
        """
        course = self.get_object()

        # Check if course can be deleted
        # Use annotated value if available, otherwise query enrollments
        enrolled = getattr(
            course, 'enrolled_count_computed', course.enrollments.filter(is_active=True).count()
        )

        if course.is_active and course.status == Course.STATUS_IN_PROGRESS and enrolled > 0:
            return self.bad_request(
                message=_('Cannot delete a course that is in progress with enrolled students.'),
                code='COURSE_IN_PROGRESS_WITH_STUDENTS',
            )

        # Perform soft delete
        course.soft_delete()

        return self.ok(
            {
                'message': _('Course deleted successfully.'),
                'course_id': str(course.id),
                'course_code': course.course_code,
            }
        )

    # ═══════════════════════════════════════════════════════════════════════════
    #   C U S T O M   A C T I O N S
    # ═══════════════════════════════════════════════════════════════════════════

    @extend_schema(
        summary='Get enrolled students',
        tags=['Courses'],
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Course UUID',
            ),
        ],
        responses={
            200: EnrolledStudentSerializer(many=True),
            403: {'description': 'Only course instructor can view enrolled students'},
        },
    )
    @action(
        detail=True,
        methods=['get'],
        url_path='enrolled-students',
        url_name='enrolled-students',
    )
    def enrolled_students(self, request, pk=None):
        """
        Get enrolled students for a course.

        Endpoint: GET /api/v1/courses/{id}/enrolled-students/

        Access Control:
            - Only the course instructor can view enrolled students
            - Returns 403 if user is not the course instructor

        Response:
            Paginated list of enrollments with student details

        Returns:
            200 OK: Paginated enrollment list
            403 Forbidden: User is not the course instructor
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
            return self.get_paginated_response(serializer.data)

        # Return all results if pagination is disabled
        serializer = self.get_serializer(enrollments, many=True)
        return self.ok(serializer.data)


__all__ = ['CourseViewSet']

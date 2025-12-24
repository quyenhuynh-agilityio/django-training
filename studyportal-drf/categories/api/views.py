"""
Category ViewSets

Provides REST API endpoints for category management.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)

from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from categories.api.serializers import CategorySerializer
from categories.models import Category


@extend_schema_view(
    list=extend_schema(
        summary='List all course categories',
        description="""
        Retrieve a list of all active course categories.

        **Filtering & Search:**
        - Search by category name using the `search` parameter
        - Sort results using the `ordering` parameter

        **Search Examples:**
        - `?search=python` - Find categories containing "python"
        - `?search=web` - Find categories related to web development

        **Ordering Examples:**
        - `?ordering=name` - Sort alphabetically A-Z
        - `?ordering=-name` - Sort reverse alphabetically Z-A
        - `?ordering=-created_at` - Sort by newest first

        **Use Cases:**
        - Display category dropdown/filter in course search
        - Show all available course topics
        - Build category navigation menu

        **Note:** Only active categories are returned.
        """,
        parameters=[
            OpenApiParameter(
                name='search',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Search by category name',
                required=False,
                examples=[
                    OpenApiExample(name='Search for Python', value='python'),
                    OpenApiExample(name='Search for Web', value='web development'),
                ],
            ),
            OpenApiParameter(
                name='ordering',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Sort by field (prefix with - for descending)',
                required=False,
                examples=[
                    OpenApiExample(name='Alphabetical', value='name'),
                    OpenApiExample(name='Reverse Alphabetical', value='-name'),
                    OpenApiExample(name='Newest First', value='-created_at'),
                ],
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=CategorySerializer(many=True),
                description='List of active categories retrieved successfully',
                examples=[
                    OpenApiExample(
                        name='Category List',
                        value=[
                            {
                                'id': '123e4567-e89b-12d3-a456-426614174000',
                                'name': 'Web Development',
                                'slug': 'web-development',
                                'description': 'Learn to build modern web applications',
                                'created_at': '2024-01-15T10:30:00Z',
                            },
                            {
                                'id': '223e4567-e89b-12d3-a456-426614174001',
                                'name': 'Data Science',
                                'slug': 'data-science',
                                'description': 'Master data analysis and machine learning',
                                'created_at': '2024-01-16T11:45:00Z',
                            },
                            {
                                'id': '323e4567-e89b-12d3-a456-426614174002',
                                'name': 'Mobile Development',
                                'slug': 'mobile-development',
                                'description': 'Build iOS and Android applications',
                                'created_at': '2024-01-17T09:15:00Z',
                            },
                        ],
                    )
                ],
            ),
        },
        tags=['Categories'],
    ),
    retrieve=extend_schema(
        summary='Get category details',
        description="""
        Retrieve detailed information about a specific category.

        **Response includes:**
        - Category ID and name
        - URL-friendly slug
        - Description
        - Creation timestamp

        **Use Cases:**
        - Display category information on course pages
        - Show category details in navigation
        - Fetch category data for filtering

        **Note:** Returns 404 if category doesn't exist or is inactive.
        """,
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Category UUID',
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=CategorySerializer,
                description='Category details retrieved successfully',
                examples=[
                    OpenApiExample(
                        name='Category Detail',
                        value={
                            'id': '123e4567-e89b-12d3-a456-426614174000',
                            'name': 'Web Development',
                            'slug': 'web-development',
                            'description': 'Learn to build modern web applications using the latest frameworks and best practices. Covers HTML, CSS, JavaScript, React, and backend technologies.',
                            'created_at': '2024-01-15T10:30:00Z',
                            'updated_at': '2024-01-20T14:22:00Z',
                        },
                    )
                ],
            ),
            404: OpenApiResponse(
                description='Category not found or inactive',
                examples=[OpenApiExample(name='Not Found', value={'detail': 'Not found.'})],
            ),
        },
        tags=['Categories'],
    ),
)
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Category ViewSet - Read-only access for course categories

    Provides public access to browse and search course categories.
    Categories help organize and filter courses by subject area.

    **Available Endpoints:**
    - List all categories with search and ordering
    - Retrieve individual category details

    **Features:**
    - Public access (no authentication required)
    - Full-text search by category name
    - Sortable by name or creation date
    - Returns only active categories

    **Common Use Cases:**
    - Display category filter in course listings
    - Show all available course categories
    - Search for specific subject areas
    """

    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


__all__ = ['CategoryViewSet']

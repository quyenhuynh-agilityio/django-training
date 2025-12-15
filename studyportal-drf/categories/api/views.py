"""
Category ViewSets

Provides REST API endpoints for category management.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view

from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from categories.api.serializers import CategorySerializer
from categories.models import Category


@extend_schema_view(
    list=extend_schema(
        summary='List categories',
        description='Get list of all active categories. Supports search and ordering.',
        tags=['Categories'],
    ),
    retrieve=extend_schema(
        summary='Get category detail',
        description='Retrieve a single active category by ID.',
        tags=['Categories'],
    ),
)
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Category ViewSet - Read-only access for public users

    Endpoints:
    ----------
    GET    /api/v1/categories/          - List all active categories
    GET    /api/v1/categories/{id}/     - Retrieve single category

    Filtering:
    ----------
    - Search: ?search=python
    - Ordering: ?ordering=name or ?ordering=-created_at

    Permissions:
    -----------
    - AllowAny: Public access to read category data
    """

    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


__all__ = ['CategoryViewSet']

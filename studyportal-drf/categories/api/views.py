from drf_spectacular.utils import extend_schema

from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from categories.models import Category
from core.api_views import CommonViewSet

from .serializers import CategorySerializer


class CategoryViewSet(CommonViewSet, viewsets.ReadOnlyModelViewSet):
    """
    Category ViewSet - List & Retrieve only

    GET /api/v1/categories/ - List all categories

    Permissions: AllowAny (public access)
    """

    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @extend_schema(
        summary='List categories', description='Get list of active categories', tags=['Categories']
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

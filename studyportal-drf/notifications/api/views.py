from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated

from core.api_views import CommonViewSet
from notifications.models import Notification

from .serializers import (
    MarkAllAsReadResponseSerializer,
    MarkAsReadResponseSerializer,
    NotificationDetailResponseSerializer,
    NotificationListResponseSerializer,
    NotificationSerializer,
    UnreadCountResponseSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary='List my notifications',
        description="""
        Get paginated list of notifications for the authenticated user.

        **Filtering:**
        - `?is_read=false` - Only unread notifications
        - `?is_read=true` - Only read notifications
        - `?type=STUDENT_ENROLLED` - Filter by notification type

        **Ordering:**
        - `?ordering=-created_at` - Newest first (default)
        - `?ordering=created_at` - Oldest first

        Results are cached for performance.
        """,
        parameters=[
            OpenApiParameter(
                name='is_read',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by read status',
            ),
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by notification type',
            ),
        ],
        responses={
            200: NotificationListResponseSerializer,
            401: OpenApiResponse(description='Authentication required'),
        },
        tags=['Notifications'],
    ),
    retrieve=extend_schema(
        summary='Get notification detail',
        description='Retrieve a specific notification by ID.',
        responses={
            200: NotificationDetailResponseSerializer,
            404: OpenApiResponse(description='Notification not found'),
        },
        tags=['Notifications'],
    ),
)
class NotificationViewSet(CommonViewSet, viewsets.ReadOnlyModelViewSet):
    """
    Notification ViewSet

    Provides endpoints for users to:
    - View their notifications (cached)
    - Mark notifications as read
    - Mark all notifications as read
    - Get unread count (cached)
    - Filter by read/unread status and type
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_read', 'type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get notifications for current user only with optimized query"""
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()

        return Notification.objects.filter(recipient=self.request.user).select_related('recipient')

    @extend_schema(
        summary='Mark notification as read',
        description='Mark a specific notification as read. Clears unread count cache.',
        responses={
            200: MarkAsReadResponseSerializer,
            404: OpenApiResponse(description='Notification not found'),
        },
        tags=['Notifications'],
    )
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a single notification as read"""
        notification = self.get_object()
        notification.mark_as_read()

        response_data = {
            'message': 'Notification marked as read',
            'data': notification,
        }

        serializer = MarkAsReadResponseSerializer(response_data)
        return self.ok(serializer.data)

    @extend_schema(
        summary='Mark all notifications as read',
        description='Mark all unread notifications as read for the current user. Clears cache.',
        responses={200: MarkAllAsReadResponseSerializer},
        tags=['Notifications'],
    )
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all unread notifications as read"""
        from django.core.cache import cache

        updated_count = Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True
        )

        # Clear cache
        cache_key = f'notification_unread_count_{request.user.id}'
        cache.delete(cache_key)

        response_data = {
            'message': f'Marked {updated_count} notification(s) as read',
            'count': updated_count,
        }

        serializer = MarkAllAsReadResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return self.ok(serializer.data)

    @extend_schema(
        summary='Get unread notification count',
        description="""
        Get the count of unread notifications for the current user.

        **Performance:**
        - Result is cached for 60 seconds (configurable via NOTIFICATION_CACHE_TIMEOUT)
        - Cache is automatically cleared when notifications are marked as read

        **Use Case:**
        Display badge count in navigation bar.
        """,
        responses={200: UnreadCountResponseSerializer},
        tags=['Notifications'],
    )
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get cached count of unread notifications"""
        count = Notification.get_unread_count_cached(request.user.id)

        response_data = {'unread_count': count}
        serializer = UnreadCountResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return self.ok(serializer.data)

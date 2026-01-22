from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet

# Create router for ViewSet
router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notifications')

# URL patterns
urlpatterns = [
    # ViewSet routes (all notifications endpoints)
    path('', include(router.urls)),
]

"""
Authentication API URLs

Routes all authentication endpoints through DRF router.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from users.api.views import AuthViewSet

# Create router for ViewSet
router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')

# URL patterns
urlpatterns = [
    # ViewSet routes (all auth endpoints)
    path('', include(router.urls)),
]

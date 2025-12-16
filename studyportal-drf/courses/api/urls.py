"""
Course API URLs

Router configuration for course endpoints
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .viewsets import CourseViewSet

# Create router
router = DefaultRouter()

# Register viewsets
router.register(r'courses', CourseViewSet, basename='course')

app_name = 'courses'

urlpatterns = [
    path('', include(router.urls)),
]

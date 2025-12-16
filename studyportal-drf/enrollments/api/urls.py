"""
Enrollment API URLs

Router configuration for enrollment endpoints following DRF best practices.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .viewsets import StudentEnrolledCoursesViewSet

# Create router
router = DefaultRouter()

# Register viewset
router.register(
    r'students/enrollments', StudentEnrolledCoursesViewSet, basename='student-enrollments'
)

app_name = 'enrollments'

urlpatterns = [
    path('', include(router.urls)),
]

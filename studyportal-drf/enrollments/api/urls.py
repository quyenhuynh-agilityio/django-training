from django.urls import path
from rest_framework.routers import DefaultRouter

from enrollments.api.viewsets import (
    EnrollInCourseView,
    EnrollmentActionsViewSet,
    LeaveCourseView,
    StudentEnrolledCoursesViewSet,
)

# Router for ViewSet
router = DefaultRouter()
router.register(
    r'students/enrolled-courses', StudentEnrolledCoursesViewSet, basename='enrolled-course'
)
router.register(
    r'students/enrollment-actions', EnrollmentActionsViewSet, basename='enrollment-action'
)

# URL patterns
urlpatterns = [
    # Enroll in a course
    path('students/enroll/', EnrollInCourseView.as_view(), name='enroll'),
    # Leave a course
    path('students/leave/<uuid:course_id>/', LeaveCourseView.as_view(), name='leave-course'),
]

# Include router URLs
urlpatterns += router.urls

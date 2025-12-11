from rest_framework.routers import DefaultRouter

from enrollments.api.viewsets import (
    EnrollmentActionsViewSet,
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


urlpatterns = router.urls

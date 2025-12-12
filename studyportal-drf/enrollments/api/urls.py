from rest_framework.routers import DefaultRouter

from enrollments.api.viewsets import StudentEnrolledCoursesViewSet

# Router for ViewSet
router = DefaultRouter()

# Enrollment listing, details, and actions (enroll/leave)
router.register(r'students/enrollments', StudentEnrolledCoursesViewSet, basename='enrollment')

urlpatterns = router.urls

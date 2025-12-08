from rest_framework.routers import DefaultRouter

from courses.api.views import CourseViewSet

router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')

urlpatterns = router.urls

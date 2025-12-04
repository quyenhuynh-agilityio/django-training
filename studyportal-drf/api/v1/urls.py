from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from django.urls import include, path
from rest_framework.routers import DefaultRouter

# Import viewsets here when you create them
# from api.v1.views.accounts import AccountViewSet
# from api.v1.views.courses import CourseViewSet
# etc.

# Create router for v1 API
router = DefaultRouter()
# Register viewsets here
# router.register(r'accounts', AccountViewSet, basename='account')
# router.register(r'courses', CourseViewSet, basename='course')

app_name = 'api_v1'

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    # API Documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'schema/swagger-ui/',
        SpectacularSwaggerView.as_view(url_name='api_v1:schema'),
        name='swagger-ui',
    ),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='api_v1:schema'), name='redoc'),
]

# accounts/api/urls.py

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import TokenRefreshSchemaView
from .viewsets import AuthViewSet

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')

urlpatterns = [
    # JWT token refresh
    path('auth/token/refresh/', TokenRefreshSchemaView.as_view(), name='token_refresh'),
]

urlpatterns += router.urls

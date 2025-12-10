# accounts/api/urls.py

from rest_framework_simplejwt.views import TokenRefreshView

from django.urls import path
from rest_framework.routers import DefaultRouter

from .viewsets import AuthViewSet

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')

urlpatterns = [
    # JWT token refresh
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns += router.urls

from rest_framework_simplejwt.views import TokenRefreshView

from django.urls import path

from accounts.api.views import (
    ChangePasswordView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    UserLoginView,
    UserLogoutView,
    UserProfileView,
    UserRegistrationView,
)

# API v1 URLs
urlpatterns = [
    # Authentication Endpoints
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password/reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path(
        'password/reset/confirm/',
        PasswordResetConfirmView.as_view(),
        name='password_reset_confirm',
    ),
    path('password/change/', ChangePasswordView.as_view(), name='change_password'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('me/', UserProfileView.as_view(), name='me'),
]

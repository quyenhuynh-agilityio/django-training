from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # ─────────────────────────────────────────────
    # Admin
    # ─────────────────────────────────────────────
    path('admin/', admin.site.urls),
    # ─────────────────────────────────────────────
    # Website (non-API)
    # ─────────────────────────────────────────────
    path('', include('courses.urls')),
    path('', include('users.urls')),
    path('enrollments/', include('enrollments.urls')),
    # ─────────────────────────────────────────────
    # API v1
    # ─────────────────────────────────────────────
    path('api/v1/users/', include('users.api.urls')),
    path('api/v1/categories/', include('categories.api.urls')),
    path('api/v1/courses/', include('courses.api.urls')),
    path('api/v1/enrollments/', include('enrollments.api.urls')),
    # ─────────────────────────────────────────────
    # API Documentation
    # ─────────────────────────────────────────────
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
]

# ─────────────────────────────────────────────
# Debug Toolbar
# ─────────────────────────────────────────────
if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

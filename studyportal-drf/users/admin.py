from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # ─────────────────────────────────────────
    # List View
    # ─────────────────────────────────────────

    list_display = (
        'email',
        'username',
        'full_name',
        'role_badge',
        'is_active',
        'is_staff',
        'created_at',
    )

    list_filter = (
        'role',
        'is_active',
        'is_staff',
        'is_superuser',
        'created_at',
    )

    search_fields = (
        'email',
        'username',
        'first_name',
        'last_name',
    )

    ordering = ('-created_at',)

    # ─────────────────────────────────────────
    # Detail / Edit View
    # ─────────────────────────────────────────

    fieldsets = (
        (
            _('Login Information'),
            {
                'fields': ('email', 'username', 'password'),
            },
        ),
        (
            _('Personal Information'),
            {
                'fields': ('first_name', 'last_name'),
            },
        ),
        (
            _('Role & Permissions'),
            {
                'fields': (
                    'role',
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
        (
            _('Important Dates'),
            {
                'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
                'classes': ('collapse',),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'username',
                    'first_name',
                    'last_name',
                    'password1',
                    'password2',
                    'role',
                    'is_active',
                ),
            },
        ),
    )

    readonly_fields = (
        'last_login',
        'date_joined',
        'created_at',
        'updated_at',
    )

    # ─────────────────────────────────────────
    # Display Helpers (UI only)
    # ─────────────────────────────────────────

    @admin.display(description=_('Role'), ordering='role')
    def role_badge(self, obj):
        """
        Colored role badge (presentation only).
        """
        color_map = {
            User.ROLE_STUDENT: '#28a745',  # Green
            User.ROLE_INSTRUCTOR: '#0d6efd',  # Blue
            User.ROLE_ADMIN: '#dc3545',  # Red
        }

        return format_html(
            '<span style="background:{}; color:white; '
            'padding:3px 10px; border-radius:4px; font-weight:500;">{}</span>',
            color_map.get(obj.role, '#6c757d'),
            obj.get_role_display(),
        )

    # ─────────────────────────────────────────
    # Safety Defaults
    # ─────────────────────────────────────────

    def get_queryset(self, request):
        """
        Explicit queryset hook for future optimization.
        """
        return super().get_queryset(request)

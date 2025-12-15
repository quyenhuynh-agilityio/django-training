from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User Admin with Instructor Management"""

    list_display = ['email', 'username', 'full_name', 'role_badge', 'is_active', 'created_at']
    list_filter = [
        'role',
        'is_active',
        'is_staff',
        'created_at',
    ]
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-created_at']

    fieldsets = (
        ('Login Information', {'fields': ('email', 'username', 'password')}),
        ('Personal Information', {'fields': ('first_name', 'last_name')}),
        (
            'Role & Permissions',
            {
                'fields': (
                    'role',
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        (
            'Important Dates',
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

    readonly_fields = ['date_joined', 'last_login', 'created_at', 'updated_at']

    def role_badge(self, obj):
        """Colored role badge"""
        colors = {
            'student': '#28a745',
            'instructor': '#007bff',
            'admin': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.role, '#6c757d'),
            obj.get_role_display(),
        )

    role_badge.short_description = 'Role'

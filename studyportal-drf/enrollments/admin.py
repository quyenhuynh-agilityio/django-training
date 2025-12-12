from django.contrib import admin
from django.utils.html import format_html

from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """
    Admin configuration for Enrollment model.

    Features:
    - Optimized list display with colored badges
    - Filtering by status, activity, and course status
    - Search across student and course fields
    - Read-only audit timestamps
    - select_related for better performance
    """

    list_display = [
        'student_email',
        'course_title',
        'status_badge',
        'is_active_badge',
        'created_at',
    ]
    list_filter = [
        'status',
        'is_active',
        'course__status',
    ]
    search_fields = [
        'student__email',
        'student__first_name',
        'student__last_name',
        'course__title',
        'course__course_code',
    ]
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['student', 'course']
    ordering = ['-created_at']
    list_per_page = 25

    fieldsets = (
        ('Enrollment Information', {'fields': ('student', 'course')}),
        ('Status', {'fields': ('status', 'is_active')}),
        (
            'Timestamps',
            {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)},
        ),
    )

    # ─────────────────────────────────────────────
    # List Display Helpers
    # ─────────────────────────────────────────────

    @admin.display(description='Student', ordering='student__email')
    def student_email(self, obj):
        return obj.student.email

    @admin.display(description='Course', ordering='course__title')
    def course_title(self, obj):
        return f'{obj.course.course_code} - {obj.course.title}'

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'active': '#28a745',
            'completed': '#17a2b8',
            'dropped': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display(),
        )

    @admin.display(description='Active')
    def is_active_badge(self, obj):
        color = 'green' if obj.is_active else 'red'
        label = 'Active' if obj.is_active else 'Inactive'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            label,
        )

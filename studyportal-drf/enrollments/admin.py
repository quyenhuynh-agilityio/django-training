# Register your models here.
from django.contrib import admin
from django.utils.html import format_html

from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """
    Enrollment Admin

    Features:
    - View all enrollments
    - Filter by student, course, status
    - Search by student email, course title
    - Colored status badges
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

    fieldsets = (
        ('Enrollment Information', {'fields': ('student', 'course')}),
        ('Status', {'fields': ('status', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('student', 'course')

    def student_email(self, obj):
        """Display student email"""
        return obj.student.email

    student_email.short_description = 'Student'
    student_email.admin_order_field = 'student__email'

    def course_title(self, obj):
        """Display course title"""
        return f'{obj.course.course_code} - {obj.course.title}'

    course_title.short_description = 'Course'
    course_title.admin_order_field = 'course__title'

    def status_badge(self, obj):
        """Display colored status badge"""
        colors = {
            'active': '#28a745',
            'completed': '#17a2b8',
            'dropped': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display(),
        )

    status_badge.short_description = 'Status'

    def is_active_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html('<span style="color: green;">● Active</span>')
        return format_html('<span style="color: red;">● Inactive</span>')

    is_active_badge.short_description = 'Active'

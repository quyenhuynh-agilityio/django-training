# Register your models here.
from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html

from .models import Course


class EnrollmentInline(admin.TabularInline):
    """Inline display of enrollments"""

    from enrollments.models import Enrollment

    model = Enrollment
    extra = 0
    readonly_fields = ['student', 'status']
    can_delete = False
    fields = ['student', 'status']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """
    Enhanced Course Admin

    Features:
    - Colored status badges
    - Enrollment statistics
    - Category management
    - Instructor assignment
    - Inline enrollments
    - Bulk actions
    """

    list_display = [
        'course_code',
        'title',
        'instructor_link',
        'status_badge',
        'enrollment_info',
        'categories_list',
        'is_active',
        'created_at',
    ]
    list_filter = [
        'status',
        'is_active',
        'categories',
        'instructor',
        'created_at',
    ]
    search_fields = [
        'title',
        'course_code',
        'description',
        'instructor__email',
        'instructor__first_name',
        'instructor__last_name',
    ]
    filter_horizontal = ['categories']
    inlines = [EnrollmentInline]

    fieldsets = (
        ('Basic Information', {'fields': ('title', 'course_code', 'description')}),
        ('Organization', {'fields': ('categories', 'instructor')}),
        ('Media', {'fields': ('video_url', 'image_url'), 'classes': ('collapse',)}),
        ('Settings', {'fields': ('status', 'is_active', 'max_students')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        """Optimize queries with annotations"""
        return (
            super()
            .get_queryset(request)
            .select_related('instructor')
            .prefetch_related('categories', 'enrollments')
            .annotate(enrollment_count=Count('enrollments', filter=Q(enrollments__is_active=True)))
        )

    def instructor_link(self, obj):
        """Display instructor with admin link"""
        if obj.instructor:
            url = f'/admin/accounts/user/{obj.instructor.id}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.instructor.full_name)
        return format_html('<span style="color: #dc3545;">No Instructor</span>')

    instructor_link.short_description = 'Instructor'

    def status_badge(self, obj):
        """Display colored status badge"""
        colors = {
            'draft': '#6c757d',
            'active': '#28a745',
            'in_progress': '#007bff',
            'completed': '#17a2b8',
            'inactive': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display(),
        )

    status_badge.short_description = 'Status'

    def enrollment_info(self, obj):
        """Display enrollment statistics"""
        count = obj.enrolled_count
        max_students = obj.max_students or '∞'

        if obj.is_full:
            color = '#dc3545'  # Red
        elif count > 0:
            color = '#28a745'  # Green
        else:
            color = '#6c757d'  # Gray

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}/{}</span> students',
            color,
            count,
            max_students,
        )

    enrollment_info.short_description = 'Enrollments'

    def categories_list(self, obj):
        """Display categories as badges"""
        categories = obj.categories.all()[:3]
        if not categories:
            return '-'

        badges = [
            format_html(
                '<span style="background-color: #17a2b8; color: white; padding: 2px 6px; border-radius: 3px; margin-right: 3px; font-size: 11px;">{}</span>',
                cat.name,
            )
            for cat in categories
        ]

        if obj.categories.count() > 3:
            badges.append(format_html('<span>+{} more</span>', obj.categories.count() - 3))

        return format_html(''.join([str(badge) for badge in badges]))

    categories_list.short_description = 'Categories'

    # Custom actions
    actions = ['activate_courses', 'deactivate_courses', 'set_to_active_status']

    def activate_courses(self, request, queryset):
        """Bulk action: Activate courses"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} course(s) activated.', level='success')

    activate_courses.short_description = '✓ Activate courses'

    def deactivate_courses(self, request, queryset):
        """Bulk action: Deactivate courses (with business rule check)"""
        # Check business rule: cannot deactivate in-progress courses with students
        in_progress = queryset.filter(status='in_progress', enrollments__is_active=True).distinct()

        if in_progress.exists():
            self.message_user(
                request,
                f'Cannot deactivate {in_progress.count()} course(s) in progress with students.',
                level='error',
            )
            queryset = queryset.exclude(id__in=in_progress.values_list('id', flat=True))

        updated = queryset.update(is_active=False)
        if updated:
            self.message_user(request, f'{updated} course(s) deactivated.', level='success')

    deactivate_courses.short_description = '✗ Deactivate courses'

    def set_to_active_status(self, request, queryset):
        """Bulk action: Set status to active"""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} course(s) set to active status.', level='success')

    set_to_active_status.short_description = '→ Set status to Active'

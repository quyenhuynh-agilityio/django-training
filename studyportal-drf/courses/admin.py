from django.contrib import admin
from django.db.models import Count, Q
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html

from accounts.models import User
from enrollments.models import Enrollment

from .models import Course


class EnrollmentInline(admin.TabularInline):
    """Inline display of enrollments."""

    model = Enrollment
    extra = 0
    readonly_fields = ['student', 'status']
    can_delete = False
    fields = ['student', 'status']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """
    Enhanced Course Admin
    - Colored status badges
    - Enrollment stats
    - Instructor link
    - Category badges
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
    autocomplete_fields = ['instructor']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [EnrollmentInline]

    fieldsets = (
        (
            'Basic Information',
            {
                'fields': ('title', 'course_code', 'description'),
            },
        ),
        (
            'Organization',
            {
                'fields': ('categories', 'instructor'),
            },
        ),
        (
            'Media',
            {
                'classes': ('collapse',),
                'fields': ('video_url', 'image_url'),
            },
        ),
        (
            'Settings',
            {
                'fields': ('status', 'is_active', 'max_students'),
            },
        ),
        (
            'Timestamps',
            {
                'classes': ('collapse',),
                'fields': ('created_at', 'updated_at'),
            },
        ),
    )

    # -------------------------------------------------------------------
    # Query Optimizations
    # -------------------------------------------------------------------

    def get_queryset(self, request):
        """Optimize queries and add enrollment count annotation."""
        return (
            super()
            .get_queryset(request)
            .select_related('instructor')
            .prefetch_related('categories', 'enrollments')
            .annotate(enrollment_count=Count('enrollments', filter=Q(enrollments__is_active=True)))
        )

    # -------------------------------------------------------------------
    # Display Helpers
    # -------------------------------------------------------------------

    def instructor_link(self, obj):
        """Clickable instructor link."""
        if not obj.instructor:
            return format_html('<span style="color:#dc3545;">No Instructor</span>')

        url = reverse('admin:accounts_user_change', args=[obj.instructor.id])
        return format_html('<a href="{}">{}</a>', url, obj.instructor.full_name)

    instructor_link.short_description = 'Instructor'

    def status_badge(self, obj):
        """Colored status badge."""
        colors = {
            'draft': '#6c757d',
            'active': '#28a745',
            'in_progress': '#007bff',
            'completed': '#17a2b8',
            'inactive': '#dc3545',
        }

        color = colors.get(obj.status, '#6c757d')

        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; border-radius:3px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = 'Status'

    def enrollment_info(self, obj):
        """Colored enrollment stats."""
        count = obj.enrolled_count
        max_students = obj.max_students or '∞'

        if obj.is_full:
            color = '#dc3545'
        elif count > 0:
            color = '#28a745'
        else:
            color = '#6c757d'

        return format_html(
            '<span style="color:{}; font-weight:bold;">{}/{}</span> students',
            color,
            count,
            max_students,
        )

    enrollment_info.short_description = 'Enrollments'

    def categories_list(self, obj):
        """Display categories as badges."""
        categories = obj.categories.all()[:3]

        if not categories:
            return '-'

        badges = [
            f'<span style="background:#17a2b8; color:white; padding:2px 6px; '
            f'border-radius:3px; margin-right:3px; font-size:11px;">{c.name}</span>'
            for c in categories
        ]

        extra = obj.categories.count() - 3
        if extra > 0:
            badges.append(f'<span>+{extra} more</span>')

        return format_html(''.join(badges))

    categories_list.short_description = 'Categories'

    # -------------------------------------------------------------------
    # Custom Actions
    # -------------------------------------------------------------------

    actions = [
        'activate_courses',
        'deactivate_courses',
        'set_to_active_status',
        'set_instructor',
    ]

    def activate_courses(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} course(s) activated.', level='success')

    activate_courses.short_description = 'Activate courses'

    def deactivate_courses(self, request, queryset):
        """Prevent deactivating courses in progress with active students."""
        in_progress = queryset.filter(status='in_progress', enrollments__is_active=True).distinct()

        if in_progress.exists():
            self.message_user(
                request,
                f'Cannot deactivate {in_progress.count()} course(s) '
                'in progress with active students.',
                level='error',
            )
            queryset = queryset.exclude(id__in=in_progress.values_list('id', flat=True))

        updated = queryset.update(is_active=False)
        if updated:
            self.message_user(request, f'{updated} course(s) deactivated.', level='success')

    deactivate_courses.short_description = 'Deactivate courses'

    def set_to_active_status(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} course(s) set to Active.', level='success')

    set_to_active_status.short_description = 'Set status to Active'

    # -------------------------------------------------------------------
    # Action: Set Instructor
    # -------------------------------------------------------------------

    def set_instructor(self, request, queryset):
        """Assign instructor to selected courses."""
        instructors = User.objects.filter(role='instructor').order_by(
            'first_name', 'last_name', 'email'
        )

        if request.method == 'POST' and 'apply' in request.POST:
            instructor_id = request.POST.get('instructor')

            if not instructor_id:
                self.message_user(request, 'No instructor selected.', level='error')
                return None

            instructor = User.objects.filter(id=instructor_id, role='instructor').first()

            if not instructor:
                self.message_user(request, 'Invalid instructor.', level='error')
                return None

            updated = queryset.update(instructor=instructor)

            self.message_user(
                request,
                f"Instructor '{instructor.full_name}' set for {updated} course(s).",
                level='success',
            )
            return None

        context = {
            **admin.site.each_context(request),
            'title': 'Set instructor',
            'courses': queryset,
            'course_ids': [str(c.id) for c in queryset],
            'instructors': instructors,
            'opts': self.model._meta,
        }

        return TemplateResponse(
            request,
            'admin/courses/course/set_instructor.html',
            context,
        )

    set_instructor.short_description = 'Set instructor to courses'

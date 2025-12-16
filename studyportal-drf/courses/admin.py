"""
Course Django Admin Configuration

Enhanced admin interface with:
- Colored status badges
- Enrollment statistics
- Instructor links
- Category badges
- Bulk actions with validation
- Query optimization
"""

from django.contrib import admin
from django.db.models import Count, Q
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from enrollments.models import Enrollment
from users.models import User

from .models import Course


class EnrollmentInline(admin.TabularInline):
    """Inline display of enrollments within course admin."""

    model = Enrollment
    extra = 0
    readonly_fields = ['student', 'status', 'created_at']
    can_delete = False
    fields = ['student', 'status', 'is_active', 'created_at']

    def has_add_permission(self, request, obj=None):
        """Prevent adding enrollments through inline"""
        return False


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """
    Enhanced Course Admin Interface

    Features:
    - Colored status badges
    - Real-time enrollment statistics
    - Clickable instructor links
    - Category display with badges
    - Bulk actions for course management
    - Query optimization with select_related/prefetch_related
    """

    list_display = [
        'course_code',
        'title',
        'instructor_link',
        'status_badge',
        'enrollment_info',
        'categories_list',
        'is_active_badge',
        'created_at',
    ]

    list_filter = [
        'status',
        'is_active',
        'categories',
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
    readonly_fields = ['created_at', 'updated_at', 'enrollment_stats']
    inlines = [EnrollmentInline]
    list_per_page = 25
    date_hierarchy = 'created_at'

    fieldsets = (
        (
            _('Basic Information'),
            {
                'fields': ('title', 'course_code', 'description'),
            },
        ),
        (
            _('Organization'),
            {
                'fields': ('categories', 'instructor'),
            },
        ),
        (
            _('Media'),
            {
                'classes': ('collapse',),
                'fields': ('video_url', 'image_url'),
            },
        ),
        (
            _('Settings'),
            {
                'fields': ('status', 'is_active', 'max_students'),
            },
        ),
        (
            _('Statistics'),
            {
                'classes': ('collapse',),
                'fields': ('enrollment_stats',),
            },
        ),
        (
            _('Timestamps'),
            {
                'classes': ('collapse',),
                'fields': ('created_at', 'updated_at'),
            },
        ),
    )

    actions = [
        'activate_courses',
        'deactivate_courses',
        'set_to_active_status',
        'set_instructor',
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    #   Q U E R Y   O P T I M I Z A T I O N
    # ═══════════════════════════════════════════════════════════════════════════

    def get_queryset(self, request):
        """
        Optimize queries with select_related and prefetch_related.
        Add enrollment count annotation for better performance.
        """
        queryset = super().get_queryset(request)
        return (
            queryset.select_related('instructor')
            .prefetch_related('categories')
            .annotate(enrollment_count=Count('enrollments', filter=Q(enrollments__is_active=True)))
        )

    # ═══════════════════════════════════════════════════════════════════════════
    #   D I S P L A Y   H E L P E R S
    # ═══════════════════════════════════════════════════════════════════════════

    @admin.display(description=_('Instructor'), ordering='instructor__first_name')
    def instructor_link(self, obj):
        """Display clickable link to instructor's admin page"""
        if not obj.instructor:
            return format_html('<span style="color:#dc3545;">{}</span>', _('No Instructor'))

        url = reverse('admin:users_user_change', args=[obj.instructor.id])
        return format_html(
            '<a href="{}" style="font-weight:500;">{}</a>',
            url,
            obj.instructor.full_name or obj.instructor.email,
        )

    @admin.display(description=_('Status'), ordering='status')
    def status_badge(self, obj):
        """Display colored status badge"""
        colors = {
            Course.STATUS_DRAFT: '#6c757d',  # Gray
            Course.STATUS_ACTIVE: '#28a745',  # Green
            Course.STATUS_IN_PROGRESS: '#007bff',  # Blue
            Course.STATUS_COMPLETED: '#17a2b8',  # Teal
        }

        color = colors.get(obj.status, '#6c757d')

        return format_html(
            '<span style="background-color:{}; color:white; '
            'padding:4px 12px; border-radius:4px; font-weight:500; '
            'display:inline-block;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description=_('Enrollments'))
    def enrollment_info(self, obj):
        """Display enrollment statistics with color coding"""
        # Use annotated value if available, otherwise compute
        count = getattr(obj, 'enrollment_count', None)
        if count is None:
            count = obj.enrollments.filter(is_active=True).count()

        max_students = obj.max_students or '∞'

        # Color based on capacity
        if obj.is_full:
            color = '#dc3545'  # Red - Full
        elif count > 0:
            color = '#28a745'  # Green - Has students
        else:
            color = '#6c757d'  # Gray - Empty

        return format_html(
            '<span style="color:{}; font-weight:600;">{}/{}</span> {}',
            color,
            count,
            max_students,
            _('students'),
        )

    @admin.display(description=_('Categories'))
    def categories_list(self, obj):
        """Display categories as colored badges"""
        categories = list(obj.categories.all()[:3])

        if not categories:
            return format_html('<span style="color:#999;">—</span>')

        badges = []
        for cat in categories:
            badges.append(
                format_html(
                    '<span style="background-color:#17a2b8; color:white; '
                    'padding:2px 8px; border-radius:3px; margin-right:4px; '
                    'font-size:11px; display:inline-block;">{}</span>',
                    cat.name,
                )
            )

        # Show +X more if there are additional categories
        total_count = obj.categories.count()
        extra = total_count - 3
        if extra > 0:
            badges.append(
                format_html(
                    '<span style="color:#6c757d; font-size:11px;">+{} {}</span>', extra, _('more')
                )
            )

        return format_html(' '.join(str(b) for b in badges))

    @admin.display(description=_('Active'), boolean=True)
    def is_active_badge(self, obj):
        """Display active status as boolean icon"""
        return obj.is_active

    @admin.display(description=_('Enrollment Statistics'))
    def enrollment_stats(self, obj):
        """Display detailed enrollment statistics in detail view"""
        if not obj.pk:
            return _('Save course first to see statistics')

        active = obj.enrollments.filter(is_active=True).count()
        completed = obj.enrollments.filter(status=Enrollment.STATUS_COMPLETED).count()
        dropped = obj.enrollments.filter(status=Enrollment.STATUS_DROPPED).count()
        total = active + completed + dropped

        return format_html(
            '<div style="padding:10px; background:#f8f9fa; border-radius:4px;">'
            '<strong style="display:block; margin-bottom:8px;">{}</strong>'
            '<ul style="margin:0; padding-left:20px;">'
            '<li><strong>{}:</strong> {}</li>'
            '<li><strong>{}:</strong> {}</li>'
            '<li><strong>{}:</strong> {}</li>'
            '<li><strong>{}:</strong> {}</li>'
            '</ul>'
            '</div>',
            _('Enrollment Summary'),
            _('Active'),
            active,
            _('Completed'),
            completed,
            _('Dropped'),
            dropped,
            _('Total'),
            total,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    #   B U L K   A C T I O N S
    # ═══════════════════════════════════════════════════════════════════════════

    @admin.action(description=_('Activate selected courses'))
    def activate_courses(self, request, queryset):
        """Bulk activate selected courses"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            _('{count} course(s) activated successfully.').format(count=updated),
            level='success',
        )

    @admin.action(description=_('Deactivate selected courses'))
    def deactivate_courses(self, request, queryset):
        """
        Bulk deactivate selected courses.
        Prevents deactivating in-progress courses with active students.
        """
        # Find courses that cannot be deactivated
        in_progress = (
            queryset.filter(status=Course.STATUS_IN_PROGRESS)
            .annotate(active_students=Count('enrollments', filter=Q(enrollments__is_active=True)))
            .filter(active_students__gt=0)
        )

        if in_progress.exists():
            in_progress_count = in_progress.count()
            in_progress_codes = ', '.join(in_progress.values_list('course_code', flat=True)[:5])

            self.message_user(
                request,
                _(
                    'Cannot deactivate {count} in-progress course(s) with active students: {codes}'
                ).format(count=in_progress_count, codes=in_progress_codes),
                level='error',
            )

            # Exclude problematic courses
            queryset = queryset.exclude(id__in=in_progress.values_list('id', flat=True))

        # Deactivate remaining courses
        updated = queryset.update(is_active=False)
        if updated:
            self.message_user(
                request,
                _('{count} course(s) deactivated successfully.').format(count=updated),
                level='success',
            )

    @admin.action(description=_('Set status to Active'))
    def set_to_active_status(self, request, queryset):
        """Bulk set course status to active"""
        updated = queryset.update(status=Course.STATUS_ACTIVE)
        self.message_user(
            request,
            _('{count} course(s) set to Active status.').format(count=updated),
            level='success',
        )

    @admin.action(description=_('Assign instructor to courses'))
    def set_instructor(self, request, queryset):
        """
        Bulk assign instructor to selected courses.
        Shows intermediate page with instructor selection form.
        """
        # Get all instructors for selection
        instructors = User.objects.filter(role=User.ROLE_INSTRUCTOR).order_by(
            'first_name', 'last_name', 'email'
        )

        # Handle form submission
        if request.method == 'POST' and 'apply' in request.POST:
            instructor_id = request.POST.get('instructor')

            if not instructor_id:
                self.message_user(request, _('No instructor selected.'), level='error')
                return None

            try:
                instructor = User.objects.get(id=instructor_id, role=User.ROLE_INSTRUCTOR)
            except User.DoesNotExist:
                self.message_user(request, _('Invalid instructor selected.'), level='error')
                return None

            # Update courses
            updated = queryset.update(instructor=instructor)
            self.message_user(
                request,
                _("Instructor '{name}' assigned to {count} course(s).").format(
                    name=instructor.full_name, count=updated
                ),
                level='success',
            )
            return None

        # Show selection form
        context = {
            **self.admin_site.each_context(request),
            'title': _('Assign instructor to courses'),
            'courses': queryset,
            'course_ids': ','.join(str(c.id) for c in queryset),
            'instructors': instructors,
            'opts': self.model._meta,
            'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
        }

        return TemplateResponse(request, 'admin/courses/course/set_instructor.html', context)


__all__ = ['CourseAdmin', 'EnrollmentInline']

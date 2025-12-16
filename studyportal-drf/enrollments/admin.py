"""
Enrollment Django Admin Configuration

Enhanced admin interface with:
- Colored status and activity badges
- Optimized queries with select_related
- Student and course search
- Filtering by multiple criteria
- Bulk actions for status management
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """
    Enhanced Enrollment Admin Interface

    Features:
    - Optimized list display with colored badges
    - Comprehensive filtering options
    - Search across student and course fields
    - Read-only audit timestamps
    - Bulk actions for enrollment management
    - Query optimization with select_related
    """

    list_display = [
        'enrollment_id',
        'student_link',
        'course_link',
        'status_badge',
        'is_active_badge',
        'enrolled_date',
    ]

    list_filter = [
        'status',
        'is_active',
        ('created_at', admin.DateFieldListFilter),
        'course__status',
    ]

    search_fields = [
        'student__email',
        'student__first_name',
        'student__last_name',
        'course__title',
        'course__course_code',
    ]

    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'enrollment_details',
    ]

    list_select_related = ['student', 'course', 'course__instructor']
    ordering = ['-created_at']
    list_per_page = 25
    date_hierarchy = 'created_at'

    fieldsets = (
        (
            _('Enrollment Information'),
            {
                'fields': ('id', 'student', 'course'),
            },
        ),
        (
            _('Status'),
            {
                'fields': ('status', 'is_active'),
            },
        ),
        (
            _('Details'),
            {
                'classes': ('collapse',),
                'fields': ('enrollment_details',),
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
        'mark_as_active',
        'mark_as_completed',
        'mark_as_dropped',
        'reactivate_enrollments',
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    #   Q U E R Y   O P T I M I Z A T I O N
    # ═══════════════════════════════════════════════════════════════════════════

    def get_queryset(self, request):
        """
        Optimize queries with select_related for better performance.
        Fetches related student, course, and instructor in single query.
        """
        queryset = super().get_queryset(request)
        return queryset.select_related('student', 'course', 'course__instructor')

    # ═══════════════════════════════════════════════════════════════════════════
    #   D I S P L A Y   H E L P E R S
    # ═══════════════════════════════════════════════════════════════════════════

    @admin.display(description=_('ID'), ordering='id')
    def enrollment_id(self, obj):
        """Display shortened enrollment ID"""
        return str(obj.id)[:8]

    @admin.display(description=_('Student'), ordering='student__email')
    def student_link(self, obj):
        """Display student email with full name on hover"""
        return format_html(
            '<span title="{}">{}</span>', obj.student.full_name or _('No name'), obj.student.email
        )

    @admin.display(description=_('Course'), ordering='course__title')
    def course_link(self, obj):
        """Display course code and title"""
        return format_html(
            '<strong>{}</strong> — {}',
            obj.course.course_code,
            obj.course.title[:50] + ('...' if len(obj.course.title) > 50 else ''),
        )

    @admin.display(description=_('Status'), ordering='status')
    def status_badge(self, obj):
        """Display colored status badge"""
        colors = {
            Enrollment.STATUS_ACTIVE: '#28a745',  # Green
            Enrollment.STATUS_COMPLETED: '#17a2b8',  # Teal
            Enrollment.STATUS_DROPPED: '#dc3545',  # Red
        }

        color = colors.get(obj.status, '#6c757d')

        return format_html(
            '<span style="background-color:{}; color:white; '
            'padding:4px 12px; border-radius:4px; font-weight:500; '
            'display:inline-block;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description=_('Active'), boolean=True, ordering='is_active')
    def is_active_badge(self, obj):
        """Display active status as boolean icon"""
        return obj.is_active

    @admin.display(description=_('Enrolled'), ordering='created_at')
    def enrolled_date(self, obj):
        """Display formatted enrollment date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')

    @admin.display(description=_('Enrollment Details'))
    def enrollment_details(self, obj):
        """Display detailed enrollment information in detail view"""
        if not obj.pk:
            return _('Save enrollment first to see details')

        return format_html(
            '<div style="padding:12px; background:#f8f9fa; border-radius:4px; '
            'border-left:4px solid #007bff;">'
            '<table style="width:100%; border-collapse:collapse;">'
            '<tr><td style="padding:4px 8px;"><strong>{}:</strong></td><td>{}</td></tr>'
            '<tr><td style="padding:4px 8px;"><strong>{}:</strong></td><td>{}</td></tr>'
            '<tr><td style="padding:4px 8px;"><strong>{}:</strong></td><td>{}</td></tr>'
            '<tr><td style="padding:4px 8px;"><strong>{}:</strong></td><td>{}</td></tr>'
            '<tr><td style="padding:4px 8px;"><strong>{}:</strong></td><td>{}</td></tr>'
            '<tr><td style="padding:4px 8px;"><strong>{}:</strong></td><td>{}</td></tr>'
            '</table>'
            '</div>',
            _('Student Name'),
            obj.student.full_name or _('N/A'),
            _('Student Email'),
            obj.student.email,
            _('Course Code'),
            obj.course.course_code,
            _('Course Title'),
            obj.course.title,
            _('Instructor'),
            obj.course.instructor.full_name if obj.course.instructor else _('N/A'),
            _('Course Status'),
            obj.course.get_status_display(),
        )

    # ═══════════════════════════════════════════════════════════════════════════
    #   F O R M   C U S T O M I Z A T I O N
    # ═══════════════════════════════════════════════════════════════════════════

    def get_form(self, request, obj=None, **kwargs):
        """Customize form to limit student choices to students only"""
        form = super().get_form(request, obj, **kwargs)

        # Limit student field to users with student role
        if 'student' in form.base_fields:
            from users.models import User

            form.base_fields['student'].queryset = User.objects.filter(role=User.ROLE_STUDENT)

        return form

    # ═══════════════════════════════════════════════════════════════════════════
    #   B U L K   A C T I O N S
    # ═══════════════════════════════════════════════════════════════════════════

    @admin.action(description=_('Mark as Active'))
    def mark_as_active(self, request, queryset):
        """Bulk set enrollment status to active"""
        updated = queryset.update(status=Enrollment.STATUS_ACTIVE, is_active=True)
        self.message_user(
            request,
            _('{count} enrollment(s) marked as active.').format(count=updated),
            level='success',
        )

    @admin.action(description=_('Mark as Completed'))
    def mark_as_completed(self, request, queryset):
        """Bulk set enrollment status to completed"""
        updated = queryset.filter(is_active=True).update(status=Enrollment.STATUS_COMPLETED)
        self.message_user(
            request,
            _('{count} enrollment(s) marked as completed.').format(count=updated),
            level='success',
        )

    @admin.action(description=_('Mark as Dropped'))
    def mark_as_dropped(self, request, queryset):
        """Bulk set enrollment status to dropped and deactivate"""
        updated = queryset.update(status=Enrollment.STATUS_DROPPED, is_active=False)
        self.message_user(
            request,
            _('{count} enrollment(s) marked as dropped.').format(count=updated),
            level='warning',
        )

    @admin.action(description=_('Reactivate enrollments'))
    def reactivate_enrollments(self, request, queryset):
        """
        Reactivate previously dropped enrollments.
        Only works for dropped enrollments.
        """
        # Only reactivate dropped enrollments
        dropped = queryset.filter(status=Enrollment.STATUS_DROPPED, is_active=False)

        updated = dropped.update(status=Enrollment.STATUS_ACTIVE, is_active=True)

        if updated:
            self.message_user(
                request,
                _('{count} enrollment(s) reactivated.').format(count=updated),
                level='success',
            )
        else:
            self.message_user(
                request, _('No dropped enrollments selected to reactivate.'), level='warning'
            )

    # ═══════════════════════════════════════════════════════════════════════════
    #   P E R M I S S I O N S
    # ═══════════════════════════════════════════════════════════════════════════

    def has_add_permission(self, request):
        """
        Allow adding enrollments through admin.
        Consider restricting this in production.
        """
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """
        Prevent deletion of enrollments.
        Use soft delete (is_active=False) instead.
        """
        return False


__all__ = ['EnrollmentAdmin']

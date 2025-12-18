from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from utils.admin.badges import status_badge
from utils.admin.display import admin_link

from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        'short_id',
        'student_display',
        'course_display',
        'status_badge',
        'is_active',
        'enrolled_at',
    )

    list_filter = (
        'status',
        'is_active',
        'course__status',
        ('created_at', admin.DateFieldListFilter),
    )

    search_fields = (
        'student__email',
        'student__first_name',
        'student__last_name',
        'course__title',
        'course__course_code',
    )

    ordering = ('-created_at',)
    list_per_page = 25
    date_hierarchy = 'created_at'

    list_select_related = ('student', 'course', 'course__instructor')

    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'details_panel',
    )

    fieldsets = (
        (_('Enrollment'), {'fields': ('id', 'student', 'course')}),
        (_('Status'), {'fields': ('status', 'is_active')}),
        (_('Details'), {'fields': ('details_panel',), 'classes': ('collapse',)}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    # ─────────────────────────────────────────────
    # QUERY OPTIMIZATION
    # ─────────────────────────────────────────────

    def get_queryset(self, request):
        return (
            super().get_queryset(request).select_related('student', 'course', 'course__instructor')
        )

    # ─────────────────────────────────────────────
    # DISPLAY HELPERS (PRESENTATION ONLY)
    # ─────────────────────────────────────────────

    @admin.display(description=_('ID'), ordering='id')
    def short_id(self, obj):
        return str(obj.id)[:8]

    @admin.display(description=_('Student'), ordering='student__email')
    def student_display(self, obj):
        return admin_link(
            obj.student,
            admin_url='admin:users_user_change',
            label=obj.student.email,
        )

    @admin.display(description=_('Course'), ordering='course__title')
    def course_display(self, obj):
        return admin_link(
            obj.course,
            admin_url='admin:courses_course_change',
            label=f'{obj.course.course_code} — {obj.course.title}',
        )

    @admin.display(description=_('Status'), ordering='status')
    def status_badge(self, obj):
        colors = {
            Enrollment.STATUS_ACTIVE: '#28a745',
            Enrollment.STATUS_COMPLETED: '#17a2b8',
            Enrollment.STATUS_DROPPED: '#dc3545',
        }

        return status_badge(obj.get_status_display(), obj.status, colors)

    @admin.display(description=_('Enrolled At'), ordering='created_at')
    def enrolled_at(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')

    @admin.display(description=_('Details'))
    def details_panel(self, obj):
        return format_html(
            '<div style="padding:10px;background:#f8f9fa;border-left:4px solid #0d6efd;">'
            '<b>{}</b>: {}<br>'
            '<b>{}</b>: {}<br>'
            '<b>{}</b>: {}<br>'
            '</div>',
            _('Student'),
            obj.student.email,
            _('Instructor'),
            obj.course.instructor.full_name if obj.course.instructor else _('N/A'),
            _('Course Status'),
            obj.course.get_status_display(),
        )

    # ─────────────────────────────────────────────
    # BULK ACTIONS (SAFE)
    # ─────────────────────────────────────────────

    actions = (
        'mark_active',
        'mark_completed',
        'mark_dropped',
    )

    @admin.action(description=_('Mark as active'))
    def mark_active(self, request, queryset):
        updated = queryset.filter(is_active=False).update(
            status=Enrollment.STATUS_ACTIVE, is_active=True
        )
        self.message_user(request, _(f'{updated} enrollment(s) activated.'))

    @admin.action(description=_('Mark as completed'))
    def mark_completed(self, request, queryset):
        updated = queryset.filter(is_active=True).update(status=Enrollment.STATUS_COMPLETED)
        self.message_user(request, _(f'{updated} enrollment(s) completed.'))

    @admin.action(description=_('Mark as dropped'))
    def mark_dropped(self, request, queryset):
        updated = queryset.update(status=Enrollment.STATUS_DROPPED, is_active=False)
        self.message_user(request, _(f'{updated} enrollment(s) dropped.'), level='warning')

    # ─────────────────────────────────────────────
    # PERMISSIONS
    # ─────────────────────────────────────────────

    def has_add_permission(self, request):
        """
        Allow adding enrollments through admin.
        Consider restricting this in production.
        """
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

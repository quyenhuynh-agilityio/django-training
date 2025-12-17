from django.contrib import admin, messages
from django.db.models import Count, Q
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from enrollments.models import Enrollment
from users.models import User
from utils.admin.badges import status_badge
from utils.admin.display import admin_link

from .models import Course


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    can_delete = False
    readonly_fields = ('student', 'status', 'is_active', 'created_at')
    fields = ('student', 'status', 'is_active', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False


# ─────────────────────────────────────────────────────────────
# Course Admin
# ─────────────────────────────────────────────────────────────


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """
    Course Admin — UI-focused, safe, and scalable.
    """

    # ── List View ─────────────────────────────────────────────
    list_display = (
        'course_code',
        'title',
        'instructor_link',
        'status_badge',
        'enrollment_info',
        'categories_list',
        'is_active_badge',
        'created_at',
    )

    list_filter = ('status', 'is_active', 'categories', 'created_at')
    search_fields = (
        'title',
        'course_code',
        'description',
        'instructor__email',
        'instructor__first_name',
        'instructor__last_name',
    )

    list_per_page = 25
    date_hierarchy = 'created_at'

    # ── Forms ────────────────────────────────────────────────
    filter_horizontal = ('categories',)
    autocomplete_fields = ('instructor',)
    readonly_fields = ('created_at', 'updated_at', 'enrollment_stats')
    inlines = (EnrollmentInline,)

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

    actions = (
        'activate_courses',
        'deactivate_courses',
        'set_to_active_status',
        'set_instructor',
    )

    # ─────────────────────────────────────────────────────────
    # Query Optimization
    # ─────────────────────────────────────────────────────────

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related('instructor')
            .prefetch_related('categories')
            .annotate(
                active_enrollments=Count(
                    'enrollments',
                    filter=Q(enrollments__is_active=True),
                )
            )
        )

    # ─────────────────────────────────────────────────────────
    # Display Helpers (UI-only)
    # ─────────────────────────────────────────────────────────

    @admin.display(description=_('Instructor'), ordering='instructor__email')
    def instructor_link(self, obj):
        return admin_link(
            obj.instructor,
            admin_url='admin:users_user_change',
            label=obj.instructor.full_name if obj.instructor else None,
        )

    @admin.display(description=_('Status'), ordering='status')
    def status_badge(self, obj):
        colors = {
            Course.STATUS_DRAFT: '#6c757d',
            Course.STATUS_ACTIVE: '#28a745',
            Course.STATUS_IN_PROGRESS: '#007bff',
            Course.STATUS_COMPLETED: '#17a2b8',
        }

        return status_badge(obj.get_status_display(), obj.status, colors)

    @admin.display(description=_('Enrollments'))
    def enrollment_info(self, obj):
        count = getattr(obj, 'active_enrollments', 0)
        max_students = obj.max_students or '∞'

        color = '#dc3545' if obj.is_full else '#28a745' if count else '#6c757d'

        return format_html(
            '<span style="color:{}; font-weight:600;">{}/{}</span>',
            color,
            count,
            max_students,
        )

    @admin.display(description=_('Categories'))
    def categories_list(self, obj):
        categories = list(obj.categories.all()[:3])

        if not categories:
            return format_html('<span style="color:#999;">—</span>')

        badges = [
            format_html(
                '<span style="background:#17a2b8; color:white; padding:2px 6px; '
                'border-radius:3px; font-size:11px; margin-right:4px;">{}</span>',
                c.name,
            )
            for c in categories
        ]

        extra = obj.categories.count() - 3
        if extra > 0:
            badges.append(format_html('<span style="font-size:11px;">+{}</span>', extra))

        return format_html(''.join(badges))

    @admin.display(description=_('Active'), boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @admin.display(description=_('Enrollment Statistics'))
    def enrollment_stats(self, obj):
        if not obj.pk:
            return _('Save course to view statistics')

        qs = obj.enrollments
        return format_html(
            '<ul style="margin-left:18px;">'
            '<li><strong>{}:</strong> {}</li>'
            '<li><strong>{}:</strong> {}</li>'
            '<li><strong>{}:</strong> {}</li>'
            '</ul>',
            _('Active'),
            qs.filter(is_active=True).count(),
            _('Completed'),
            qs.filter(status=Enrollment.STATUS_COMPLETED).count(),
            _('Dropped'),
            qs.filter(status=Enrollment.STATUS_DROPPED).count(),
        )

    # ─────────────────────────────────────────────────────────
    # Save Validation (Admin-only guardrail)
    # ─────────────────────────────────────────────────────────

    def save_model(self, request, obj, form, change):
        if change:
            original = Course.objects.get(pk=obj.pk)

            if (
                original.is_active
                and not obj.is_active
                and original.status == Course.STATUS_IN_PROGRESS
                and original.enrollments.filter(is_active=True).exists()
            ):
                messages.error(
                    request,
                    _('Cannot deactivate an in-progress course with active enrollments.'),
                )
                return

        super().save_model(request, obj, form, change)

    # ─────────────────────────────────────────────────────────
    # Bulk Actions
    # ─────────────────────────────────────────────────────────

    @admin.action(description=_('Activate selected courses'))
    def activate_courses(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            _('{count} course(s) activated.').format(count=updated),
            messages.SUCCESS,
        )

    @admin.action(description=_('Deactivate selected courses'))
    def deactivate_courses(self, request, queryset):
        blocked = queryset.filter(
            status=Course.STATUS_IN_PROGRESS,
            enrollments__is_active=True,
        ).distinct()

        if blocked.exists():
            self.message_user(
                request,
                _('Some in-progress courses with active students were skipped.'),
                messages.ERROR,
            )
            queryset = queryset.exclude(pk__in=blocked.values_list('pk', flat=True))

        updated = queryset.update(is_active=False)
        if updated:
            self.message_user(
                request,
                _('{count} course(s) deactivated.').format(count=updated),
                messages.SUCCESS,
            )

    @admin.action(description=_('Set status to Active'))
    def set_to_active_status(self, request, queryset):
        queryset.update(status=Course.STATUS_ACTIVE)
        self.message_user(request, _('Status updated.'), messages.SUCCESS)

    @admin.action(description=_('Assign instructor'))
    def set_instructor(self, request, queryset):
        instructors = User.objects.filter(role=User.ROLE_INSTRUCTOR)

        if request.method == 'POST' and 'apply' in request.POST:
            instructor = instructors.filter(pk=request.POST.get('instructor')).first()
            if not instructor:
                self.message_user(request, _('Invalid instructor.'), messages.ERROR)
                return

            queryset.update(instructor=instructor)
            self.message_user(request, _('Instructor assigned.'), messages.SUCCESS)
            return

        context = {
            **self.admin_site.each_context(request),
            'title': _('Assign instructor'),
            'courses': queryset,
            'instructors': instructors,
            'opts': self.model._meta,
            'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
        }
        return TemplateResponse(request, 'admin/courses/course/set_instructor.html', context)

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
from .statistics import course_stats


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    can_delete = False
    readonly_fields = ('student', 'status', 'is_active', 'created_at')
    fields = ('student', 'status', 'is_active', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Course Admin with Introduction/Auto-Enrollment Management"""

    # ── List View ─────────────────────────────────────────────
    list_display = (
        'course_code',
        'title',
        'instructor_link',
        'status_badge',
        'enrollment_info',
        'is_introduction',
        'is_auto_enrolled',
        'categories_list',
        'is_active',
        'created_at',
    )

    list_filter = (
        'is_introduction',
        'is_auto_enrolled',
        'status',
        'is_active',
        'categories',
        'created_at',
    )

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
    readonly_fields = (
        'created_at',
        'updated_at',
        'enrollment_stats',
        'display_average_enrollment',
        'display_top_courses',
    )
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
            _('Auto-Enrollment'),
            {
                'description': _(
                    'Introduction Course: Tag for beginner/intro courses (organization only). '
                    'Auto-Enroll: Automatically enroll new students when they verify email. '
                    'Note: Auto-enrollment only works for Active courses.'
                ),
                'fields': ('is_introduction', 'is_auto_enrolled'),
            },
        ),
        (
            _('Enrollment Details'),
            {
                'classes': ('collapse',),
                'fields': ('enrollment_stats',),
            },
        ),
        (
            _('Statistics'),
            {
                'fields': ('display_average_enrollment', 'display_top_courses'),
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
        'enable_introduction',
        'disable_introduction',
        'enable_auto_enrollment',
        'disable_auto_enrollment',
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
    # Display Helpers
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

    @admin.display(description=_('Average Enrollment'))
    def display_average_enrollment(self, obj):
        stats = course_stats.get_average_enrollments()
        return format_html(
            '{:.2f} avg ({} courses, {} enrollments)',
            stats['average'],
            stats['total_courses'],
            stats['total_enrollments'],
        )

    @admin.display(description=_('Top 5 Courses'))
    def display_top_courses(self, obj):
        top_courses = course_stats.get_top_courses(limit=5)
        if not top_courses:
            return '—'

        items = []
        for course in top_courses:
            count = getattr(course, 'enrollment_count', 0)
            items.append(f'{course.title} ({count})')

        return format_html('<br>'.join(items))

    # ─────────────────────────────────────────────────────────
    # Save Validation
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

        # Warn about auto-enrollment on inactive courses
        if obj.is_auto_enrolled and (not obj.is_active or obj.status != Course.STATUS_ACTIVE):
            messages.warning(
                request,
                _(
                    'Auto-enrollment enabled but course is not Active. Auto-enrollment will not work until course is activated.'
                ),
            )

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

    # ─────────────────────────────────────────────────────────
    # Introduction/Auto-Enrollment Actions
    # ─────────────────────────────────────────────────────────

    @admin.action(description=_('Mark as Introduction Course'))
    def enable_introduction(self, request, queryset):
        updated = queryset.update(is_introduction=True)
        self.message_user(
            request,
            _('{count} course(s) marked as Introduction.').format(count=updated),
            messages.SUCCESS,
        )

    @admin.action(description=_('Remove Introduction Tag'))
    def disable_introduction(self, request, queryset):
        updated = queryset.update(is_introduction=False)
        self.message_user(
            request,
            _('{count} course(s) no longer marked as Introduction.').format(count=updated),
            messages.SUCCESS,
        )

    @admin.action(description=_('Enable Auto-Enrollment'))
    def enable_auto_enrollment(self, request, queryset):
        inactive = queryset.filter(Q(is_active=False) | ~Q(status=Course.STATUS_ACTIVE))

        if inactive.exists():
            self.message_user(
                request,
                _(
                    '{count} course(s) are not Active. Auto-enrollment will only work when courses are Active.'
                ).format(count=inactive.count()),
                messages.WARNING,
            )

        updated = queryset.update(is_auto_enrolled=True)
        self.message_user(
            request,
            _('Auto-enrollment enabled for {count} course(s).').format(count=updated),
            messages.SUCCESS,
        )

    @admin.action(description=_('Disable Auto-Enrollment'))
    def disable_auto_enrollment(self, request, queryset):
        updated = queryset.update(is_auto_enrolled=False)
        self.message_user(
            request,
            _('Auto-enrollment disabled for {count} course(s).').format(count=updated),
            messages.SUCCESS,
        )

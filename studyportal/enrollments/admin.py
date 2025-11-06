from django.contrib import admin
from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "enrolled_at", "is_active")
    list_filter = ("course", "is_active")
    search_fields = ("user__username", "course__title")
    actions = ["soft_delete_enrollments"]

    # Disable Add & Edit from admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # prevents editing record

    # Still allow soft delete action
    def soft_delete_enrollments(self, request, queryset):
        queryset.update(is_active=False)

    soft_delete_enrollments.short_description = "Soft delete selected enrollments"

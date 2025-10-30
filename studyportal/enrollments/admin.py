from django.contrib import admin
from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "enrolled_at", "is_deleted")
    list_filter = ("course", "is_deleted")
    search_fields = ("user__username", "course__title")
    actions = ["soft_delete_enrollments"]

    def soft_delete_enrollments(self, request, queryset):
        queryset.update(is_deleted=True)

    soft_delete_enrollments.short_description = "Soft delete selected enrollments"

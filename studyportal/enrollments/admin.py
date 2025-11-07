from django.contrib import admin
from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "enrolled_at", "is_active")
    list_filter = ("course", "is_active")
    search_fields = ("user__username", "course__title")

    # No actions (admin cannot soft delete)
    actions = None

    # Disable add & edit
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    # Disable delete
    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        # Ensure delete_selected doesn't appear
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

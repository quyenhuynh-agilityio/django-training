from django.contrib import admin
from .models import Course


# Register the Course model in Django Admin
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    # Fields to display in the admin list view
    list_display = ("title", "category", "is_active", "is_deleted", "created_at")

    # Filters on the right side panel
    list_filter = ("category", "is_active", "is_deleted")

    # Searchable fields (top search bar)
    search_fields = ("title", "category")

    # Pagination: number of items per page
    list_per_page = 20

    # Custom admin actions available in bulk action dropdown
    actions = ["soft_delete_courses"]

    # Action: Soft delete selected courses (instead of permanent delete)
    def soft_delete_courses(self, request, queryset):
        # Update selected records setting is_deleted = True
        queryset.update(is_deleted=True)

    # Action label shown in admin UI
    soft_delete_courses.short_description = "Soft delete selected courses"

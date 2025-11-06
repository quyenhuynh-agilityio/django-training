from django.contrib import admin
from .models import Course, Category


# Register the Category model in Django Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    list_per_page = 20


# Register the Course model in Django Admin
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    # Fields to display in the admin list view
    list_display = ("title", "get_categories", "is_active", "is_deleted", "created_at")
    filter_horizontal = ("categories",)  # Better UI for many-to-many selection

    # Filters on the right side panel
    list_filter = ("categories", "is_active", "is_deleted")

    # Searchable fields (top search bar)
    search_fields = ("title", "categories__name")

    def get_categories(self, obj):
        """Display categories as comma-separated string."""
        return ", ".join([cat.name for cat in obj.categories.all()])

    get_categories.short_description = "Categories"

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

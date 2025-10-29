from django.contrib import admin
from .models import Course  

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_active', 'is_deleted', 'created_at')
    list_filter = ('category', 'is_active', 'is_deleted')
    search_fields = ('title', 'category')
    actions = ['soft_delete_courses']

    def soft_delete_courses(self, request, queryset):
        queryset.update(is_deleted=True)
    soft_delete_courses.short_description = "Soft delete selected courses"

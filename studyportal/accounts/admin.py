from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model

User = get_user_model()  # Use your custom User model

# ====== User Admin ======
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_deleted')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_deleted', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    filter_horizontal = ('groups', 'user_permissions')

    actions = ['soft_delete_users']

    def soft_delete_users(self, request, queryset):
        queryset.update(is_deleted=True, is_active=False)
    soft_delete_users.short_description = "Soft delete selected users"

# ====== Group Admin ======
admin.site.unregister(Group)
@admin.register(Group)
class CustomGroupAdmin(BaseGroupAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('permissions',)

# ====== Permission Admin ======
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'codename', 'content_type')
    search_fields = ('name', 'codename')

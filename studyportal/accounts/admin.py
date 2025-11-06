# accounts/admin.py
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import (
    UserAdmin as BaseUserAdmin,
    GroupAdmin as BaseGroupAdmin,
)
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

User = get_user_model()


# ---------------------------
# Custom add form (uses UserCreationForm)
# ---------------------------
class CustomUserCreationForm(UserCreationForm):
    # Make first_name and last_name required on add
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")


# ---------------------------
# Custom change form (uses UserChangeForm)
# ---------------------------
class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        # Use all fields from the user model for change form
        fields = "__all__"

    def clean_first_name(self):
        val = self.cleaned_data.get("first_name")
        if not val or not val.strip():
            raise forms.ValidationError("First name is required.")
        return val.strip()

    def clean_last_name(self):
        val = self.cleaned_data.get("last_name")
        if not val or not val.strip():
            raise forms.ValidationError("Last name is required.")
        return val.strip()


# ---------------------------
# User admin
# ---------------------------
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "last_login",
        "date_joined",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "email", "first_name", "last_name")
    filter_horizontal = ("groups", "user_permissions")

    # Make last_login & date_joined read-only
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "email")}),
        ("Status", {"fields": ("is_active",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                # password1 and password2 belong to UserCreationForm (add_form)
                "fields": (
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    actions = ["deactivate_users"]

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)

    deactivate_users.short_description = "Deactivate selected users"


# ---------------------------
# Group admin (keep default behavior but re-register)
# ---------------------------
admin.site.unregister(Group)


@admin.register(Group)
class CustomGroupAdmin(BaseGroupAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    filter_horizontal = ("permissions",)


# ---------------------------
# Permission admin
# ---------------------------
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("name", "codename", "content_type")
    search_fields = ("name", "codename")

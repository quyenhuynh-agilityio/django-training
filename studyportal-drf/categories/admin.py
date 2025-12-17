from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from utils.admin.badges import badge

from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Category Admin Configuration

    Consistent with Course admin category badges.
    Clean, readable, and fast.
    """

    list_display = (
        'id',
        'name_badge',
        'is_active',
        'created_at',
    )

    list_filter = ('is_active',)

    search_fields = ('name',)

    ordering = ('name',)

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    fieldsets = (
        (
            _('Category Information'),
            {
                'fields': ('name', 'is_active'),
            },
        ),
        (
            _('Timestamps'),
            {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',),
            },
        ),
    )

    list_per_page = 25

    # ───────────────────────────────────────────────────────────
    # Display helpers
    # ───────────────────────────────────────────────────────────

    @admin.display(description=_('Category'))
    def name_badge(self, obj):
        return badge(obj.name, '#17a2b8')

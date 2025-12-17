from django.urls import reverse
from django.utils.html import format_html


def admin_link(obj, *, admin_url, label=None, bold=True):
    """
    Generate a clickable link to an admin change page.

    Usage:
        admin_link(obj.instructor, admin_url='admin:users_user_change')
    """
    if not obj:
        return '—'

    url = reverse(admin_url, args=[obj.pk])
    text = label or str(obj)

    style = 'font-weight:500;' if bold else ''

    return format_html('<a href="{}" style="{}">{}</a>', url, style, text)

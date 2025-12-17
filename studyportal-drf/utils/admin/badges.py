from django.utils.html import format_html


def badge(label, color, *, font_size='12px', padding='3px 10px'):
    """
    Generic badge renderer for Django admin.

    Usage:
        badge('Active', '#28a745')
    """
    return format_html(
        '<span style="background-color:{}; color:white; '
        'padding:{}; border-radius:4px; '
        'font-size:{}; font-weight:500; display:inline-block;">{}</span>',
        color,
        padding,
        font_size,
        label,
    )


def status_badge(label, status, color_map):
    """
    Render status badge based on a color map.

    Usage:
        status_badge(obj.get_status_display(), obj.status, COLORS)
    """
    color = color_map.get(status, '#6c757d')
    return badge(label, color)


def inactive_badge(label='Inactive'):
    return badge(label, '#6c757d')

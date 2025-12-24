from rest_framework.permissions import AllowAny


def is_active_authenticated(user):
    """Return True if the user is authenticated and active."""
    return bool(
        user and getattr(user, 'is_authenticated', False) and getattr(user, 'is_active', False)
    )


def permissions_for_action(*, action, permission_classes_map, default_permissions):
    """
    Return instantiated permission classes based on ViewSet action.

    Args:
        action: Current ViewSet action (e.g. 'list', 'create')
        permission_classes_map: Mapping of action → permission classes
        default_permissions: Fallback permission classes

    Returns:
        List of permission instances
    """
    default_permissions = default_permissions or [AllowAny]

    permission_classes = permission_classes_map.get(action, default_permissions)
    return [permission() for permission in permission_classes]

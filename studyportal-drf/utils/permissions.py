def is_active_authenticated(user):
    """Return True if the user is authenticated and active."""
    return bool(
        user and getattr(user, 'is_authenticated', False) and getattr(user, 'is_active', False)
    )

def get_audit_read_only_fields(*extra_fields, include_updated=True):
    """
    Return tuple of audit fields to mark as read-only.

    Examples:
        read_only_fields = get_audit_read_only_fields()
        # ('id', 'created_at', 'updated_at')

        read_only_fields = get_audit_read_only_fields('student', 'course')
        # ('id', 'created_at', 'updated_at', 'student', 'course')
    """
    base = ['id', 'created_at']
    if include_updated:
        base.append('updated_at')
    if extra_fields:
        base.extend(extra_fields)
    return tuple(base)

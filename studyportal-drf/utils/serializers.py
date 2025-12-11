"""
Shared serializer helpers used across API modules.
"""

from rest_framework import serializers


class AuditReadOnlyFieldsMixin(serializers.Serializer):
    """
    Mixin providing common read-only audit fields.

    Usage:
        class Meta:
            read_only_fields = AuditReadOnlyFieldsMixin.audit_fields()

    Avoids repeating (`id`, `created_at`, `updated_at`) in every serializer.
    """

    audit_read_only_fields = ('id', 'created_at', 'updated_at')

    @classmethod
    def audit_fields(cls, *extra_fields, include_updated=True):
        """
        Return tuple of default audit fields plus optional extras.

        Args:
            *extra_fields: Additional field names to set as read-only.
            include_updated: When False, omit `updated_at`.
        """
        base = ['id', 'created_at']
        if include_updated:
            base.append('updated_at')
        if extra_fields:
            base.extend(extra_fields)
        return tuple(base)

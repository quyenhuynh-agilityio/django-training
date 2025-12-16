"""
Shared serializer utilities used across API modules.

Provides reusable base classes and helper functions for common patterns.
"""

from rest_framework import serializers


class AuditFieldsBase(serializers.Serializer):
    """
    Base class providing common read-only audit fields.

    This is NOT a DRF mixin - it's a base class for sharing fields.

    Automatically includes: id, created_at, updated_at as read-only.

    Usage:
        # Option 1: Inherit from this base class
        class MySerializer(AuditFieldsBase, serializers.ModelSerializer):
            class Meta:
                model = MyModel
                fields = ['field1', 'field2', 'id', 'created_at', 'updated_at']
                # id, created_at, updated_at are automatically read-only

        # Option 2: Use the helper function
        class MySerializer(serializers.ModelSerializer):
            class Meta:
                model = MyModel
                fields = ['field1', 'field2']
                read_only_fields = audit_read_only_fields()
    """

    # These fields are defined but will be provided by the model
    # DRF automatically handles them as read-only when in read_only_fields

    @classmethod
    def get_read_only_fields(cls, *extra_fields, include_updated=True):
        """
        Return tuple of default audit fields plus optional extras.

        Args:
            *extra_fields: Additional field names to set as read-only
            include_updated: When False, omit `updated_at`

        Returns:
            Tuple of field names to mark as read-only

        Examples:
            # Basic usage - id, created_at, updated_at
            read_only_fields = AuditFieldsBase.get_read_only_fields()

            # Without updated_at
            read_only_fields = AuditFieldsBase.get_read_only_fields(include_updated=False)

            # With extra fields
            read_only_fields = AuditFieldsBase.get_read_only_fields('student', 'course')
        """
        base = ['id', 'created_at']
        if include_updated:
            base.append('updated_at')
        if extra_fields:
            base.extend(extra_fields)
        return tuple(base)


# Convenience function for backward compatibility
def audit_read_only_fields(*extra_fields, include_updated=True):
    """
    Helper function to get audit read-only fields.

    This is a convenience wrapper around AuditFieldsBase.get_read_only_fields()

    Args:
        *extra_fields: Additional field names to set as read-only
        include_updated: When False, omit `updated_at`

    Returns:
        Tuple of field names to mark as read-only

    Usage:
        class MySerializer(serializers.ModelSerializer):
            class Meta:
                model = MyModel
                fields = ['field1', 'field2', 'id', 'created_at', 'updated_at']
                read_only_fields = audit_read_only_fields()

        # With extra fields
        class EnrollmentSerializer(serializers.ModelSerializer):
            class Meta:
                model = Enrollment
                fields = ['id', 'student', 'course', 'created_at', 'updated_at']
                read_only_fields = audit_read_only_fields('student')
    """
    return AuditFieldsBase.get_read_only_fields(*extra_fields, include_updated=include_updated)


__all__ = [
    'AuditFieldsBase',
    'audit_read_only_fields',
]

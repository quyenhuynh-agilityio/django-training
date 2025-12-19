"""Serializer utilities for API case conversion.

Naming convention:
- Python/Django: snake_case
- JSON (JS clients): camelCase

This module provides a serializer mixin to automatically translate between the two.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from rest_framework import serializers

# Regex patterns for camelCase to snake_case conversion
_CAMEL_PATTERN_1 = re.compile(r'(.)([A-Z][a-z]+)')
_CAMEL_PATTERN_2 = re.compile(r'([a-z0-9])([A-Z])')


def snake_to_camel(name):
    """Convert snake_case string to camelCase.

    Examples:
        >>> snake_to_camel('first_name')
        'firstName'
        >>> snake_to_camel('date_of_birth')
        'dateOfBirth'
        >>> snake_to_camel('id')
        'id'
    """
    if not name or '_' not in name:
        return name

    parts = name.split('_')
    # Keep first part lowercase, capitalize rest
    return parts[0] + ''.join(part.capitalize() for part in parts[1:] if part)


def camel_to_snake(name):
    """Convert camelCase/PascalCase string to snake_case.

    Examples:
        >>> camel_to_snake('firstName')
        'first_name'
        >>> camel_to_snake('dateOfBirth')
        'date_of_birth'
        >>> camel_to_snake('HTTPResponse')
        'http_response'
    """
    if not name:
        return name

    # Insert underscore before uppercase letters
    name = _CAMEL_PATTERN_1.sub(r'\1_\2', name)
    name = _CAMEL_PATTERN_2.sub(r'\1_\2', name)
    return name.lower()


def transform_keys(data, key_transformer):
    """Recursively transform keys in nested data structures.

    Args:
        data: Data structure (dict, list, or primitive)
        key_transformer: Function to transform string keys

    Examples:
        >>> data = {'user_name': 'John', 'user_age': 30}
        >>> transform_keys(data, snake_to_camel)
        {'userName': 'John', 'userAge': 30}
    """
    if isinstance(data, list):
        return [transform_keys(item, key_transformer) for item in data]

    if isinstance(data, Mapping):
        return {
            key_transformer(key) if isinstance(key, str) else key: transform_keys(
                value, key_transformer
            )
            for key, value in data.items()
        }

    return data


class CamelCaseSerializerMixin:
    """Mixin to automatically convert between snake_case and camelCase.

    Provides automatic field name translation:
    - Incoming JSON (camelCase) → Python (snake_case) before validation
    - Outgoing Python (snake_case) → JSON (camelCase) in responses

    Usage:
        class UserSerializer(CamelCaseSerializerMixin, serializers.ModelSerializer):
            class Meta:
                model = User
                fields = ['id', 'first_name', 'last_name', 'email']

        # API will accept/return:
        # {"id": 1, "firstName": "John", "lastName": "Doe", "email": "john@example.com"}

    Note:
        Add this mixin as the *first* base class so method overrides take precedence.
    """

    def to_representation(self, instance):
        """Convert outgoing data from snake_case to camelCase."""
        data = super().to_representation(instance)
        return transform_keys(data, snake_to_camel)

    def to_internal_value(self, data):
        """Convert incoming data from camelCase to snake_case."""
        snake_case_data = transform_keys(data, camel_to_snake)
        return super().to_internal_value(snake_case_data)


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
    'CamelCaseSerializerMixin',
    'camel_to_snake',
    'snake_to_camel',
    'AuditFieldsBase',
    'audit_read_only_fields',
]

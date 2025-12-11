"""
User Profile Serializers

Serializers for user profile operations:
- User profile retrieval and update
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from utils.serializers import AuditReadOnlyFieldsMixin

User = get_user_model()


class UserProfileSerializer(AuditReadOnlyFieldsMixin, serializers.ModelSerializer):
    """
    Returns full user profile details.

    All fields are read-only to avoid unintended data exposure.
    """

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'is_active',
            'date_joined',
            'created_at',
        ]
        read_only_fields = AuditReadOnlyFieldsMixin.audit_fields(
            'email',
            'username',
            'role',
            'is_active',
            'date_joined',
            include_updated=False,
        )

"""
Category Serializers

Provides serialization for Category model with proper audit field handling.
"""

from rest_framework import serializers

from categories.models import Category
from core.texts import ErrorMessage


class CategorySerializer(serializers.ModelSerializer):
    """
    Category Serializer

    Read-only serializer for listing and retrieving categories.
    All fields are read-only since this is used with ReadOnlyModelViewSet.

    Validations:
    ------------
    - name: required, max 100 chars, unique
    - is_active: optional, defaults to True
    """

    class Meta:
        model = Category
        fields = ['id', 'name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'name': {
                'required': True,
                'allow_blank': False,
                'max_length': 100,
            }
        }

    def validate_name(self, value):
        """
        Validate category name:
        - Strip whitespace
        - Ensure not empty
        - Check uniqueness (excluding current instance on update)
        """
        value = value.strip()

        if not value:
            raise serializers.ValidationError(ErrorMessage.CATEGORY_NAME_EMPTY)

        # Check uniqueness
        queryset = Category.objects.filter(name__iexact=value)

        # Exclude current instance during update
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(ErrorMessage.CATEGORY_NAME_ALREADY_EXISTS)

        return value

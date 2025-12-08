from rest_framework import serializers

from categories.models import Category


class CategorySerializer(serializers.ModelSerializer):
    """
    Category Serializer

    Fields:
    - id: UUID
    - name: Category name
    - description: Category description
    - is_active: Active status
    """

    class Meta:
        model = Category
        fields = ['id', 'name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

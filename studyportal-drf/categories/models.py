import uuid

from django.db import models

from core.texts import HelpText


class Category(models.Model):
    """
    Simple category system to organize courses.
    Required for: Course filtering by category (mobile + web).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,  # Fast filtering in course list
        help_text=HelpText.CATEGORY_NAME,
    )

    is_active = models.BooleanField(
        default=True, db_index=True, help_text=HelpText.CATEGORY_IS_ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

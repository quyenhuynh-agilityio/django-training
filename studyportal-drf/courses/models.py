# Create your models here.
import uuid

from django.db import models

from categories.models import Category


class Course(models.Model):
    """
    Course model for the training platform.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    course_code = models.CharField(max_length=20)
    description = models.TextField()
    categories = models.ManyToManyField(Category, related_name='courses', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

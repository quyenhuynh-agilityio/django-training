import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # Use UUID as the primary key instead of auto-increment integer
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,  # automatically generate UUID
        editable=False,  # prevent editing in admin or code
    )

    # Soft-delete flag (instead of removing user permanently from DB)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        # Custom table name in database instead of default "auth_user"
        db_table = "user"

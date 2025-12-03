from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.

    You can add custom fields here as needed.
    """

    # Add custom fields here if needed
    # For example:
    # phone_number = models.CharField(max_length=20, blank=True)
    # profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

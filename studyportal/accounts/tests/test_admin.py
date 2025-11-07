# accounts/tests/test_admin.py
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from accounts.admin import UserAdmin, CustomUserCreationForm, CustomUserChangeForm

User = get_user_model()


class DummyRequest:
    pass


class UserAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.user1 = User.objects.create_user(
            username="u1", email="u1@example.com", password="p"
        )
        self.user2 = User.objects.create_user(
            username="u2", email="u2@example.com", password="p"
        )
        self.admin = UserAdmin(User, self.site)

    def test_deactivate_users_action(self):
        # Ensure action flips is_active to False for selected users
        queryset = User.objects.filter(id__in=[self.user1.id, self.user2.id])
        # call admin action
        request = DummyRequest()
        self.admin.deactivate_users(request, queryset)
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.assertFalse(self.user1.is_active)
        self.assertFalse(self.user2.is_active)

    def test_custom_forms_exist(self):
        # basic sanity: forms instantiate
        add_form = CustomUserCreationForm()
        change_form = CustomUserChangeForm()
        self.assertIsNotNone(add_form)
        self.assertIsNotNone(change_form)

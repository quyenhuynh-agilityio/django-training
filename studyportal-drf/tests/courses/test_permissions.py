from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from courses.api.permissions import IsCourseInstructor, IsInstructor, IsStudent

User = get_user_model()


class IsInstructorPermissionTest(TestCase):
    """Test IsInstructor permission class"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsInstructor()
        self.view = Mock()

    def test_authenticated_instructor_has_permission(self):
        """Authenticated instructor should have permission"""
        user = Mock(is_authenticated=True, is_instructor=True)
        request = self.factory.get('/')
        request.user = user

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_authenticated_non_instructor_denied(self):
        """Authenticated non-instructor should be denied"""
        user = Mock(is_authenticated=True, is_instructor=False)
        request = self.factory.get('/')
        request.user = user

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_unauthenticated_user_denied(self):
        """Unauthenticated user should be denied"""
        user = Mock(is_authenticated=False, is_instructor=False)
        request = self.factory.get('/')
        request.user = user

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_unauthenticated_instructor_flag_denied(self):
        """Unauthenticated user with instructor flag should still be denied"""
        user = Mock(is_authenticated=False, is_instructor=True)
        request = self.factory.get('/')
        request.user = user

        self.assertFalse(self.permission.has_permission(request, self.view))


class IsCourseInstructorPermissionTest(TestCase):
    """Test IsCourseInstructor permission class"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsCourseInstructor()
        self.view = Mock()

    def test_view_level_authenticated_instructor_has_permission(self):
        """Authenticated instructor should pass view-level check"""
        user = Mock(is_authenticated=True, is_instructor=True)
        request = self.factory.get('/')
        request.user = user

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_view_level_authenticated_non_instructor_denied(self):
        """Authenticated non-instructor should fail view-level check"""
        user = Mock(is_authenticated=True, is_instructor=False)
        request = self.factory.get('/')
        request.user = user

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_view_level_unauthenticated_denied(self):
        """Unauthenticated user should fail view-level check"""
        user = Mock(is_authenticated=False, is_instructor=False)
        request = self.factory.get('/')
        request.user = user

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_object_level_course_owner_has_permission(self):
        """Course owner should have object-level permission"""
        user = Mock(is_authenticated=True, is_instructor=True, is_staff=False)
        request = self.factory.get('/')
        request.user = user

        course = Mock(instructor=user)

        self.assertTrue(self.permission.has_object_permission(request, self.view, course))

    def test_object_level_different_instructor_denied(self):
        """Different instructor should be denied object-level permission"""
        user = Mock(is_authenticated=True, is_instructor=True, is_staff=False)
        other_user = Mock(is_authenticated=True, is_instructor=True)
        request = self.factory.get('/')
        request.user = user

        course = Mock(instructor=other_user)

        self.assertFalse(self.permission.has_object_permission(request, self.view, course))

    def test_object_level_staff_has_permission(self):
        """Staff user should have object-level permission regardless of ownership"""
        user = Mock(is_authenticated=True, is_instructor=True, is_staff=True)
        other_user = Mock(is_authenticated=True, is_instructor=True)
        request = self.factory.get('/')
        request.user = user

        course = Mock(instructor=other_user)

        self.assertTrue(self.permission.has_object_permission(request, self.view, course))

    def test_object_level_staff_non_instructor_has_permission(self):
        """Staff user should have permission even if not flagged as instructor"""
        user = Mock(is_authenticated=True, is_instructor=False, is_staff=True)
        other_user = Mock(is_authenticated=True, is_instructor=True)
        request = self.factory.get('/')
        request.user = user

        course = Mock(instructor=other_user)

        self.assertTrue(self.permission.has_object_permission(request, self.view, course))


class IsStudentPermissionTest(TestCase):
    """Test IsStudent permission class"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsStudent()
        self.view = Mock()

    def test_authenticated_student_has_permission(self):
        """Authenticated student should have permission"""
        user = Mock(is_authenticated=True, is_student=True)
        request = self.factory.get('/')
        request.user = user

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_authenticated_non_student_denied(self):
        """Authenticated non-student should be denied"""
        user = Mock(is_authenticated=True, is_student=False)
        request = self.factory.get('/')
        request.user = user

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_unauthenticated_user_denied(self):
        """Unauthenticated user should be denied"""
        user = Mock(is_authenticated=False, is_student=False)
        request = self.factory.get('/')
        request.user = user

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_unauthenticated_student_flag_denied(self):
        """Unauthenticated user with student flag should still be denied"""
        user = Mock(is_authenticated=False, is_student=True)
        request = self.factory.get('/')
        request.user = user

        self.assertFalse(self.permission.has_permission(request, self.view))

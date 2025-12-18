import pytest

from rest_framework import serializers

from users.api.bases import (
    EmailNormalizationBase,
    NameValidationBase,
    PasswordConfirmationBase,
    ResetTokenValidationBase,
)

pytestmark = pytest.mark.django_db


class TestEmailNormalizationBase:
    """Test EmailNormalizationBase functionality"""

    def test_normalize_email_lowercase(self):
        """Test that email is normalized to lowercase"""
        base = EmailNormalizationBase()
        assert base.normalize_email('Test@Example.COM') == 'test@example.com'

    def test_normalize_email_strips_whitespace(self):
        """Test that email whitespace is stripped"""
        base = EmailNormalizationBase()
        assert base.normalize_email('  test@example.com  ') == 'test@example.com'

    def test_normalize_email_empty_returns_empty(self):
        """Test that empty email returns empty"""
        base = EmailNormalizationBase()
        assert base.normalize_email('') == ''
        assert base.normalize_email(None) is None


class TestNameValidationBase:
    """Test NameValidationBase functionality"""

    def test_validate_name_empty(self):
        """Test that empty name is rejected"""
        base = NameValidationBase()
        with pytest.raises(serializers.ValidationError):
            base.validate_name('', 'First name')

    def test_validate_name_whitespace_only(self):
        """Test that whitespace-only name is rejected"""
        base = NameValidationBase()
        with pytest.raises(serializers.ValidationError):
            base.validate_name('   ', 'First name')

    def test_validate_name_invalid_characters(self):
        """Test that names with invalid characters are rejected"""
        base = NameValidationBase()
        with pytest.raises(serializers.ValidationError):
            base.validate_name('John123', 'First name')
        with pytest.raises(serializers.ValidationError):
            base.validate_name('John@Doe', 'First name')

    def test_validate_name_valid_with_hyphen(self):
        """Test that names with hyphens are accepted"""
        base = NameValidationBase()
        result = base.validate_name('Mary-Jane', 'First name')
        assert result == 'Mary-Jane'

    def test_validate_name_valid_with_apostrophe(self):
        """Test that names with apostrophes are accepted"""
        base = NameValidationBase()
        result = base.validate_name("O'Connor", 'Last name')
        assert result == "O'Connor"

    def test_validate_name_capitalizes_properly(self):
        """Test that names are properly capitalized"""
        base = NameValidationBase()
        result = base.validate_name('mary-jane smith', 'Full name')
        assert result == 'Mary-Jane Smith'

    def test_validate_name_strips_whitespace(self):
        """Test that name whitespace is stripped"""
        base = NameValidationBase()
        result = base.validate_name('  John  ', 'First name')
        assert result == 'John'


class TestPasswordConfirmationBase:
    """Test PasswordConfirmationBase functionality"""

    def test_check_password_match_success(self):
        """Test that matching passwords pass validation"""
        base = PasswordConfirmationBase()
        # Should not raise
        base.check_password_match('password123', 'password123')

    def test_check_password_match_failure(self):
        """Test that mismatched passwords raise ValidationError"""
        base = PasswordConfirmationBase()
        with pytest.raises(serializers.ValidationError) as exc_info:
            base.check_password_match('password123', 'different')
        assert 'password_confirm' in exc_info.value.detail
        error_message = exc_info.value.detail['password_confirm']
        assert 'Passwords do not match' in str(error_message)


class TestResetTokenValidationBase:
    """Test ResetTokenValidationBase functionality"""

    def test_validate_reset_token_invalid_uid(self, create_user):
        """Test that invalid UID raises ValidationError"""
        base = ResetTokenValidationBase()
        with pytest.raises(serializers.ValidationError) as exc_info:
            base.validate_reset_token('invalid-uid', 'some-token')
        assert 'uid' in exc_info.value.detail

    def test_validate_reset_token_invalid_token(self, create_user):
        """Test that invalid token raises ValidationError"""
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        user = create_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        base = ResetTokenValidationBase()
        with pytest.raises(serializers.ValidationError) as exc_info:
            base.validate_reset_token(uid, 'invalid-token')
        assert 'token' in exc_info.value.detail

    def test_validate_reset_token_inactive_user(self, create_user):
        """Test that inactive user raises ValidationError"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        user = create_user(is_active=False)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        base = ResetTokenValidationBase()
        with pytest.raises(serializers.ValidationError) as exc_info:
            base.validate_reset_token(uid, token)
        assert 'detail' in exc_info.value.detail

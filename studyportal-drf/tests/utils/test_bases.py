import pytest

from rest_framework import serializers

from utils.validators import (
    normalize_email,
    validate_name,
    validate_password_confirmation,
    validate_reset_token,
)

pytestmark = pytest.mark.django_db


class TestNormalizeEmail:
    """Tests for normalize_email utility function"""

    def test_lowercase_email(self):
        assert normalize_email('Test@Example.COM') == 'test@example.com'

    def test_strip_whitespace(self):
        assert normalize_email('  test@example.com  ') == 'test@example.com'

    def test_empty_string(self):
        assert normalize_email('') == ''

    def test_none_value(self):
        assert normalize_email(None) is None


class TestValidateName:
    """Tests for validate_name utility function"""

    def test_empty_name(self):
        with pytest.raises(serializers.ValidationError):
            validate_name('', 'First name')

    def test_whitespace_only(self):
        with pytest.raises(serializers.ValidationError):
            validate_name('   ', 'First name')

    def test_invalid_characters(self):
        with pytest.raises(serializers.ValidationError):
            validate_name('John123', 'First name')

        with pytest.raises(serializers.ValidationError):
            validate_name('John@Doe', 'First name')

    def test_valid_name_simple(self):
        assert validate_name('John', 'First name') == 'John'

    def test_valid_name_with_hyphen(self):
        assert validate_name('Mary-Jane', 'First name') == 'Mary-Jane'

    def test_valid_name_with_apostrophe(self):
        assert validate_name("O'Connor", 'Last name') == "O'Connor"

    def test_capitalization(self):
        assert validate_name('mary-jane smith', 'Full name') == 'Mary-Jane Smith'

    def test_strip_whitespace(self):
        assert validate_name('  John  ', 'First name') == 'John'


class TestCheckPasswordMatch:
    """Tests for check_password_match utility function"""

    def test_passwords_match(self):
        # Should not raise
        validate_password_confirmation('password123', 'password123')

    def test_passwords_do_not_match(self):
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_password_confirmation('password123', 'different')

        assert 'password_confirm' in exc_info.value.detail


class TestValidateResetToken:
    """Tests for validate_reset_token utility function"""

    def test_invalid_uid(self):
        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_reset_token('invalid-uid', 'some-token')

        assert 'uid' in exc_info.value.detail

    def test_invalid_token(self, create_user):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        user = create_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_reset_token(uid, 'invalid-token')

        assert 'token' in exc_info.value.detail

    def test_inactive_user(self, create_user):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        user = create_user(is_active=False)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        with pytest.raises(serializers.ValidationError) as exc_info:
            validate_reset_token(uid, token)

        assert 'detail' in exc_info.value.detail

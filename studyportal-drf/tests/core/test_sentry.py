"""Tests for core.sentry module."""

from unittest.mock import MagicMock, patch

import pytest

from core.sentry import (
    sentry_add_breadcrumb,
    sentry_capture_exception,
    sentry_capture_message,
    sentry_scope,
)


class TestSentryScope:
    @patch('core.sentry.sentry_sdk')
    def test_sentry_scope_sets_tags(self, mock_sentry):
        mock_scope = MagicMock()
        mock_sentry.new_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_sentry.new_scope.return_value.__exit__ = MagicMock(return_value=None)

        with sentry_scope(tags={'key': 'value'}):
            pass

        mock_scope.set_tag.assert_called()

    @patch('core.sentry.sentry_sdk')
    def test_sentry_scope_skips_none_tags(self, mock_sentry):
        mock_scope = MagicMock()
        mock_sentry.new_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_sentry.new_scope.return_value.__exit__ = MagicMock(return_value=None)

        with sentry_scope(tags={'a': 1, 'b': None}):
            pass

        assert mock_scope.set_tag.call_count == 1

    @patch('core.sentry.sentry_sdk')
    def test_sentry_scope_sets_contexts(self, mock_sentry):
        mock_scope = MagicMock()
        mock_sentry.new_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_sentry.new_scope.return_value.__exit__ = MagicMock(return_value=None)

        with sentry_scope(contexts={'task_data': {'id': '123'}}):
            pass

        mock_scope.set_context.assert_called_once_with('task_data', {'id': '123'})

    @patch('core.sentry.sentry_sdk')
    def test_sentry_scope_sets_user(self, mock_sentry):
        mock_scope = MagicMock()
        mock_sentry.new_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_sentry.new_scope.return_value.__exit__ = MagicMock(return_value=None)

        with sentry_scope(user={'id': 'user-1', 'email': 'u@example.com'}):
            pass

        mock_scope.set_user.assert_called_once()


class TestSentryCaptureException:
    @patch('core.sentry.sentry_sdk')
    def test_capture_exception_calls_sdk(self, mock_sentry):
        exc = ValueError('test')
        sentry_capture_exception(exc)
        mock_sentry.capture_exception.assert_called_once_with(exc)


class TestSentryCaptureMessage:
    @patch('core.sentry.sentry_sdk')
    def test_capture_message_default_level(self, mock_sentry):
        sentry_capture_message('Something failed')
        mock_sentry.capture_message.assert_called_once_with('Something failed', level='error')

    @patch('core.sentry.sentry_sdk')
    def test_capture_message_with_extra(self, mock_sentry):
        sentry_capture_message('Msg', extra={'key': 'value'})
        mock_sentry.set_extra.assert_called()
        mock_sentry.capture_message.assert_called_once()


class TestSentryAddBreadcrumb:
    @patch('core.sentry.sentry_sdk')
    def test_add_breadcrumb(self, mock_sentry):
        sentry_add_breadcrumb(category='auth', message='User logged in')
        mock_sentry.add_breadcrumb.assert_called_once()
        call_kw = mock_sentry.add_breadcrumb.call_args[1]
        assert call_kw['category'] == 'auth'
        assert call_kw['message'] == 'User logged in'
        assert call_kw['level'] == 'info'

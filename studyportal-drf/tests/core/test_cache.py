"""Tests for core.cache module."""

from unittest.mock import MagicMock, patch

import pytest

from core.cache import (
    build_cache_key,
    cache_get_or_set,
    delete_cache_with_prefix,
    get_timeout,
)


class TestGetTimeout:
    def test_returns_setting_when_present(self, settings):
        settings.MY_CACHE_TIMEOUT = 120
        assert get_timeout('MY_CACHE_TIMEOUT', 60) == 120

    def test_returns_default_when_setting_missing(self, settings):
        assert get_timeout('MISSING_TIMEOUT', 60) == 60

    def test_casts_to_int(self, settings):
        settings.SOME_TIMEOUT = '90'
        assert get_timeout('SOME_TIMEOUT', 30) == 90


class TestBuildCacheKey:
    def test_namespace_only(self, settings):
        settings.CACHES = {'default': {'KEY_PREFIX': ''}}
        key = build_cache_key('courses:list')
        assert key == 'courses:list:v1'

    def test_with_prefix(self, settings):
        settings.CACHES = {'default': {'KEY_PREFIX': 'myapp'}}
        key = build_cache_key('courses:list')
        assert key == 'myapp:courses:list:v1'

    def test_with_parts(self, settings):
        settings.CACHES = {'default': {'KEY_PREFIX': ''}}
        key = build_cache_key('courses:list', page=1, search='python')
        assert 'courses:list:v1' in key
        assert 'page=1' in key
        assert 'search=python' in key

    def test_skips_none_and_empty_parts(self, settings):
        settings.CACHES = {'default': {'KEY_PREFIX': ''}}
        key = build_cache_key('ns', a=1, b=None, c='')
        assert 'a=1' in key
        assert 'b=' not in key or 'None' not in key
        assert 'c=' not in key

    def test_version_override(self, settings):
        settings.CACHES = {'default': {'KEY_PREFIX': ''}}
        key = build_cache_key('courses:list', version=2)
        assert key == 'courses:list:v2'


class TestCacheGetOrSet:
    @patch('core.cache.cache')
    def test_returns_cached_value_on_hit(self, mock_cache):
        mock_cache.get.return_value = {'cached': True}
        result = cache_get_or_set('key', lambda: {'new': True})
        assert result == {'cached': True}
        mock_cache.set.assert_not_called()

    @patch('core.cache.cache')
    def test_computes_and_sets_on_miss(self, mock_cache):
        mock_cache.get.return_value = None
        producer = lambda: 42
        result = cache_get_or_set('key', producer, timeout=60)
        assert result == 42
        mock_cache.set.assert_called_once_with('key', 42, 60)

    @patch('core.cache.cache')
    def test_uses_default_timeout_when_none(self, mock_cache):
        mock_cache.get.return_value = None
        mock_cache.default_timeout = 300
        cache_get_or_set('key', lambda: 1)
        mock_cache.set.assert_called_once_with('key', 1, 300)

    @patch('core.cache.cache')
    def test_logs_miss_when_log_misses_true(self, mock_cache, caplog):
        import logging
        caplog.set_level(logging.DEBUG)
        mock_cache.get.return_value = None
        cache_get_or_set('key', lambda: 1, log_misses=True)
        assert 'Cache miss' in caplog.text or 'key' in caplog.text

    @patch('core.cache.cache')
    def test_fallback_on_exception(self, mock_cache):
        mock_cache.get.side_effect = Exception('Redis down')
        result = cache_get_or_set('key', lambda: 99)
        assert result == 99


class TestDeleteCacheWithPrefix:
    @patch('core.cache.cache')
    def test_uses_delete_pattern_when_available(self, mock_cache):
        mock_cache.delete_pattern.return_value = 3
        result = delete_cache_with_prefix('courses:')
        assert result == 3
        mock_cache.delete_pattern.assert_called_once_with('courses:*')

    @patch('core.cache.cache')
    def test_fallback_scan_iter_when_no_delete_pattern(self, mock_cache):
        mock_cache.delete_pattern.side_effect = AttributeError
        mock_client = MagicMock()
        mock_client.scan_iter.return_value = iter(['k1', 'k2'])
        mock_cache.client.get_client.return_value = mock_client
        result = delete_cache_with_prefix('pref:')
        assert result == 2
        assert mock_client.delete.call_count == 2

    @patch('core.cache.cache')
    def test_returns_zero_on_failure(self, mock_cache):
        mock_cache.delete_pattern.side_effect = AttributeError
        mock_cache.client.get_client.side_effect = Exception('No client')
        result = delete_cache_with_prefix('pref:')
        assert result == 0

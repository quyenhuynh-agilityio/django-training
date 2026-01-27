"""Shared caching helpers to keep keys, timeouts, and invalidation consistent."""

import logging
import time

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache versioning: increment when cache schema changes
CACHE_VERSION = 1


def get_timeout(setting_name, default):
    """
    Resolve a cache timeout from settings with a safe fallback.
    """
    return int(getattr(settings, setting_name, default))


def build_cache_key(namespace, version=None, **parts):
    """
    Build a namespaced cache key with the global KEY_PREFIX and optional versioning.

    Args:
        namespace: Base namespace (e.g., "courses:list")
        version: Optional cache version override (defaults to CACHE_VERSION)
        **parts: Key-value pairs to include in the key

    Example:
        build_cache_key("courses:list", page=1, search="python")
        build_cache_key("courses:list", version=2, page=1)
    """
    prefix = settings.CACHES['default'].get('KEY_PREFIX', '')
    cache_version = version if version is not None else CACHE_VERSION
    base = f'{prefix}:{namespace}:v{cache_version}' if prefix else f'{namespace}:v{cache_version}'

    payload = ':'.join(
        f'{name}={value}' for name, value in sorted(parts.items()) if value not in (None, '')
    )

    return f'{base}:{payload}' if payload else base


def cache_get_or_set(key, producer, timeout=None, log_misses=False):
    """
    Retrieve a cached value or compute-and-set it with optional metrics logging.

    Args:
        key: Cache key
        producer: Callable that produces the value if cache misses
        timeout: Cache timeout in seconds (None uses default)
        log_misses: Whether to log cache misses for debugging

    Returns:
        Cached or computed value
    """
    try:
        cached = cache.get(key)
        if cached is not None:
            return cached

        if log_misses:
            logger.debug(f'Cache miss: {key}')

        start_time = time.time()
        value = producer()
        compute_time = time.time() - start_time

        if compute_time > 1.0:
            logger.warning(
                f'Slow cache producer for key {key}: {compute_time:.2f}s '
                '- consider optimizing query or increasing timeout'
            )

        cache.set(key, value, cache.default_timeout if timeout is None else timeout)
        return value

    except Exception as exc:
        logger.error(f'Cache error for key {key}: {exc}', exc_info=True)
        # Fallback: compute value without caching
        return producer()


def delete_cache_with_prefix(prefix):
    """
    Best-effort deletion of keys with a given prefix (Redis backend friendly).

    Returns:
        int: Number of keys deleted (or 0 if indeterminate)
    """
    pattern = f'{prefix}*'
    deleted_count = 0

    # django-redis offers delete_pattern; fallback to raw client scan if available
    try:
        deleted_count = cache.delete_pattern(pattern)  # type: ignore[attr-defined]
        logger.info(f'Deleted {deleted_count} cache keys with pattern {pattern}')
        return deleted_count
    except AttributeError:
        # delete_pattern not available, try raw client
        pass
    except Exception as exc:
        logger.warning(f'delete_pattern failed for {pattern}: {exc}')

    try:
        client = cache.client.get_client()  # type: ignore[attr-defined]
        for key in client.scan_iter(match=pattern):
            client.delete(key)
            deleted_count += 1
        logger.info(f'Deleted {deleted_count} cache keys with pattern {pattern}')
        return deleted_count
    except Exception as exc:  # pragma: no cover - best effort
        logger.debug('Failed to delete cache keys with prefix %s: %s', prefix, exc)
        return 0

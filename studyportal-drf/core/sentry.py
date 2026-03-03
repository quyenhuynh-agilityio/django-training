"""
Small Sentry helper wrappers (SDK 2.x+).

Goal:
- Centralize common "new scope + tags/context + capture" patterns
- Make it easy to add consistent context across tasks/views/signals
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager

import sentry_sdk


def _set_tags(scope: object, tags: Mapping[str, object] | None) -> None:
    if not tags:
        return
    for k, v in tags.items():
        if v is None:
            continue
        scope.set_tag(str(k), v)


def _set_contexts(scope: object, contexts: Mapping[str, Mapping[str, object]] | None) -> None:
    """
    contexts is a mapping of context name -> dict data.
    Example: {"task_data": {"user_id": "...", "email": "..."}}.
    """
    if not contexts:
        return
    for name, data in contexts.items():
        if data is None:
            continue
        scope.set_context(str(name), dict(data))


def _set_user(scope: object, user: Mapping[str, object] | None) -> None:
    if not user:
        return
    scope.set_user(dict(user))


@contextmanager
def sentry_scope(
    *,
    tags: Mapping[str, object] | None = None,
    contexts: Mapping[str, Mapping[str, object]] | None = None,
    user: Mapping[str, object] | None = None,
) -> Iterator[object]:
    """
    Context manager that creates a new Sentry scope and enriches it.
    Uses new_scope() (SDK 2.x+) so tags/context/user do not leak outside the block.
    """
    with sentry_sdk.new_scope() as scope:
        _set_tags(scope, tags)
        _set_contexts(scope, contexts)
        _set_user(scope, user)
        yield scope


def sentry_capture_exception(
    exc: BaseException,
    *,
    tags: Mapping[str, object] | None = None,
    contexts: Mapping[str, Mapping[str, object]] | None = None,
    user: Mapping[str, object] | None = None,
) -> None:
    with sentry_scope(tags=tags, contexts=contexts, user=user):
        sentry_sdk.capture_exception(exc)


def sentry_capture_message(
    message: str,
    *,
    level: str = 'error',
    tags: Mapping[str, object] | None = None,
    contexts: Mapping[str, Mapping[str, object]] | None = None,
    extra: Mapping[str, object] | None = None,
) -> None:
    with sentry_scope(tags=tags, contexts=contexts):
        if extra:
            for k, v in extra.items():
                sentry_sdk.set_extra(str(k), v)
        sentry_sdk.capture_message(message, level=level)


def sentry_add_breadcrumb(
    *,
    category: str,
    message: str,
    level: str = 'info',
    data: dict[str, object] | None = None,
) -> None:
    sentry_sdk.add_breadcrumb(
        category=category,
        message=message,
        level=level,
        data=data or {},
    )

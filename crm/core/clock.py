"""Single source of "now" so time-dependent behaviour is testable.

Business code must call ``clock.now()`` instead of ``timezone.now()``. Tests and
the worker's ``--now`` option can freeze time with ``clock.frozen(dt)``.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import threading

from django.utils import timezone

_state = threading.local()


def now() -> dt.datetime:
    frozen = getattr(_state, "frozen", None)
    if frozen is not None:
        return frozen
    return timezone.now()


@contextlib.contextmanager
def frozen(moment: dt.datetime):
    if timezone.is_naive(moment):
        raise ValueError("frozen() requires an aware datetime")
    previous = getattr(_state, "frozen", None)
    _state.frozen = moment.astimezone(dt.UTC)
    try:
        yield
    finally:
        _state.frozen = previous


def set_frozen(moment: dt.datetime | None) -> None:
    """Freeze (or unfreeze with None) for the current thread; used by tests."""
    _state.frozen = moment.astimezone(dt.UTC) if moment else None

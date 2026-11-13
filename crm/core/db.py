"""Database helpers that keep SQLite specifics out of business logic."""
from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable

from django.db import OperationalError, transaction

from .errors import ServiceUnavailable

log = logging.getLogger("crm.db")

# SQLite binds integers as signed 64-bit. A larger Python int becomes a database error.
SQL_INT_MAX = 2**63 - 1


def parse_version(raw) -> int | None:
    """A posted optimistic version that is safe to bind, or None when it is missing or oversized."""
    if type(raw) is int:
        return raw if 0 <= raw <= SQL_INT_MAX else None
    # isdigit() is true for superscripts and circled numbers, which int() rejects.
    if not isinstance(raw, str) or not raw.isdecimal() or len(raw) > 19:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value <= SQL_INT_MAX else None


def require_version(version) -> int:
    """Reject a missing or out-of-range expected version before it reaches the database."""
    from .errors import DomainError

    if type(version) is not int or version < 0 or version > SQL_INT_MAX:
        raise DomainError("Reload the page and try again.", code="version_required")
    return version

_LOCK_MESSAGES = ("database is locked", "database table is locked", "busy")


def is_lock_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return isinstance(exc, OperationalError) and any(m in text for m in _LOCK_MESSAGES)


def write_transaction[T](fn: Callable[[], T], *, attempts: int = 4, base_delay: float = 0.05) -> T:
    """Run ``fn`` in a short atomic write transaction with bounded lock retries.

    Only lock/busy errors are retried. After the final attempt the failure is
    surfaced as ``ServiceUnavailable`` so the UI shows it instead of hiding it.
    ``fn`` must be safe to re-run (it is, because the transaction rolled back).
    """
    for attempt in range(1, attempts + 1):
        try:
            with transaction.atomic():
                return fn()
        except OperationalError as exc:
            if not is_lock_error(exc) or transaction.get_connection().in_atomic_block:
                raise
            if attempt == attempts:
                log.warning("write transaction gave up after lock contention", extra={"attempts": attempt})
                raise ServiceUnavailable(
                    "The database is busy. Nothing was saved; please try again.", code="db_busy"
                ) from exc
            time.sleep(base_delay * (2 ** (attempt - 1)) * (1 + random.random()))
    raise AssertionError("unreachable")

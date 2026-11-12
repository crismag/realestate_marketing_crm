from __future__ import annotations

import datetime as dt
import hashlib

from django.conf import settings
from django.db import transaction
from django.db.models import F

from crm.core import clock

from .models import LoginThrottle


def _keys(email: str, ip: str) -> list[str]:
    ident = hashlib.sha256((email or "").strip().lower().encode()).hexdigest()[:32]
    return [f"acct:{ident}", f"ip:{ip or 'unknown'}"]


def lockout_remaining(email: str, ip: str) -> dt.timedelta | None:
    now = clock.now()
    rows = LoginThrottle.objects.filter(key__in=_keys(email, ip), locked_until__gt=now)
    latest = max((r.locked_until for r in rows), default=None)
    return (latest - now) if latest else None


def record_failure(email: str, ip: str) -> None:
    now = clock.now()
    window = dt.timedelta(minutes=settings.CRM_LOGIN_LOCK_MINUTES)
    # The IP limit is looser so one office NAT does not lock everyone out.
    limits = {"acct": settings.CRM_LOGIN_MAX_FAILURES, "ip": settings.CRM_LOGIN_MAX_FAILURES * 4}
    with transaction.atomic():
        for key in _keys(email, ip):
            row, _ = LoginThrottle.objects.get_or_create(key=key)
            if row.first_failure_at is None or now - row.first_failure_at > window:
                LoginThrottle.objects.filter(pk=row.pk).update(failures=1, first_failure_at=now, locked_until=None)
                continue
            LoginThrottle.objects.filter(pk=row.pk).update(failures=F("failures") + 1)
            row.refresh_from_db()
            if row.failures >= limits[key.split(":")[0]]:
                LoginThrottle.objects.filter(pk=row.pk).update(locked_until=now + window)


def record_success(email: str, ip: str) -> None:
    LoginThrottle.objects.filter(key=_keys(email, ip)[0]).delete()

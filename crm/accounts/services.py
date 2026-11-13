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


# --- Two-step sign-in -------------------------------------------------------------

def verify_second_factor(user, code: str) -> bool:
    """Check an authenticator code (no replay) or a one-time recovery code. Records the use."""
    from crm.core.services import audit

    from . import totp
    from .models import User

    step = totp.matching_step(user.totp_secret, code, timestamp=clock.now().timestamp(), after_step=user.totp_last_step)
    if step is not None:
        # Conditional update: two requests racing with the same code cannot both succeed.
        return bool(User.objects.filter(pk=user.pk, totp_last_step__lt=step).update(totp_last_step=step))
    digest = totp.hash_code(code)
    with transaction.atomic():
        fresh = User.objects.select_for_update().get(pk=user.pk)
        if digest in fresh.recovery_code_hashes:
            remaining = [h for h in fresh.recovery_code_hashes if h != digest]
            User.objects.filter(pk=user.pk).update(recovery_code_hashes=remaining)
            audit("auth.recovery_code_used", fresh, f"Recovery code used; {len(remaining)} left", actor=fresh)
            return True
    return False


def enable_two_factor(user, *, secret: str, code: str) -> list[str] | None:
    """Confirm setup with a code from the app. Returns fresh recovery codes (shown once) or None if the code is wrong."""
    from crm.core.services import audit

    from . import totp
    from .models import User

    step = totp.matching_step(secret, code, timestamp=clock.now().timestamp())
    if step is None:
        return None
    codes = totp.new_recovery_codes()
    with transaction.atomic():
        User.objects.filter(pk=user.pk).update(totp_secret=secret, totp_confirmed_at=clock.now(), totp_last_step=step,
                                               recovery_code_hashes=[totp.hash_code(c) for c in codes])
        audit("auth.2fa_enabled", user, "Two-step sign-in turned on", actor=user)
    return codes


def disable_two_factor(user, *, actor) -> None:
    from crm.core.services import audit

    from .models import User

    with transaction.atomic():
        User.objects.filter(pk=user.pk).update(totp_secret="", totp_confirmed_at=None, totp_last_step=0,
                                               recovery_code_hashes=[])
        who = "by themselves" if actor.pk == user.pk else f"by {actor}"
        audit("auth.2fa_disabled", user, f"Two-step sign-in turned off {who}", actor=actor)


def allow_reset_request(ip: str, *, limit: int = 5) -> bool:
    """At most ``limit`` password-reset emails per IP per lockout window (separate from sign-in counters)."""
    now = clock.now()
    window = dt.timedelta(minutes=settings.CRM_LOGIN_LOCK_MINUTES)
    with transaction.atomic():
        row, _ = LoginThrottle.objects.get_or_create(key=f"reset:{ip or 'unknown'}")
        if row.first_failure_at is None or now - row.first_failure_at > window:
            LoginThrottle.objects.filter(pk=row.pk).update(failures=1, first_failure_at=now, locked_until=None)
            return True
        LoginThrottle.objects.filter(pk=row.pk).update(failures=F("failures") + 1)
        return row.failures + 1 <= limit

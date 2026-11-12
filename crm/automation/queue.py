"""Transactional outbox / durable job queue API used by business services.

``enqueue`` is called inside the business transaction, so the job exists if
and only if the business change committed. Delivery happens later in the
worker, so a failed notification never undoes a valid business change.
"""
from __future__ import annotations

import datetime as dt

from django.db import IntegrityError, transaction

from crm.core import clock

from .models import Job


def enqueue(kind: str, payload: dict, *, logical_key: str | None = None, run_at: dt.datetime | None = None,
            max_attempts: int = 5, rule=None) -> Job | None:
    """Create a job. Returns None if a job with the same logical key already exists (duplicate suppression)."""
    if logical_key and Job.objects.filter(logical_key=logical_key).exists():
        return None
    try:
        with transaction.atomic():
            return Job.objects.create(
                kind=kind,
                payload=payload,
                logical_key=logical_key,
                run_at=run_at or clock.now(),
                max_attempts=max_attempts,
                rule=rule,
                rule_version=getattr(rule, "version", None),
                created_at=clock.now(),
                updated_at=clock.now(),
            )
    except IntegrityError:
        if logical_key and Job.objects.filter(logical_key=logical_key).exists():
            return None
        raise


def emit(event: str, **payload) -> Job | None:
    """Record a domain event for asynchronous handling (notifications, rules)."""
    key = payload.pop("event_key", None)
    return enqueue(f"event.{event}", payload, logical_key=f"event:{event}:{key}" if key else None)

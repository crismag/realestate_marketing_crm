"""Database-backed worker: leases, retries with backoff, crash recovery, schedules.

Run with ``python manage.py run_worker``. Several workers may run; a job is
leased atomically with a conditional UPDATE so only one worker executes it.
A crashed worker's lease expires and the job becomes runnable again
(at-least-once execution). Handlers are idempotent through logical keys.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import signal
import socket
import time
import traceback
import uuid
import zoneinfo

from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import F

from crm.core import clock
from crm.core.db import is_lock_error
from crm.core.services import get_policy

from . import engine
from .models import Job, JobAttempt, ScheduleState, WorkerHeartbeat
from .queue import enqueue

log = logging.getLogger("crm.worker")


class PermanentError(Exception):
    """Do not retry this job."""


def _handlers():
    from crm.comms import services as comms

    def send(job):
        try:
            return comms.send_message(job.payload["message_id"], job.payload)
        except comms.RetryLater as exc:
            raise Deferred(str(exc), exc.run_at) from exc

    return {
        "event.inquiry_received": lambda job: engine.on_inquiry_received(job.payload),
        "event.became_client": lambda job: engine.on_became_client(job.payload),
        "event.handover_requested": lambda job: engine.on_handover_requested(job.payload),
        "event.handover_closed": lambda job: engine.on_handover_closed(job.payload),
        "event.task_assigned": lambda job: engine.on_task_assigned(job.payload),
        "event.contact_updated": lambda job: engine.on_contact_event(job.payload, job_id=job.pk),
        "event.contact_activity": lambda job: engine.on_contact_event(job.payload, job_id=job.pk),
        "event.assignment_changed": lambda job: engine.on_assignment_changed(job.payload, job_id=job.pk),
        "event.customer_replied": lambda job: engine.on_customer_replied(job.payload, job_id=job.pk),
        "sweep.attention": lambda job: engine.run_sweep(clock.now(), job=job),
        "digest.daily": lambda job: engine.run_digest(clock.now(), job=job),
        "comms.send": send,
    }


class Deferred(Exception):
    def __init__(self, message, run_at):
        super().__init__(message)
        self.run_at = run_at


def backoff(attempts: int) -> dt.timedelta:
    return dt.timedelta(seconds=min(3600, 30 * (2 ** max(0, attempts - 1))))


# --- Scheduling --------------------------------------------------------------------

def schedule_periodic(now: dt.datetime | None = None) -> list[str]:
    """Enqueue due periodic jobs. Missed windows are coalesced into one run (catch-up policy)."""
    now = now or clock.now()
    policy = get_policy()
    created = []
    sweep_minutes = max(1, int(policy["notifications"]["attention_sweep_minutes"]))
    state, _ = ScheduleState.objects.get_or_create(key="sweep.attention", defaults={"next_run_at": now})
    if state.next_run_at <= now:
        slot = int(now.timestamp() // (sweep_minutes * 60))
        if enqueue("sweep.attention", {}, logical_key=f"sweep:{slot}", max_attempts=3):
            created.append("sweep.attention")
        ScheduleState.objects.filter(pk=state.pk).update(last_run_at=now, next_run_at=now + dt.timedelta(minutes=sweep_minutes))

    tz = zoneinfo.ZoneInfo(policy["timezone"])
    local = now.astimezone(tz)
    digest_hour = int(policy["notifications"]["digest_hour"])
    today_at = local.replace(hour=digest_hour, minute=0, second=0, microsecond=0)
    state, _ = ScheduleState.objects.get_or_create(key="digest.daily", defaults={"next_run_at": today_at.astimezone(dt.UTC)})
    if state.next_run_at <= now:
        due_local_day = local.date() if local >= today_at else (local - dt.timedelta(days=1)).date()
        if enqueue("digest.daily", {"day": due_local_day.isoformat()}, logical_key=f"digest:{due_local_day.isoformat()}",
                   max_attempts=3):
            created.append("digest.daily")
        nxt = today_at if local < today_at else today_at + dt.timedelta(days=1)
        ScheduleState.objects.filter(pk=state.pk).update(last_run_at=now, next_run_at=nxt.astimezone(dt.UTC))
    return created


# --- Leasing ------------------------------------------------------------------------

def recover_expired_leases(now: dt.datetime) -> int:
    expired = Job.objects.filter(status="running", lease_expires_at__lt=now)
    count = 0
    for job in expired:
        exhausted = job.attempts >= job.max_attempts
        with transaction.atomic():
            updated = Job.objects.filter(
                pk=job.pk, status="running", lease_owner=job.lease_owner, attempts=job.attempts,
                lease_expires_at=job.lease_expires_at, lease_expires_at__lt=now,
            ).update(
                status="dead" if exhausted else "failed",
                last_error=f"Lease expired (worker {job.lease_owner} stopped or crashed)",
                lease_owner="", lease_expires_at=None, updated_at=now, run_at=now,
                finished_at=now if exhausted else None,
            )
            if updated:
                JobAttempt.objects.filter(job=job, attempt_no=job.attempts, worker_id=job.lease_owner,
                                          finished_at__isnull=True).update(finished_at=now, outcome="lease_expired")
                if exhausted and job.kind == "comms.send":
                    from crm.comms.services import mark_uncertain_after_crash

                    mark_uncertain_after_crash(job.payload.get("message_id"))
            count += updated
        if updated:
            log.warning("job lease expired", extra={"job_id": job.pk, "kind": job.kind, "attempt": job.attempts,
                                                    "worker": job.lease_owner, "exhausted": exhausted})
    return count


def lease_next(worker_id: str, now: dt.datetime) -> Job | None:
    lease = dt.timedelta(seconds=settings.CRM_WORKER_LEASE_SECONDS)
    candidates = Job.objects.filter(status__in=("queued", "failed"), run_at__lte=now).order_by("run_at", "id").values_list(
        "pk", flat=True)[:10]
    for pk in candidates:
        with transaction.atomic():
            won = Job.objects.filter(pk=pk, status__in=("queued", "failed"), run_at__lte=now).update(
                status="running", lease_owner=worker_id, lease_expires_at=now + lease, attempts=F("attempts") + 1,
                updated_at=now,
            )
            if won == 1:
                job = Job.objects.get(pk=pk)
                JobAttempt.objects.create(job=job, attempt_no=job.attempts, worker_id=worker_id, started_at=now)
                return job
    return None


def execute(job: Job, worker_id: str) -> str:
    handlers = _handlers()
    handler = handlers.get(job.kind)
    started = clock.now()

    def finish(outcome, *, error="", fail_message=False, **changes):
        # The attempt is a fencing token even if a worker reuses its identifier.
        # Keep finalization and its side effects atomic with the ownership check.
        with transaction.atomic():
            updated = Job.objects.filter(pk=job.pk, status="running", lease_owner=worker_id,
                                         attempts=job.attempts).update(**changes)
            if not updated:
                log.warning("stale job result discarded", extra={"job_id": job.pk, "kind": job.kind,
                                                                 "attempt": job.attempts, "outcome": outcome})
                return "stale"
            JobAttempt.objects.filter(job=job, attempt_no=job.attempts, worker_id=worker_id,
                                      finished_at__isnull=True).update(
                finished_at=clock.now(), outcome=outcome, error=error)
            if fail_message:
                from crm.comms.services import mark_failed

                mark_failed(job.payload.get("message_id"), error)
        return outcome

    try:
        if handler is None:
            raise PermanentError(f"No handler for job kind '{job.kind}'")
        # Slow handler work stays outside the short finalization transaction.
        result = handler(job) or {}
        finished = clock.now()
        return finish("succeeded", status="succeeded", result=result, finished_at=finished,
                      updated_at=finished, lease_owner="", lease_expires_at=None, last_error="")
    except Deferred as exc:
        return finish("deferred", error=str(exc), status="queued", run_at=exc.run_at,
                      attempts=F("attempts") - 1, lease_owner="", lease_expires_at=None,
                      last_error=str(exc), updated_at=clock.now())
    except Exception as exc:  # noqa: BLE001 - every failure is recorded and retried or dead-lettered
        if is_lock_error(exc):
            return finish("contended", status="queued", attempts=F("attempts") - 1, lease_owner="",
                          lease_expires_at=None, run_at=clock.now() + dt.timedelta(seconds=2))
        now = clock.now()
        permanent = isinstance(exc, PermanentError) or job.attempts >= job.max_attempts
        error = f"{exc.__class__.__name__}: {exc}"[:2000]
        outcome = finish(
            "dead" if permanent else "failed", error=error,
            fail_message=permanent and job.kind == "comms.send",
            status="dead" if permanent else "failed", last_error=error, updated_at=now, lease_owner="",
            lease_expires_at=None, run_at=now + backoff(job.attempts), finished_at=now if permanent else None,
        )
        if outcome != "stale":
            log.warning("job failed", extra={"job_id": job.pk, "kind": job.kind, "attempt": job.attempts,
                                             "permanent": permanent, "error": error,
                                             "trace": traceback.format_exc().splitlines()[-1]})
        return outcome
    finally:
        log.info("job finished", extra={"job_id": job.pk, "kind": job.kind,
                                        "ms": int((clock.now() - started).total_seconds() * 1000)})


def retry_job(job: Job, *, actor) -> Job:
    """Controlled manual retry of a dead or failed job (Automation screen)."""
    from crm.core.errors import DomainError
    from crm.core.services import audit

    if job.status not in ("dead", "failed"):
        raise DomainError("Only failed jobs can be retried.", code="not_retryable")
    with transaction.atomic():
        Job.objects.filter(pk=job.pk, status__in=("dead", "failed")).update(
            status="queued", run_at=clock.now(), max_attempts=F("attempts") + 1, finished_at=None, updated_at=clock.now()
        )
        if job.kind == "comms.send":
            from crm.comms.models import OutboundMessage

            OutboundMessage.objects.filter(pk=job.payload.get("message_id"), status="failed").update(
                status="scheduled", status_reason="Manual retry requested")
        audit("job.retry", job, f"Manual retry of job {job.pk} ({job.kind})", actor=actor)
    return Job.objects.get(pk=job.pk)


def cancel_job(job: Job, *, actor) -> Job:
    from crm.core.errors import DomainError
    from crm.core.services import audit

    if job.status not in ("queued", "failed", "dead"):
        raise DomainError("Only waiting or failed jobs can be cancelled.", code="not_cancellable")
    with transaction.atomic():
        Job.objects.filter(pk=job.pk, status__in=("queued", "failed", "dead")).update(status="cancelled",
                                                                                      finished_at=clock.now())
        if job.kind == "comms.send":
            from crm.comms.models import OutboundMessage

            OutboundMessage.objects.filter(pk=job.payload.get("message_id"), status__in=("scheduled", "failed")).update(
                status="cancelled", status_reason="Cancelled by a user")
        audit("job.cancelled", job, f"Cancelled job {job.pk} ({job.kind})", actor=actor)
    return Job.objects.get(pk=job.pk)


class Worker:
    def __init__(self, *, worker_id: str | None = None, poll_seconds: float | None = None):
        self.worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
        self.poll_seconds = poll_seconds if poll_seconds is not None else settings.CRM_WORKER_POLL_SECONDS
        self.stopping = False
        self.processed = 0

    def heartbeat(self, state: str = "running"):
        now = clock.now()
        WorkerHeartbeat.objects.update_or_create(
            worker_id=self.worker_id,
            defaults={"hostname": socket.gethostname()[:120], "pid": os.getpid(), "last_seen_at": now,
                      "jobs_processed": self.processed, "state": state},
            create_defaults={"hostname": socket.gethostname()[:120], "pid": os.getpid(), "started_at": now,
                             "last_seen_at": now, "jobs_processed": 0, "state": state},
        )

    def install_signal_handlers(self):
        def stop(signum, frame):
            log.info("worker stopping after current job", extra={"signal": signum})
            self.stopping = True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

    def run_once(self, *, schedule: bool = True, max_jobs: int = 1000) -> dict:
        """Process every currently due job (used by tests, cron-style runs and --once)."""
        outcomes: dict[str, int] = {}
        self.heartbeat()
        recover_expired_leases(clock.now())
        if schedule:
            schedule_periodic(clock.now())
        for _ in range(max_jobs):
            if self.stopping:
                break
            job = lease_next(self.worker_id, clock.now())
            if job is None:
                break
            outcome = execute(job, self.worker_id)
            self.processed += 1
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
        self.heartbeat()
        return outcomes

    def run_forever(self, *, deadline: dt.datetime | None = None):
        self.install_signal_handlers()
        log.info("worker started", extra={"worker_id": self.worker_id})
        failures = 0
        while not self.stopping:
            if deadline and clock.now() >= deadline:
                break
            try:
                close_old_connections()
                outcomes = self.run_once()
                failures = 0
                if not outcomes:
                    time.sleep(self.poll_seconds)
            except Exception as exc:  # noqa: BLE001 - keep the worker alive with bounded backoff
                failures += 1
                wait = min(60, 2 ** failures)
                log.error("worker loop error", extra={"error": str(exc)[:500], "retry_in_s": wait})
                time.sleep(wait)
        self.heartbeat(state="stopped")
        log.info("worker stopped", extra={"worker_id": self.worker_id, "processed": self.processed})


def worker_health(now: dt.datetime | None = None) -> dict:
    now = now or clock.now()
    beats = list(WorkerHeartbeat.objects.all()[:10])
    alive = [b for b in beats if b.state == "running" and now - b.last_seen_at < dt.timedelta(
        seconds=max(60, settings.CRM_WORKER_POLL_SECONDS * 6))]
    backlog = Job.objects.filter(status__in=("queued", "failed"), run_at__lte=now).count()
    oldest = Job.objects.filter(status__in=("queued", "failed"), run_at__lte=now).order_by("run_at").first()
    return {
        "alive": bool(alive),
        "workers": beats,
        "due_backlog": backlog,
        "oldest_due": oldest.run_at if oldest else None,
        "dead": Job.objects.filter(status="dead").count(),
        "running": Job.objects.filter(status="running").count(),
    }

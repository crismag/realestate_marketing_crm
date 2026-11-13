"""A worker that lost its lease cannot finalize a newer execution."""
import datetime as dt

import pytest
from django.db import OperationalError

from crm.automation import worker
from crm.automation.models import Job, JobAttempt
from crm.automation.queue import enqueue
from crm.comms.models import OutboundMessage
from crm.comms.services import schedule_customer_message
from crm.core import clock

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("outcome", ["success", "deferred", "contended", "failure"])
@pytest.mark.parametrize("same_owner", [False, True])
def test_lost_lease_cannot_overwrite_new_attempt(monkeypatch, frozen, outcome, same_owner):
    queued = enqueue("test.fence", {}, max_attempts=1)
    original = worker.lease_next("worker-a", frozen)
    assert original.pk == queued.pk
    current_owner = "worker-a" if same_owner else "worker-b"

    def handler(job):
        Job.objects.filter(pk=job.pk).update(lease_expires_at=frozen - dt.timedelta(seconds=1))
        assert worker.recover_expired_leases(frozen) == 1
        Job.objects.filter(pk=job.pk).update(status="queued", max_attempts=3)
        replacement = worker.lease_next(current_owner, frozen)
        assert replacement.attempts == 2
        if outcome == "deferred":
            raise worker.Deferred("quiet hours", frozen + dt.timedelta(hours=1))
        if outcome == "contended":
            raise OperationalError("database is locked")
        if outcome == "failure":
            raise RuntimeError("late failure")
        return {"late": True}

    monkeypatch.setattr(worker, "_handlers", lambda: {"test.fence": handler})
    assert worker.execute(original, "worker-a") == "stale"
    queued.refresh_from_db()
    assert queued.status == "running"
    assert queued.lease_owner == current_owner
    assert queued.attempts == 2
    assert queued.result == {}
    old, new = list(JobAttempt.objects.filter(job=queued).order_by("attempt_no"))
    assert old.outcome == "lease_expired"
    assert new.finished_at is None


def test_stale_terminal_send_failure_does_not_fail_message(monkeypatch, frozen, make_contact):
    contact = make_contact(email="test@example.test")
    msg = schedule_customer_message(contact, template_key="inquiry-ack", rule=None, logical_key="test-message")
    original = worker.lease_next("worker-a", clock.now())
    assert original.kind == "comms.send"
    Job.objects.filter(pk=original.pk).update(max_attempts=1)
    original.max_attempts = 1

    def handler(job):
        Job.objects.filter(pk=job.pk).update(status="succeeded", lease_owner="", lease_expires_at=None)
        OutboundMessage.objects.filter(pk=msg.pk).update(status="scheduled")
        raise RuntimeError("late failure")

    monkeypatch.setattr(worker, "_handlers", lambda: {"comms.send": handler})
    assert worker.execute(original, "worker-a") == "stale"
    msg.refresh_from_db()
    assert msg.status == "scheduled"


def test_recovery_does_not_expire_replacement_lease(monkeypatch, frozen):
    from django.db.models.query import QuerySet

    queued = enqueue("test.fence", {})
    original = worker.lease_next("worker-a", frozen)
    Job.objects.filter(pk=queued.pk).update(lease_expires_at=frozen - dt.timedelta(seconds=1))
    update = QuerySet.update

    def interleave(queryset, **changes):
        if changes.get("last_error", "").startswith("Lease expired"):
            # Another recovery and worker win after this recovery read its snapshot.
            update(Job.objects.filter(pk=queued.pk), attempts=2, lease_owner="worker-b",
                   lease_expires_at=frozen + dt.timedelta(minutes=5))
            JobAttempt.objects.create(job=queued, attempt_no=2, worker_id="worker-b", started_at=frozen)
        return update(queryset, **changes)

    monkeypatch.setattr(QuerySet, "update", interleave)
    assert worker.recover_expired_leases(frozen) == 0
    queued.refresh_from_db()
    assert queued.status == "running" and queued.lease_owner == "worker-b"
    assert JobAttempt.objects.get(job=queued, attempt_no=2).finished_at is None
    assert JobAttempt.objects.get(job=original, attempt_no=1).finished_at is None

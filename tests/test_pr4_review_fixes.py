"""Follow-up fixes from the review of the hardening work (unanswered replies, crashed sends, merged digests)."""
import datetime as dt

import pytest

from crm.attention import services as attention
from crm.automation import engine, worker
from crm.automation.models import Job, Notification
from crm.comms.models import OutboundMessage
from crm.comms.services import schedule_customer_message
from crm.contacts import services as contacts
from crm.contacts.merging import merge_contacts
from crm.contacts.models import Contact
from crm.core import clock
from crm.core.errors import DomainError

pytestmark = pytest.mark.django_db
H = dt.timedelta(hours=1)


def awaiting(contact, policy, now):
    return [reason for item in attention.evaluate(now=now, policy=policy, contact_ids=[contact.pk])
            for reason in item.active_reasons if reason.code == "inquiry_awaiting"]


def record(contact, actor, kind, when, now, inquiry=None):
    with clock.frozen(now):
        return contacts.record_interaction(contact, actor=actor, kind=kind, channel="phone", summary="Recorded evidence",
                                           occurred_at=when, inquiry=inquiry)


def test_second_customer_reply_does_not_reset_the_wait(users, make_contact, policy, now):
    contact = make_contact()
    record(contact, users["ana"], "inbound_reply", now - 30 * H, now)
    record(contact, users["ana"], "inbound_reply", now - H, now)
    reasons = awaiting(contact, policy, now)
    assert len(reasons) == 1
    assert reasons[0].since == now - 30 * H
    assert reasons[0].overdue


def test_reply_on_inquiry_closed_without_response_stays_closed(users, make_contact, policy, now):
    with clock.frozen(now - 3 * H):
        contact = make_contact(inquiry="Spam offer")
    inquiry = contact.inquiries.get()
    record(contact, users["ana"], "inbound_reply", now - 2 * H, now, inquiry=inquiry)
    with clock.frozen(now - H):
        contacts.close_inquiry(inquiry, actor=users["ana"], reason="Spam")
    assert awaiting(contact, policy, now) == []
    # A later reply that is not tied to the closed inquiry still needs someone.
    record(contact, users["ana"], "inbound_reply", now - H / 2, now)
    assert len(awaiting(contact, policy, now)) == 1


def crash_send_job(make_contact, *, reached_transport):
    contact = make_contact(email="test@example.test")
    msg = schedule_customer_message(contact, template_key="inquiry-ack", rule=None, logical_key="crash-message")
    job = worker.lease_next("worker-a", clock.now())
    assert job.kind == "comms.send"
    if reached_transport:
        OutboundMessage.objects.filter(pk=msg.pk).update(attempted_at=clock.now())
    Job.objects.filter(pk=job.pk).update(max_attempts=1, lease_expires_at=clock.now() - dt.timedelta(seconds=1))
    assert worker.recover_expired_leases(clock.now()) == 1
    job.refresh_from_db()
    msg.refresh_from_db()
    assert job.status == "dead"
    return job, msg


def test_send_job_that_crashes_after_reaching_transport_ends_uncertain(frozen, make_contact, users):
    job, msg = crash_send_job(make_contact, reached_transport=True)
    assert msg.status == "uncertain"  # never failed: a manual retry could send it twice
    with pytest.raises(DomainError, match="may already have gone out"):
        worker.retry_job(job, actor=users["ana"])


def test_send_job_that_crashes_before_sending_fails_and_can_be_retried(frozen, make_contact, users):
    job, msg = crash_send_job(make_contact, reached_transport=False)
    assert msg.status == "failed"
    worker.retry_job(job, actor=users["ana"])
    msg.refresh_from_db()
    assert msg.status == "scheduled"


def test_merged_client_counts_as_continuing_in_next_digest(users, make_contact):
    day = dt.datetime(2026, 11, 16, 3, tzinfo=dt.UTC)
    with clock.frozen(day):
        keep = make_contact("Maria Santos", email="maria@example.test")
        dup = make_contact("Maria Santos", email="maria.s@example.test")
        engine.run_digest()
    with clock.frozen(day + dt.timedelta(hours=2)):
        keep, dup = Contact.objects.get(pk=keep.pk), Contact.objects.get(pk=dup.pk)
        merge_contacts(keep, dup, actor=users["ana"], keep_version=keep.version, duplicate_version=dup.version)
    with clock.frozen(day + dt.timedelta(days=1)):
        engine.run_digest()
    note = Notification.objects.filter(kind="digest", recipient=users["ana"]).latest("created_at", "id")
    assert "0 new" in note.title and "1 continuing" in note.title and "0 resolved" in note.title


def test_merge_chain_maps_to_the_final_record(frozen, make_contact):
    from crm.automation.engine import _canonical_ids

    ids = [make_contact(f"Chain Person {i}", email=f"chain{i}@example.test").pk for i in range(8)]
    for older, newer in zip(ids, ids[1:], strict=False):
        Contact.objects.filter(pk=older).update(merged_into_id=newer)
    assert _canonical_ids([ids[0]]) == {ids[-1]}

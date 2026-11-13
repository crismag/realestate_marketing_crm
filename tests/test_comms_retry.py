import pytest

from crm.automation.models import Job
from crm.automation.worker import execute, lease_next
from crm.comms.models import OutboundMessage
from crm.comms.services import resolve_uncertain, retry_message, schedule_customer_message, send_message
from crm.contacts.models import Inquiry, Interaction
from crm.core.errors import ConflictError, DomainError
from crm.core.models import AuditEvent

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("stop", ["answered", "replied"])
def test_retry_preserves_inquiry_stop_policy(stop, make_contact, users, frozen, settings):
    contact = make_contact(email="customer@example.test")
    inquiry = Inquiry.objects.create(contact=contact, message="Hello", received_at=frozen)
    msg = schedule_customer_message(contact, template_key="inquiry-ack", rule=None,
                                    logical_key="retry-stop", context={"inquiry_id": inquiry.pk})
    OutboundMessage.objects.filter(pk=msg.pk).update(status="failed")
    msg.refresh_from_db()
    if stop == "answered":
        Inquiry.objects.filter(pk=inquiry.pk).update(status="responded")
    else:
        Interaction.objects.create(contact=contact, kind="inbound_reply", channel="email",
                                   summary="Customer replied", occurred_at=frozen)
    retry_message(msg, actor=users["ana"])
    retry = Job.objects.filter(kind="comms.send").order_by("-pk").first()
    send_message(msg.pk, retry.payload)
    msg.refresh_from_db()
    assert msg.status == "suppressed"
    assert not (settings.VAR_DIR / "sandbox_mail" / f"message-{msg.pk}.eml").exists()


def test_stale_retry_does_not_enqueue_or_audit(make_contact, users, frozen):
    msg = OutboundMessage.objects.create(contact=make_contact(), logical_key="stale-retry", status="failed")
    OutboundMessage.objects.filter(pk=msg.pk).update(status="cancelled")
    with pytest.raises(ConflictError):
        retry_message(msg, actor=users["ana"])
    assert not Job.objects.filter(kind="comms.send").exists()
    assert not AuditEvent.objects.filter(action="message.retry").exists()


def test_stale_resolution_does_not_audit(make_contact, users, frozen):
    msg = OutboundMessage.objects.create(contact=make_contact(), logical_key="stale-resolve", status="uncertain")
    OutboundMessage.objects.filter(pk=msg.pk).update(status="cancelled")
    with pytest.raises(ConflictError):
        resolve_uncertain(msg, actor=users["ana"], outcome="failed", note="Checked provider")
    assert not AuditEvent.objects.filter(action="message.resolved").exists()


def test_repeated_retry_at_same_clock_enqueues_after_each_failure(make_contact, users, frozen):
    msg = schedule_customer_message(make_contact(email="customer@fail.invalid"), template_key="inquiry-ack",
                                    rule=None, logical_key="repeated-retry")
    Job.objects.filter(kind="comms.send").update(status="dead")
    OutboundMessage.objects.filter(pk=msg.pk).update(status="failed")
    msg.refresh_from_db()
    retry_message(msg, actor=users["ana"])
    first = lease_next("retry-worker", frozen)
    assert execute(first, "retry-worker") == "dead"
    msg.refresh_from_db()
    assert msg.status == "failed"
    retry_message(msg, actor=users["ana"])
    second = lease_next("retry-worker", frozen)
    assert second is not None
    assert second.pk != first.pk
    assert execute(second, "retry-worker") == "dead"


def test_retry_without_original_context_fails_without_changes(make_contact, users, frozen):
    msg = OutboundMessage.objects.create(contact=make_contact(), logical_key="missing-context", status="failed")
    with pytest.raises(DomainError) as exc:
        retry_message(msg, actor=users["ana"])
    assert exc.value.code == "retry_context_missing"
    assert "original" in exc.value.message.lower()
    msg.refresh_from_db()
    assert msg.status == "failed"
    assert not Job.objects.filter(kind="comms.send").exists()
    assert not AuditEvent.objects.filter(action="message.retry").exists()

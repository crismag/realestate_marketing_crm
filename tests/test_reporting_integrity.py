"""Chronology and transactional integrity behind reporting numbers."""
import datetime as dt

import pytest

from crm.contacts import services as contacts
from crm.contacts.models import Inquiry, Interaction, Source
from crm.core.errors import DomainError
from crm.core.models import AuditEvent
from crm.reporting.models import SpendEntry

pytestmark = pytest.mark.django_db


def test_future_inquiry_is_rejected_without_persistence(users, make_contact, frozen):
    contact = make_contact()
    with pytest.raises(DomainError, match="future"):
        contacts.record_inquiry(contact, actor=users["ana"], message="Future request", channel="phone", source=None,
                                received_at=frozen + dt.timedelta(minutes=1))
    assert not Inquiry.objects.filter(contact=contact).exists()


def test_response_before_receipt_is_rejected(users, make_contact, frozen):
    contact = make_contact(inquiry="Question")
    inquiry = contact.inquiries.get()
    with pytest.raises(DomainError, match="before"):
        contacts.record_interaction(contact, actor=users["ana"], kind="conversation", channel="phone", summary="Old call",
                                    occurred_at=frozen - dt.timedelta(hours=1), inquiry=inquiry)
    inquiry.refresh_from_db()
    assert inquiry.status == "awaiting"
    assert not Interaction.objects.filter(contact=contact).exists()


def test_spend_creation_rolls_back_if_audit_fails(client, users, monkeypatch, frozen):
    client.force_login(users["ana"])

    def fail_audit(**kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(AuditEvent.objects, "create", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post("/reports/spend/", {"source": Source.objects.get(code="social").pk, "kind": "actual",
                                       "period_start": frozen.date(), "period_end": frozen.date(), "amount": "12.34"})
    assert not SpendEntry.objects.exists()


def test_historical_inquiry_and_response_remain_valid(users, make_contact, frozen):
    contact = make_contact()
    received = frozen - dt.timedelta(days=2)
    inquiry = contacts.record_inquiry(contact, actor=users["ana"], message="Historical request", channel="phone",
                                      source=None, received_at=received, external_key="historical-request")
    # A replay returns the committed inquiry even if a retried payload has an invalid timestamp.
    replay = contacts.record_inquiry(contact, actor=users["ana"], message="Retry", channel="phone", source=None,
                                     received_at=frozen + dt.timedelta(days=1), external_key="historical-request")
    assert replay.pk == inquiry.pk
    interaction = contacts.record_interaction(contact, actor=users["ana"], kind="conversation", channel="phone",
                                              summary="Historical response", occurred_at=received, inquiry=inquiry)
    inquiry.refresh_from_db()
    assert inquiry.status == "responded" and inquiry.responded_at == received
    assert interaction.recorded_at == frozen


def test_future_inquiry_form_keeps_entered_message(client, users, make_contact, frozen):
    client.force_login(users["ana"])
    contact = make_contact()
    response = client.post(f"/contacts/{contact.pk}/inquiries/", {
        "inq-message": "Keep this inquiry", "inq-channel": "phone", "inq-received_at": "2099-01-01T12:00"})
    assert response.status_code == 400
    assert "Keep this inquiry" in response.content.decode()
    assert not contact.inquiries.exists()


def test_spend_success_keeps_audit_and_exact_minor_units(client, users, frozen):
    client.force_login(users["ana"])
    response = client.post("/reports/spend/", {"source": Source.objects.get(code="social").pk, "kind": "actual",
                                             "period_start": frozen.date(), "period_end": frozen.date(), "amount": "12.34"})
    assert response.status_code == 302
    assert SpendEntry.objects.get().amount_minor == 1234
    assert AuditEvent.objects.filter(action="spend.created").count() == 1

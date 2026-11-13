"""Unanswered inbound replies remain visible without a separately captured inquiry."""
import datetime as dt

import pytest

from crm.attention import services as attention
from crm.contacts import services as contacts
from crm.contacts.models import Interaction
from crm.core import clock
from crm.work import services as work

pytestmark = pytest.mark.django_db
H = dt.timedelta(hours=1)


def awaiting(contact, policy, now):
    return [reason for item in attention.evaluate(now=now, policy=policy, contact_ids=[contact.pk])
            for reason in item.active_reasons if reason.code == "inquiry_awaiting"]


def record(contact, actor, kind, when, now, inquiry=None):
    with clock.frozen(now):
        return contacts.record_interaction(contact, actor=actor, kind=kind, channel="phone", summary="Recorded evidence",
                                           occurred_at=when, inquiry=inquiry)


def test_unlinked_reply_routes_response_needed_despite_future_plan(client, users, make_contact, policy, now):
    with clock.frozen(now):
        contact = make_contact(next_contact_agreed_at=now + 24 * H)
        work.create_task(contact, actor=users["ana"], assignee=users["ana"], title="Future call", kind="call",
                         due_at=now + 24 * H)
    record(contact, users["ana"], "inbound_reply", now - 25 * H, now)
    record(contact, users["ana"], "note", now - H, now)
    client.force_login(users["ana"])
    with clock.frozen(now):
        client.get(f"/contacts/{contact.pk}/")
    reasons = awaiting(contact, policy, now)
    assert len(reasons) == 1
    assert reasons[0].since == now - 25 * H
    assert reasons[0].recipients == [users["ana"]]
    assert reasons[0].inquiry is None
    assert reasons[0].overdue


@pytest.mark.parametrize("kind", ["outbound_attempt", "conversation", "meeting_tour"])
def test_later_human_response_clears_reply_but_new_reply_reopens(users, make_contact, policy, now, kind):
    contact = make_contact()
    record(contact, users["ana"], "inbound_reply", now - 3 * H, now)
    assert len(awaiting(contact, policy, now)) == 1
    record(contact, users["ana"], kind, now - 2 * H, now)
    assert awaiting(contact, policy, now) == []
    record(contact, users["ana"], "inbound_reply", now - H, now)
    reasons = awaiting(contact, policy, now)
    assert len(reasons) == 1
    assert reasons[0].since == now - H
    assert not reasons[0].overdue


def test_only_strictly_later_nonfuture_response_clears_reply(users, make_contact, policy, now):
    contact = make_contact()
    record(contact, users["ana"], "conversation", now - 3 * H, now)
    record(contact, users["ana"], "inbound_reply", now - H, now)
    record(contact, users["ana"], "outbound_attempt", now - H, now)
    Interaction.objects.create(contact=contact, actor=users["ana"], kind="conversation", channel="phone",
                               summary="Imported future evidence", occurred_at=now + H)
    assert len(awaiting(contact, policy, now)) == 1
    assert awaiting(contact, policy, now + 2 * H) == []


def test_linked_awaiting_inquiry_does_not_duplicate_reply_reason(users, make_contact, policy, now):
    with clock.frozen(now - 2 * H):
        contact = make_contact(inquiry="Please call")
    inquiry = contact.inquiries.get()
    record(contact, users["ana"], "inbound_reply", now - H, now, inquiry=inquiry)
    reasons = awaiting(contact, policy, now)
    assert len(reasons) == 1
    assert reasons[0].inquiry == inquiry

"""Agreed future contact pauses cadence nudges but not urgent work."""
import datetime as dt

import pytest

from crm.attention.services import evaluate
from crm.contacts.services import record_interaction
from crm.core import clock
from crm.work.services import create_task

pytestmark = pytest.mark.django_db


def test_agreed_future_contact_pauses_tour_alert_and_resurfaces_when_due(users, make_contact, policy, now):
    with clock.frozen(now):
        contact = make_contact(next_contact_agreed_at=now + dt.timedelta(days=2), inquiry="Still interested")
        record_interaction(contact, actor=users["ana"], kind="meeting_tour", channel="in_person",
                           summary="Viewed apartment", occurred_at=now - dt.timedelta(days=5))
        create_task(contact, actor=users["ana"], assignee=users["ana"], title="Send promised plan",
                    kind="promise", due_at=now - dt.timedelta(days=1))
    item = evaluate(now=now, policy=policy, contact_ids=[contact.pk])[0]
    codes = {reason.code for reason in item.active_reasons}
    assert "toured_no_followup" not in codes
    assert {"inquiry_awaiting", "promise_due"} <= codes
    later = evaluate(now=now + dt.timedelta(days=2), policy=policy, contact_ids=[contact.pk])[0]
    assert "toured_no_followup" in {reason.code for reason in later.active_reasons}

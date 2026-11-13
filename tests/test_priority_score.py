"""C-R1: an explained attention score sorts the queue and does not change responsibility."""
import datetime as dt

import pytest

from crm.attention import services as attention
from crm.contacts import services as contacts
from crm.core.services import get_policy, get_settings_row, update_policy
from crm.work.models import Assignment

pytestmark = pytest.mark.django_db
D = dt.timedelta(days=1)


def test_recent_tour_outranks_a_slightly_older_inquiry(users, make_contact, policy, now, frozen):
    older = make_contact("Older Inquiry", inquiry="Still waiting")
    newer = make_contact("Newer Tour", inquiry="Just asked")
    # Rewrite the inquiry clocks: capture stamps them at frozen now.
    from crm.contacts.models import Inquiry

    Inquiry.objects.filter(contact=older).update(received_at=now - 3 * D)
    Inquiry.objects.filter(contact=newer).update(received_at=now - D)
    contacts.record_interaction(
        newer, actor=users["ana"], kind="meeting_tour", channel="in_person",
        summary="Viewed the unit", occurred_at=now - D,
    )
    items = attention.evaluate(now=now, policy=policy)
    names = [item.contact.display_name for item in items]
    assert names.index("Newer Tour") < names.index("Older Inquiry")
    newer_item = next(item for item in items if item.contact.display_name == "Newer Tour")
    assert newer_item.score > next(item.score for item in items if item.contact.display_name == "Older Inquiry")
    assert "Tour within the last 7 day(s)" in newer_item.score_lines
    assert any(line.startswith("Inquiry waiting") for line in newer_item.score_lines)
    assert newer_item.handler_users == [users["ana"]]
    assert Assignment.objects.get(contact=newer).user_id == users["ana"].pk


def test_later_stage_and_a_watcher_add_explained_points(users, make_contact, policy, now, frozen):
    early = make_contact("Early Deal", inquiry="Hello")
    later = make_contact("Later Deal", inquiry="Hello")
    contacts.save_opportunity(
        early, actor=users["ana"], opportunity=None, expected_version=None,
        data={"title": "New file", "stage": "new", "amount_minor": 1, "currency": "USD"},
    )
    contacts.save_opportunity(
        later, actor=users["ana"], opportunity=None, expected_version=None,
        data={"title": "Decision file", "stage": "decision", "amount_minor": 1, "currency": "USD"},
    )
    contacts.watch(later, actor=users["ben"], reason="Keep an eye")
    items = {item.contact.display_name: item for item in attention.evaluate(now=now, policy=policy)}
    assert items["Later Deal"].score > items["Early Deal"].score
    assert "Open opportunity at Decision" in items["Later Deal"].score_lines
    assert "1 colleague(s) watching" in items["Later Deal"].score_lines
    assert Assignment.objects.get(contact=later).version == Assignment.objects.get(contact=early).version


def test_turning_the_score_off_restores_age_order(users, make_contact, now, frozen):
    older = make_contact("Older Inquiry", inquiry="Still waiting")
    newer = make_contact("Newer Tour", inquiry="Just asked")
    from crm.contacts.models import Inquiry

    Inquiry.objects.filter(contact=older).update(received_at=now - 3 * D)
    Inquiry.objects.filter(contact=newer).update(received_at=now - D)
    contacts.record_interaction(
        newer, actor=users["ana"], kind="meeting_tour", channel="in_person",
        summary="Viewed the unit", occurred_at=now - D,
    )
    policy = get_policy()
    policy["attention"]["priority"]["enabled"] = False
    update_policy(policy, actor=users["admin"], expected_version=get_settings_row().version, note="score off")
    names = [item.contact.display_name for item in attention.evaluate(now=now, policy=get_policy())]
    assert names.index("Older Inquiry") < names.index("Newer Tour")
    assert all(item.score == 0 and not item.score_enabled for item in attention.evaluate(now=now, policy=get_policy()))


def test_today_shows_the_score_as_a_sort_aid(client, users, make_contact, now, frozen):
    from crm.contacts.models import Inquiry

    contact = make_contact("Score Shown", inquiry="Is it available?")
    Inquiry.objects.filter(contact=contact).update(received_at=now - 2 * D)
    client.force_login(users["ana"])
    body = client.get("/").content.decode()
    assert "does not rank people" in body
    assert "Priority" in body
    assert "Why this score" in body
    queue = client.get("/attention/?scope=all").content.decode()
    assert "does not rank people" in queue
    assert "Score Shown" in queue
